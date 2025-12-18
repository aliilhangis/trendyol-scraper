import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

async def scrape_product(url: str) -> dict:
    async with async_playwright() as p:
        # Daha "insansı" bir tarayıcı profili
        browser = await p.chromium.launch(
            headless=True, 
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        # Gerçek bir Windows tarayıcısı gibi davran
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale="tr-TR"
        )
        page = await context.new_page()
        
        print(f"Hedefe gidiliyor: {url}")
        
        # 1. SAYFAYI AÇ VE YÖNLENDİRMEYİ BEKLE
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            # Kısa linkten uzun linke geçiş için ekstra bekleme
            await page.wait_for_timeout(5000) 
            
            # Eğer çerez onayı penceresi çıkarsa kapat (Bazen veriyi engeller)
            try:
                if await page.locator("#onetrust-accept-btn-handler").count() > 0:
                    await page.click("#onetrust-accept-btn-handler", timeout=2000)
            except: pass

        except Exception as e:
            print(f"Yükleme hatası: {e}")

        # 2. UZUN URL VE ID TESPİTİ
        full_url = page.url
        content_id = None
        id_match = re.search(r'p-(\d+)', full_url)
        if id_match:
            content_id = id_match.group(1)
        
        # 3. VERİ ÇEKME (JSON + HTML HYBRID)
        data_result = {
            "title": "Bulunamadı",
            "price": "Bulunamadı",
            "images": [],
            "reviews": [],
            "questions": []
        }

        # Ham veri objesini sayfadan çekmeye çalış
        try:
            raw_data = await page.evaluate("() => window.__PRODUCT_DETAIL_APP_INITIAL_STATE__")
            if raw_data and "product" in raw_data:
                p_info = raw_data["product"]
                data_result["title"] = p_info.get("name")
                data_result["price"] = p_info.get("price", {}).get("sellingPrice", {}).get("value")
                data_result["images"] = [f"https://cdn.dsmcdn.com{img}" for img in p_info.get("images", [])]
                
                # Yorum ve Sorular (Sayfaya gömülüyse)
                if "reviews" in raw_data:
                    data_result["reviews"] = raw_data["reviews"].get("content", [])
                if "questions" in raw_data:
                    data_result["questions"] = raw_data["questions"].get("items", [])
        except:
            print("JS Objesi okunamadı, HTML denemesi yapılıyor...")

        # Yedek Plan: HTML Selector'lar
        if data_result["title"] == "Bulunamadı":
            try:
                data_result["title"] = await page.locator("h1").first.inner_text()
                # Fiyat için alternatif selector
                for sel in [".prc-dsc", ".prc-org", "span[data-behold='price-value']"]:
                    if await page.locator(sel).count() > 0:
                        data_result["price"] = await page.locator(sel).first.inner_text()
                        break
            except: pass

        await browser.close()

    return {
        "status": "success",
        "content_id": content_id,
        "full_url": full_url,
        "data": data_result
    }

def main():
    # URL'yi env'den al veya default kullan
    input_url = os.getenv("PRODUCT_URL", "https://ty.gl/s1rjjs18qobjp")
    
    result = asyncio.run(scrape_product(input_url))

    print("===SCRAPE_RESULT_START===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("===SCRAPE_RESULT_END===")

if __name__ == "__main__":
    main()
