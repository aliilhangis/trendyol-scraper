import asyncio
import json
import os
import re
from urllib.parse import urlparse, parse_qs
import httpx
from playwright.async_api import async_playwright

def extract_ids(url):
    """URL'den Content ID (p-...) ve Merchant ID bilgilerini ayıklar."""
    content_id_match = re.search(r'p-(\d+)', url)
    content_id = content_id_match.group(1) if content_id_match else None
    
    parsed_url = urlparse(url)
    params = parse_qs(parsed_url.query)
    merchant_id = params.get('merchantId', [None])[0]
    
    return content_id, merchant_id

async def get_extra_data(content_id, merchant_id):
    """Yorumları ve Soruları Trendyol API üzerinden yüksek hızda çeker."""
    extra = {"reviews": [], "questions": []}
    
    # Trendyol'un bot olarak algılamaması için gerekli başlıklar
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.trendyol.com",
        "Referer": "https://www.trendyol.com/",
        "Domain": "www.trendyol.com"
    }
    
    async with httpx.AsyncClient(headers=headers, timeout=20.0, follow_redirects=True) as client:
        try:
            # 1. Yorumlar API (İlk sayfa, 20-30 yorum getirir)
            review_url = f"https://public-mdc.trendyol.com/discovery-web-social-gateway/reviews/{content_id}?merchantId={merchant_id or 0}&culture=tr-TR&page=0"
            r_rev = await client.get(review_url)
            if r_rev.status_code == 200:
                extra["reviews"] = r_rev.json().get("result", {}).get("productReviews", {}).get("content", [])

            # 2. Soru-Cevap API (İlk 20 soru)
            q_url = f"https://public-mdc.trendyol.com/discovery-web-questions-gateway/questions?contentId={content_id}&page=0&pageSize=20"
            r_q = await client.get(q_url)
            if r_q.status_code == 200:
                extra["questions"] = r_q.json().get("result", {}).get("items", [])
        
        except Exception as e:
            print(f"API Error (Reviews/Questions): {e}")
            
    return extra

async def scrape_product(url: str) -> dict:
    async with async_playwright() as p:
        # Railway uyumlu tarayıcı ayarları
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Sayfaya git ve kısa linkin çözülmesini (redirect) bekle
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000) # İçeriğin oturması için bekle
        
        # Gerçek URL'yi al (ty.gl den kurtulmak için)
        full_url = page.url
        content_id, merchant_id = extract_ids(full_url)

        # Başlık Çekme
        title = None
        try:
            title = await page.locator("h1").first.inner_text()
        except: pass

        # Fiyat Çekme (Farklı varyasyonları dene)
        price = None
        price_selectors = ["span.prc-dsc", "span.prc-org", "div.product-price-container", ".price-promotion-item"]
        for sel in price_selectors:
            try:
                if await page.locator(sel).count() > 0:
                    price = await page.locator(sel).first.inner_text()
                    if price: break
            except: continue

        # Görsel Çekme
        images = []
        try:
            imgs = page.locator("img")
            count = await imgs.count()
            for i in range(min(count, 15)):
                src = await imgs.nth(i).get_attribute("src")
                if src and "product" in src and src.startswith("http"):
                    if src not in images: images.append(src)
        except: pass

        await browser.close()

    # API üzerinden Yorum ve Soruları Getir
    extra_data = {"reviews": [], "questions": []}
    if content_id:
        extra_data = await get_extra_data(content_id, merchant_id)

    return {
        "url": full_url,
        "content_id": content_id,
        "merchant_id": merchant_id,
        "title": title,
        "price": price,
        "images": images,
        "reviews": extra_data["reviews"],
        "questions": extra_data["questions"]
    }

def main():
    # Railway'den linki al, yoksa varsayılanı kullan
    url = os.getenv("PRODUCT_URL")
    if not url:
        url = "https://www.trendyol.com/lg/55-inc-140-ekran-uydu-alicili-4k-smart-ai-sihirli-kumanda-qned-tv-2025-p-963920296?merchantId=275331"

    print(f"Başlatılıyor: {url}")
    data = asyncio.run(scrape_product(url))

    # Sonucu JSON formatında bas
    print("===SCRAPE_RESULT_START===")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print("===SCRAPE_RESULT_END===")

if __name__ == "__main__":
    main()
