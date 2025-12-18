import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

async def scrape_product(url: str) -> dict:
    captured_data = {"reviews": [], "questions": []}

    async with async_playwright() as p:
        # 1. Tarayıcıyı 'Stealth' başlat
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox", 
                "--disable-blink-features=AutomationControlled",
                "--use-fake-ui-for-media-stream",
                "--window-size=1920,1080"
            ]
        )
        
        # 2. Gerçekçi bir Context oluştur
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={"Accept-Language": "tr-TR,tr;q=0.9"}
        )

        # Webdriver izini sil
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()

        # 3. API Yanıtlarını Yakala
        async def handle_response(response):
            try:
                # Trendyol yorum ve soru API uç noktaları
                if "discovery-web-social-gateway/reviews" in response.url and response.status == 200:
                    res_json = await response.json()
                    captured_data["reviews"] = res_json.get("result", {}).get("productReviews", {}).get("content", [])
                if "discovery-web-questions-gateway/questions" in response.url and response.status == 200:
                    res_json = await response.json()
                    captured_data["questions"] = res_json.get("result", {}).get("items", [])
            except: pass

        page.on("response", handle_response)

        print(f"Hedefe gidiliyor: {url}")
        
        # 4. Sayfaya git ve çerezleri/renderı bekle
        await page.goto(url, wait_until="commit", timeout=60000)
        await page.wait_for_timeout(3000) # İlk yükleme
        
        # Fiyat ve görsellerin yüklenmesi için 'scroll' yap
        # Trendyol scroll yapılmadan API'leri tetiklemez
        for _ in range(3):
            await page.mouse.wheel(0, 1000)
            await page.wait_for_timeout(1500)

        # 5. Verileri Ayıkla (HTML + Veri Katmanı)
        full_url = page.url
        title = await page.locator("h1").first.inner_text() if await page.locator("h1").count() > 0 else "Bulunamadı"
        
        # Fiyatı yakalamak için daha derin tarama
        price = "Bulunamadı"
        price_selectors = [".prc-dsc", ".prc-org", "span.product-price", ".total-price"]
        for sel in price_selectors:
            if await page.locator(sel).count() > 0:
                price = await page.locator(sel).first.inner_text()
                break

        # Görseller
        images = []
        try:
            # Sadece ürün ana görsellerini al (Thumbnail değil)
            imgs = await page.query_selector_all(".product-slide img, .base-product-image img")
            for img in imgs:
                src = await img.get_attribute("src")
                if src and "cdn.dsmcdn" in src:
                    images.append(src)
        except: pass

        await browser.close()

    return {
        "status": "success",
        "title": title,
        "price": price,
        "full_url": full_url,
        "images": list(set(images))[:5], # İlk 5 görsel yeterli
        "reviews": captured_data["reviews"],
        "questions": captured_data["questions"],
        "reviews_count": len(captured_data["reviews"]),
        "questions_count": len(captured_data["questions"])
    }

def main():
    # Railway environment variable veya test linki
    input_url = os.getenv("PRODUCT_URL", "https://ty.gl/s1rjjs18qobjp")
    
    try:
        result = asyncio.run(scrape_product(input_url))
        print("===SCRAPE_RESULT_START===")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("===SCRAPE_RESULT_END===")
    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    main()
