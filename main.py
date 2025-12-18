import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

async def scrape_product(url: str) -> dict:
    async with async_playwright() as p:
        # Bot korumasını aşmak için daha gerçekçi tarayıcı ayarları
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        print(f"Sayfa yükleniyor: {url}")
        # Sayfaya git ve ağ trafiği durulana kadar bekle
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Yükleme hatası (yine de devam ediliyor): {e}")

        # --- KRİTİK HAMLE: GİZLİ JSON VERİSİNİ ÇEK ---
        # Trendyol tüm datayı 'window.__PRODUCT_DETAIL_APP_INITIAL_STATE__' içine koyar
        product_data = {}
        try:
            raw_script = await page.evaluate("window.__PRODUCT_DETAIL_APP_INITIAL_STATE__")
            if raw_script:
                product_data = raw_script
        except:
            print("Gizli veri objesi bulunamadı.")

        # --- VERİLERİ AYIKLA ---
        product = product_data.get("product", {})
        
        # Başlık ve Fiyat
        title = product.get("name", "Başlık Bulunamadı")
        price = product.get("price", {}).get("sellingPrice", {}).get("value", "Fiyat Bulunamadı")
        
        # Görseller
        images = [f"https://cdn.dsmcdn.com{img}" for img in product.get("images", [])]
        
        # Yorumlar (Eğer sayfa içine gömülüyse buradan alırız)
        reviews_raw = product_data.get("reviews", {}).get("content", [])
        
        # Soru-Cevaplar (Eğer sayfa içine gömülüyse buradan alırız)
        questions_raw = product_data.get("questions", {}).get("items", [])

        # Eğer yukarıdaki JSON boşsa, HTML'den son bir kez dene
        if title == "Başlık Bulunamadı":
            title = await page.locator("h1").first.inner_text() if await page.locator("h1").count() > 0 else title

        await browser.close()

    return {
        "status": "success",
        "url": url,
        "content_id": product.get("id"),
        "title": title,
        "price": price,
        "brand": product.get("brand", {}).get("name"),
        "images": images,
        "reviews": reviews_raw,
        "questions": questions_raw,
        "total_reviews": product.get("reviews", {}).get("totalCount", 0)
    }

def main():
    # URL'yi env'den veya manuel al
    url = os.getenv("PRODUCT_URL", "https://www.trendyol.com/lg/55-inc-140-ekran-uydu-alicili-4k-smart-ai-sihirli-kumanda-qned-tv-2025-p-963920296?merchantId=275331")
    
    try:
        data = asyncio.run(scrape_product(url))
        print("===SCRAPE_RESULT_START===")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        print("===SCRAPE_RESULT_END===")
    except Exception as e:
        print(f"Fatal Error: {e}")

if __name__ == "__main__":
    main()
