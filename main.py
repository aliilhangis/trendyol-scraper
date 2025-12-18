import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

async def scrape_product(url: str) -> dict:
    captured_data = {"reviews": [], "questions": [], "price": "Bulunamadı"}

    async with async_playwright() as p:
        # 1. Tarayıcıyı en 'insansı' ayarlarla başlat
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-http2" # Bazı ban sistemleri HTTP2'den tanır, bunu kapatıyoruz
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )

        page = await context.new_page()

        # 2. API YANITLARINI YAKALAMA (En Garantici Yol)
        async def handle_response(response):
            try:
                # Yorumlar API'sini yakala
                if "reviews" in response.url and response.status == 200:
                    data = await response.json()
                    captured_data["reviews"] = data.get("result", {}).get("productReviews", {}).get("content", [])
                
                # Soru API'sini yakala
                if "questions" in response.url and response.status == 200:
                    data = await response.json()
                    captured_data["questions"] = data.get("result", {}).get("items", [])
                
                # Ürün detay (fiyat) API'sini yakala
                if "details" in response.url and response.status == 200:
                    data = await response.json()
                    price_val = data.get("result", {}).get("price", {}).get("sellingPrice", {}).get("value")
                    if price_val:
                        captured_data["price"] = str(price_val)
            except:
                pass

        page.on("response", handle_response)

        print(f"Hedefe gidiliyor: {url}")
        
        # 3. SAYFAYA GİT VE ZORLA SCROLL YAP
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # Trendyol bazen botu 'çerez' sayfasında bekletir, sayfayı aktif tutalım
        await page.wait_for_timeout(4000)
        
        # Sayfayı 5 parça halinde aşağı kaydır (API'leri tetikler)
        for i in range(5):
            await page.mouse.wheel(0, 800)
            await page.wait_for_timeout(1000)

        # 4. HTML'DEN YEDEK VERİ ÇEKME
        title = await page.locator("h1").first.inner_text() if await page.locator("h1").count() > 0 else "Başlık Alınamadı"
        
        # Eğer API'den fiyat gelmediyse HTML'den kazıyalım
        if captured_data["price"] == "Bulunamadı":
            for sel in [".prc-dsc", ".prc-org", "span[data-behold='price-value']"]:
                if await page.locator(sel).count() > 0:
                    captured_data["price"] = await page.locator(sel).first.inner_text()
                    break

        await browser.close()

    return {
        "status": "success",
        "title": title,
        "price": captured_data["price"],
        "reviews_count": len(captured_data["reviews"]),
        "questions_count": len(captured_data["questions"]),
        "reviews": captured_data["reviews"][:10], # İlk 10 yorum
        "questions": captured_data["questions"][:10]
    }

def main():
    input_url = os.getenv("PRODUCT_URL", "https://ty.gl/s1rjjs18qobjp")
    
    try:
        result = asyncio.run(scrape_product(input_url))
        print("===SCRAPE_RESULT_START===")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("===SCRAPE_RESULT_END===")
    except Exception as e:
        print(f"Sistem Hatası: {e}")

if __name__ == "__main__":
    main()
