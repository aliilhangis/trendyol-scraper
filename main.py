import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

async def scrape_product(url: str) -> dict:
    captured_data = {
        "reviews": [],
        "questions": [],
        "details": {}
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        # AĞ TRAFİĞİNİ DİNLE: Trendyol'un API yanıtlarını yakala
        async def handle_response(response):
            try:
                if "reviews" in response.url and response.status == 200:
                    data = await response.json()
                    captured_data["reviews"] = data.get("result", {}).get("productReviews", {}).get("content", [])
                elif "questions" in response.url and response.status == 200:
                    data = await response.json()
                    captured_data["questions"] = data.get("result", {}).get("items", [])
            except:
                pass

        page.on("response", handle_response)

        print(f"Hedefe gidiliyor: {url}")
        await page.goto(url, wait_until="networkidle", timeout=90000)
        
        # Sayfayı aşağı kaydır (Yorumlar ve detayların yüklenmesi için tetikleyici olur)
        await page.mouse.wheel(0, 2000)
        await page.wait_for_timeout(5000)

        # HTML'den temel bilgileri al (Yedek)
        full_url = page.url
        title = await page.locator("h1").first.inner_text() if await page.locator("h1").count() > 0 else "Bulunamadı"
        
        # Fiyatı yakalamak için daha agresif bir yöntem
        price = "Bulunamadı"
        try:
            # Sayfa içindeki tüm sayısal fiyat değerlerini ara
            price_element = page.locator(".prc-dsc, .prc-org, [data-behold='price-value']").first
            if await price_element.count() > 0:
                price = await price_element.inner_text()
        except: pass

        # Görselleri al
        images = []
        try:
            img_elements = await page.locator(".product-slide img").all()
            for img in img_elements:
                src = await img.get_attribute("src")
                if src and "cdn.dsmcdn" in src:
                    images.append(src)
        except: pass

        await browser.close()

    return {
        "status": "success",
        "full_url": full_url,
        "title": title,
        "price": price,
        "images": list(set(images)),
        "reviews": captured_data["reviews"],
        "questions": captured_data["questions"],
        "reviews_count": len(captured_data["reviews"]),
        "questions_count": len(captured_data["questions"])
    }

def main():
    input_url = os.getenv("PRODUCT_URL", "https://ty.gl/s1rjjs18qobjp")
    
    try:
        result = asyncio.run(scrape_product(input_url))
        print("===SCRAPE_RESULT_START===")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("===SCRAPE_RESULT_END===")
    except Exception as e:
        print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    main()
