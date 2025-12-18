import asyncio
import json
import os
import re
from urllib.parse import urlparse, parse_qs
import httpx # API istekleri için daha hafif bir kütüphane
from playwright.async_api import async_playwright

# ID Ayıklama Fonksiyonu
def extract_ids(url):
    content_id_match = re.search(r'p-(\d+)', url)
    content_id = content_id_match.group(1) if content_id_match else None
    parsed_url = urlparse(url)
    params = parse_qs(parsed_url.query)
    merchant_id = params.get('merchantId', [None])[0]
    return content_id, merchant_id

async def get_extra_data(content_id, merchant_id):
    """Yorum ve soruları API üzerinden çeker"""
    extra = {"reviews": [], "questions": []}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Domain": "www.trendyol.com"
    }
    
    async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
        try:
            # 1. Yorumlar API
            rev_url = f"https://public-mdc.trendyol.com/discovery-web-social-gateway/reviews/{content_id}?merchantId={merchant_id or 0}&culture=tr-TR&page=0"
            r = await client.get(rev_url)
            if r.status_code == 200:
                rev_json = r.json()
                extra["reviews"] = rev_json.get("result", {}).get("productReviews", {}).get("content", [])
            
            # 2. Sorular API
            q_url = f"https://public-mdc.trendyol.com/discovery-web-questions-gateway/questions?contentId={content_id}&page=0&pageSize=10"
            q = await client.get(q_url)
            if q.status_code == 200:
                q_json = q.json()
                extra["questions"] = q_json.get("result", {}).get("items", [])
        except Exception as e:
            print(f"API Error: {e}")
            
    return extra

async def scrape_product(url: str) -> dict:
    # Önce ID'leri alalım
    content_id, merchant_id = extract_ids(url)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        
        # Başlık
        title = await page.locator("h1").first.inner_text() if await page.locator("h1").count() > 0 else None
        
        # Fiyat
        price = None
        for sel in ["span.price-view-original", "span.prc-dsc", "span.prc-org"]:
            if await page.locator(sel).count() > 0:
                price = await page.locator(sel).first.inner_text()
                break

        # Görseller
        images = []
        imgs = page.locator("img")
        for i in range(min(await imgs.count(), 10)): # İlk 10 görsel
            src = await imgs.nth(i).get_attribute("src")
            if src and "product" in src: # Sadece ürün görsellerini al
                images.append(src)

        await browser.close()

    # API ile yorum ve soruları çek
    extra_data = await get_extra_data(content_id, merchant_id)

    return {
        "url": url,
        "content_id": content_id,
        "title": title,
        "price": price,
        "images": images,
        "reviews": extra_data["reviews"],
        "questions": extra_data["questions"]
    }

def main():
    url = os.getenv("PRODUCT_URL")
    if not url:
        # Test için manuel link koyabilirsin, Railway'de env'den okur
        url = "https://www.trendyol.com/lg/55-inc-140-ekran-uydu-alicili-4k-smart-ai-sihirli-kumanda-qned-tv-2025-p-963920296?merchantId=275331"

    data = asyncio.run(scrape_product(url))

    print("===SCRAPE_RESULT_START===")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print("===SCRAPE_RESULT_END===")

if __name__ == "__main__":
    main()
