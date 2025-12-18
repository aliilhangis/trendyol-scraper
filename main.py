import asyncio
import json
import os
import requests
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


async def get_product_id(url: str) -> int:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except PlaywrightTimeoutError:
            pass  # yine de JS state'i deneyelim

        # JS state oluşana kadar bekle (max 15 sn)
        product_id = None
        for _ in range(15):
            product_id = await page.evaluate("""
                () => {
                    try {
                        return window.__PRODUCT_DETAIL_APP_INITIAL_STATE__
                            ?.product
                            ?.productId || null;
                    } catch (e) {
                        return null;
                    }
                }
            """)
            if product_id:
                break
            await page.wait_for_timeout(1000)

        await browser.close()

        if not product_id:
            raise Exception("productId bulunamadı (sayfa state oluşmadı)")

        return int(product_id)


def get_comments(product_id: int, limit: int = 20) -> list:
    url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/review/{product_id}"
    params = {"page": 0, "size": limit}

    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    return [
        {
            "rate": x.get("rate"),
            "comment": x.get("comment"),
            "date": x.get("commentDate")
        }
        for x in data.get("result", {}).get("reviews", [])
    ]


def get_qna(product_id: int, limit: int = 20) -> list:
    url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/qna/{product_id}"
    params = {"page": 0, "size": limit}

    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    return [
        {
            "question": x.get("question"),
            "answer": x.get("answer")
        }
        for x in data.get("result", {}).get("questions", [])
    ]


def main():
    url = os.getenv("PRODUCT_URL")
    if not url:
        raise Exception("PRODUCT_URL environment variable bulunamadı")

    product_id = asyncio.run(get_product_id(url))

    output = {
        "url": url,
        "productId": product_id,
        "comments": get_comments(product_id),
        "qna": get_qna(product_id)
    }

    print("===SCRAPE_RESULT_START===")
    print(json.dumps(output, ensure_ascii=False))
    print("===SCRAPE_RESULT_END===")


if __name__ == "__main__":
    main()
