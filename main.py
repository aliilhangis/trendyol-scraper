import asyncio
import json
import os
import re
from urllib.parse import urlparse, parse_qs
import httpx
from playwright.async_api import async_playwright

def extract_ids(url):
    content_id_match = re.search(r'p-(\d+)', url)
    content_id = content_id_match.group(1) if content_id_match else None
    parsed_url = urlparse(url)
    params = parse_qs(parsed_url.query)
    merchant_id = params.get('merchantId', [None])[0]
    return content_id, merchant_id

async def get_extra_data(content_id, merchant_id):
    extra = {"reviews": [], "questions": []}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Domain": "www.trendyol.com",
        "Referer": "https://www.trendyol.com/"
    }
    
    # Railway DNS hatalarını aşmak için AsyncClient ayarları optimize edildi
    async with httpx.AsyncClient(headers=headers, timeout=20.0, follow_redirects=True, verify=False) as client:
        try:
            # Yorumlar
            rev_url = f"https://public-mdc.trendyol.com/discovery-web-social-gateway/reviews/{content_id}?merchantId={merchant_id or 0}&culture=tr-TR&page=0"
            r_rev = await client.get(rev_url)
            if r_rev.status_code == 200:
                extra["reviews"] = r_rev.json().get("result", {}).get("productReviews", {}).get("content", [])

            # Sorular
            q_url = f"https://public-mdc.trendyol.com/discovery-web-questions-gateway/questions?contentId={content_id}&page=0&pageSize=20"
            r_q = await client.get(q_url)
            if r_q.status_code == 200:
                extra["questions"] = r_q.json().get("result", {}).get("items", [])
        except Exception as e:
            print(f"API Connection Error: {e}") # DNS hatası burada yakalanırsa loglanır
            
    return extra

async def scrape_product(url: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        await page.goto(url, wait_until="networkidle", timeout=60000)
        
        full_url = page.url
        content_id, merchant_id = extract_ids(full_url)

        # Ürün Başlığı
        title = await page.locator("h1").first.inner_text() if await page.locator("h1").count() > 0 else "Başlık Alınamadı"

        # --- YENİ FİYAT YAKALAMA MANTIĞI ---
        # Sayfanın kaynak kodundaki JSON verisinden (window.__PRODUCT_DETAIL_APP_INITIAL_STATE__) fiyatı çekelim
        price = "Fiyat Bulunamadı"
        try:
            content = await page.content()
            price_match = re.search(r'"totalPrice":\s*(\d+\.?\d*)', content)
            if price_match:
                price = price_match.group(1)
            else:
                # Klasik yöntem yedek
                price_loc = page.locator(".prc-dsc, .prc-org").first
                if await price_loc.count() > 0:
                    price = await price_loc.inner_text()
        except: pass

        # Görseller
        images = []
        try:
            imgs = await page.locator(".product-slide img").all()
            for img in imgs:
                src = await img.get_attribute("src")
                if src and "cdn.dsmcdn" in src: images.append(src)
        except: pass

        await browser.close()

    # API verilerini çek
    extra_data = await get_extra_data(content_id, merchant_id)

    return {
        "status": "success",
        "url": full_url,
        "content_id": content_id,
        "title": title,
        "price": price,
        "reviews_count": len(extra_data["reviews"]),
        "questions_count": len(extra_data["questions"]),
        "reviews": extra_data["reviews"],
        "questions": extra_data["questions"],
        "images": list(set(images)) # Tekrar edenleri temizle
    }

def main():
    url = os.getenv("PRODUCT_URL", "https://www.trendyol.com/lg/55-inc-140-ekran-uydu-alicili-4k-smart-ai-sihirli-kumanda-qned-tv-2025-p-963920296?merchantId=275331")
    
    print(f"İşlem başlıyor... Hedef: {url}")
    data = asyncio.run(scrape_product(url))

    print("===SCRAPE_RESULT_START===")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print("===SCRAPE_RESULT_END===")

if __name__ == "__main__":
    main()
