import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

async def scrape_product(url: str) -> dict:
    captured_data = {"reviews": [], "questions": [], "price": "Bulunamadı"}

    async with async_playwright() as p:
        # 1. BOT ENGELLERİNİ AŞAN BAŞLATMA AYARLARI
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-http2" # Bazı sunucular HTTP2 parmak izinden botu tanır
            ]
        )
        
        # Gerçek bir Windows kullanıcısı profili
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800},
            extra_http_headers={"Accept-Language": "tr-TR,tr;q=0.9"}
        )

        # Webdriver izini tamamen temizle
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()

        # 2. ARKA PLAN API TRAFİĞİNİ YAKALA (Network Sniffing)
        async def handle_response(response):
            try:
                # Yorumlar ve Sorular API'lerini URL'den yakala
                if "reviews" in response.url and response.status == 200:
                    res_json = await response.json()
                    captured_data["reviews"] = res_json.get("result", {}).get("productReviews", {}).get("content", [])
                
                if "questions" in response.url and response.status == 200:
                    res_json = await response.json()
                    captured_data["questions"] = res_json.get("result", {}).get("items", [])
            except:
                pass

        page.on("response", handle_response)

        print(f"Hedefe gidiliyor: {url}")
        
        # 3. SAYFAYA GİT VE ETKİLEŞİM KUR
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000) # Sayfanın oturması için kısa bekleme

        # Trendyol scroll yapmadan yorumları yüklemez. 
        # Sayfayı yavaşça 3 defa aşağı kaydırıyoruz.
        for _ in range(3):
            await page.mouse.wheel(0, 1000)
            await page.wait_for_timeout(1500)

        # 4. VERİLERİ TOPLA
        full_url = page.url
        title = await page.locator("h1").first.inner_text() if await page.locator("h1").count() > 0 else "Başlık Alınamadı"
        
        # Fiyatı yakalamak için daha agresif bir tarama
        price = "Bulunamadı"
        for sel in [".prc-dsc", ".prc-org", "span[data-behold='price-value']"]:
            if await page.locator(sel).count() > 0:
                price = await page.locator(sel).first.inner_text()
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
        "price": price,
        "full_url": full_url,
        "images": list(set(images))[:5],
        "reviews": captured_data["reviews"],
        "questions": captured_data["questions"],
        "reviews_count": len(captured_data["reviews"]),
        "questions_count": len(captured_data["questions"])
    }

def main():
    input_url = os.
