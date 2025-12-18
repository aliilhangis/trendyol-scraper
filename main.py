import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

async def scrape_product(url: str) -> dict:
    async with async_playwright() as p:
        # Daha az bot izi bırakan başlatma
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars"
            ]
        )
        
        # Gerçek bir kullanıcı çerez yapısı ve dili simüle ediliyor
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="tr-TR",
            timezone_id="Europe/Istanbul"
        )

        page = await context.new_page()
        
        # Bot kontrolü olan 'webdriver' özelliğini tamamen kaldır
        await page.add_init_script("delete navigator.__proto__.webdriver")

        print(f"Hedefe gidiliyor: {url}")
        
        # Sayfaya git ve içeriğin render edilmesi için süre tanı
        await page.goto(url, wait_until="networkidle", timeout=60000)
        
        # Sayfada gerçek bir insan gibi bekle ve kaydır
        await page.wait_for_timeout(4000)
        await page.mouse.wheel(0, 1500) 
        await page.wait_for_timeout(2000)

        # Temel Bilgiler
        full_url = page.url
        title = "Bulunamadı"
        price = "Bulunamadı"
        reviews = []
        questions = []

        # --- VERİ ÇEKME STRATEJİSİ ---
        # 1. Başlık
        title_loc = page.locator("h1.pr-new-br span, h1").first
        if await title_loc.count() > 0:
            title = await title_loc.inner_text()

        # 2. Fiyat (En güncel seçiciler)
        for sel in [".prc-dsc", ".prc-org", "span[data-behold='price-value']", ".product-price"]:
            if await page.locator(sel).count() > 0:
                price = await page.locator(sel).first.inner_text()
                break

        # 3. Yorumlar ve Sorular (Data Layer üzerinden deneme)
        try:
            raw_state = await page.evaluate("window.__PRODUCT_DETAIL_APP_INITIAL_STATE__")
            if raw_state:
                if "reviews" in raw_state:
                    reviews = raw_state["reviews"].get("content", [])
                if "questions" in raw_state:
                    questions = raw_state["questions"].get("items", [])
        except:
            pass

        await browser.close()

    return {
        "status": "success",
        "title": title.strip() if title else title,
        "price": price.strip() if price else price,
        "full_url": full_url,
        "reviews_count": len(reviews),
        "questions_count": len(questions),
        "reviews": reviews[:5], # Logları kirletmemek için ilk 5'i
        "questions": questions[:5]
    }

def main():
    input_url = os.getenv("PRODUCT_URL", "https://ty.gl/s1rjjs18qobjp")
    result = asyncio.run(scrape_product(input_url))

    print("===SCRAPE_RESULT_START===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("===SCRAPE_RESULT_END===")

if __name__ == "__main__":
    main()
