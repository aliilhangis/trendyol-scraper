import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

async def scrape_product(url: str) -> dict:
    captured_data = {"reviews": [], "questions": [], "price": "Bulunamadı"}

    async with async_playwright() as p:
        # 1. Tarayıcıyı Stealth (Gizli) Ayarlarla Başlat
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-http2"
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800},
            extra_http_headers={"Accept-Language": "tr-TR,tr;q=0.9"}
        )

        # Webdriver izini sil (Bot koruması için kritik)
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()

        # 2. Arka Plan API Yanıtlarını Yakala
        async def handle_response(response):
            try:
                # Yorumlar API
                if "discovery-web-social-gateway/reviews" in response.url and response.status == 200:
                    res_json = await response.json()
                    captured_data["reviews"] = res_json.get("result", {}).get("productReviews", {}).get("content", [])
                
                # Sorular API
                if "discovery-web-questions-gateway/questions" in response.url and response.status == 200:
                    res_json = await response.json()
                    captured_data["questions"] = res_json.get("result", {}).get("items", [])
            except:
                pass

        page.on("response", handle_response)

        print(f"Hedefe gidiliyor: {url}")
        
        # 3. Sayfaya Git ve Etkileşim Kur
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)

        # Trendyol API'lerini tetiklemek için yavaşça aşağı kaydır
        for _ in range(3):
            await page.mouse.wheel(0, 1000)
            await page.wait_for_timeout(1500)

        # 4. Verileri Topla
        full_url = page.url
        title = await page.locator("h1").first.inner_text() if await page.locator("h1").count() > 0 else "Başlık Alınamadı"
        
        # Fiyatı HTML'den yakalamaya çalış
        for sel in [".prc-dsc", ".prc-org", "span[data-behold='price-value']"]:
            if await page.locator(sel).count() > 0:
                captured_data["price"] = await page.locator(sel).first.inner_text()
                break

        # Görseller
        images = []
        try:
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
        "price": captured_data["price"],
        "full_url": full_url,
        "images": list(set(images))[:5],
        "reviews": captured_data["reviews"],
        "questions": captured_data["questions"],
        "reviews_count": len(captured_data["reviews"]),
        "questions_count": len(captured_data["questions"])
    }

def main():
    # URL'yi env'den güvenli bir şekilde çekiyoruz
    input_url = os.getenv("PRODUCT_URL", "https://ty.gl/s1rjjs18qobjp")
    
    try:
        # Event loop'u başlat
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(scrape_product(input_url))
        
        print("===SCRAPE_RESULT_START===")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("===SCRAPE_RESULT_END===")
    except Exception as e:
        print(f"Hata oluştu: {str(e)}")

if __name__ == "__main__":
    main()
