import asyncio
import json
import os
from playwright.async_api import async_playwright

async def scrape_product(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page()

        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Çerez popup kapatma
        cookie_selectors = [
            'button:has-text("Kabul Et")',
            'button#onetrust-accept-btn-handler',
            'button:has-text("Çerezleri Kabul Et")',
            'button[data-testid="cookie-accept-button"]',
            'button:has-text("Accept All")'
        ]
        for sel in cookie_selectors:
            try:
                await page.wait_for_selector(sel, timeout=2000)
                await page.click(sel)
                break
            except:
                continue

        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight/3)")
        await page.wait_for_timeout(1000)

        # Ürün başlığı
        title = await page.locator("h1").first.inner_text()

        # Fiyat
        price = None
        price_locator = page.locator("span.price-view-original")
        if await price_locator.count() > 0:
            price = await price_locator.first.inner_text()

        # Açıklama
        description = ""
        desc_locator = page.locator(
            "div#product-description, div.product-description, div#productDetail"
        )
        if await desc_locator.count() > 0:
            description = await desc_locator.first.inner_text()

        # Görseller
        images = []
        thumbs = page.locator("img")
        for i in range(await thumbs.count()):
            src = await thumbs.nth(i).get_attribute("src")
            if src and src.startswith("http") and src not in images:
                images.append(src)

        # Yorumlar (limitli)
        comments = []
        comment_selectors = [
            "div.comment",
            "div[data-testid='comment']",
            "div.review-item"
        ]
        for selector in comment_selectors:
            items = page.locator(selector)
            if await items.count() > 0:
                for i in range(min(await items.count(), 50)):
                    try:
                        text = await items.nth(i).inner_text()
                        if text.strip():
                            comments.append({"text": text.strip()})
                    except:
                        continue
                break

        # Q&A
        qna = []
        qna_items = page.locator("div.qna-item")
        if await qna_items.count() > 0:
            for i in range(min(await qna_items.count(), 50)):
                try:
                    question = ""
                    answer = ""
                    q = qna_items.nth(i).locator("h4")
                    a = qna_items.nth(i).locator("h5")
                    if await q.count() > 0:
                        question = await q.first.inner_text()
                    if await a.count() > 0:
                        answer = await a.first.inner_text()
                    if question or answer:
                        qna.append({
                            "question": question.strip(),
                            "answer": answer.strip()
                        })
                except:
                    continue

        await browser.close()

        return {
            "url": url,
            "title": title.strip(),
            "price": price.strip() if price else None,
            "description": description.strip(),
            "images": images,
            "comments": comments,
            "qna": qna
        }


def main():
    url = os.getenv("PRODUCT_URL")
    if not url:
        raise Exception("PRODUCT_URL environment variable bulunamadı")

    data = asyncio.run(scrape_product(url))

    # Railway log’larına JSON bas (n8n / debug için ideal)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
