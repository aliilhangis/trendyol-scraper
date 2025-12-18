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

        # Title
        title = None
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

        # Images
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

        await browser.close()

        return {
            "url": url,
            "title": title,
            "price": price,
            "images": images
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
