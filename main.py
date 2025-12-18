import asyncio
import json
import os
from playwright.async_api import async_playwright


async def scrape_product(url: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Cookie accept (best-effort)
        cookie_selectors = [
            'button#onetrust-accept-btn-handler',
            'button:has-text("Kabul Et")',
            'button:has-text("Çerezleri Kabul Et")',
            'button:has-text("Accept All")'
        ]
        for selector in cookie_selectors:
            try:
                await page.click(selector, timeout=2000)
                break
            except Exception:
                pass

        await page.wait_for_timeout(1500)

        # Scroll biraz
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
        await page.wait_for_timeout(1500)

        # Title
        title = ""
        try:
            title = await page.locator("h1").first.inner_text()
        except Exception:
            pass

        # Price (fallback'li)
        price = None
        price_selectors = [
            "span.price-view-original",
            "span.prc-dsc",
            "span.prc-org"
        ]
        for sel in price_selectors:
            try:
                loc = page.locator(sel)
                if await loc.count() > 0:
                    price = await loc.first.inner_text()
                    break
            except Exception:
                pass

        # Description
        description = ""
        try:
            desc = page.locator("div#product-description")
            if await desc.count() > 0:
                description = await desc.first.inner_text()
        except Exception:
            pass

        # Images (tüm img src – ürünleşirken filtrelenecek)
        images = []
        try:
            imgs = page.locator("img")
            count = await imgs.count()
            for i in range(count):
                src = await imgs.nth(i).get_attribute("src")
                if src and src.startswith("http") and src not in images:
                    images.append(src)
        except Exception:
            pass

        # Comments (şimdilik boş – DOM çok değişken)
        comments = []

        # QnA (şimdilik boş)
        qna = []

        await browser.close()

        return {
            "url": url,
            "title": title.strip() if title else None,
            "price": price.strip() if price else None,
            "description": description.strip() if description else "",
            "images": images,
            "comments": comments,
            "qna": qna
        }


def main():
    url = os.getenv("PRODUCT_URL")
    if not url:
        raise Exception("PRODUCT_URL environment variable bulunamadı")

    data = asyncio.run(scrape_product(url))

    print("===SCRAPE_RESULT_START===")
    print(json.dumps(data, ensure_ascii=False))
    print("===SCRAPE_RESULT_END===")


if __name__ == "__main__":
    main()
