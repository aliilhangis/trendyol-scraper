import asyncio
import json
import os
import re
import requests
from playwright.async_api import async_playwright


# -------------------------
# Playwright: productId al
# -------------------------
async def get_product_id(url: str) -> int:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Sayfa JS state içinden productId çek
        content = await page.content()

        browser.close()

        match = re.search(r'"productId"\s*:\s*(\d+)', content)
        if not match:
            raise Exception("productId bulunamadı")

        return int(match.group(1))


# -------------------------
# Trendyol API – Yorumlar
# -------------------------
def get_comments(product_id: int, limit: int = 20) -> list:
    url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/review/{product_id}"
    params = {
        "page": 0,
        "size": limit,
        "orderBy": "DESC"
    }

    res = requests.get(url, params=params, timeout=15)
    res.raise_for_status()
    data = res.json()

    comments = []
    for item in data.get("result", {}).get("reviews", []):
        comments.append({
            "rate": item.get("rate"),
            "comment": item.get("comment"),
            "date": item.get("commentDate")
        })

    return comments


# -------------------------
# Trendyol API – QnA
# -------------------------
def get_qna(product_id: int, limit: int = 20) -> list:
    url = f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/qna/{product_id}"
    params = {
        "page": 0,
        "size": limit
    }

    res = requests.get(url, params=params, timeout=15)
    res.raise_for_status()
    data = res.json()

    qna = []
    for item in data.get("result", {}).get("questions", []):
        qna.append({
            "question": item.get("question"),
            "answer": item.get("answer")
        })

    return qna


# -------------------------
# MAIN
# -------------------------
def main():
    url = os.getenv("PRODUCT_URL")
    if not url:
        raise Exception("PRODUCT_URL environment variable bulunamadı")

    product_id = asyncio.run(get_product_id(url))
    comments = get_comments(product_id)
    qna = get_qna(product_id)

    output = {
        "url": url,
        "productId": product_id,
        "comments": comments,
        "qna": qna
    }

    print("===SCRAPE_RESULT_START===")
    print(json.dumps(output, ensure_ascii=False))
    print("===SCRAPE_RESULT_END===")


if __name__ == "__main__":
    main()
