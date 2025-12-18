import json
import os
import re
import requests


def get_product_id_from_url(url: str) -> int:
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    })

    r = session.get(url, allow_redirects=True, timeout=20)
    final_url = r.url

    # URL içinden -p-123456789 yakala
    match = re.search(r"-p-(\d+)", final_url)
    if not match:
        raise Exception("productId URL içinden bulunamadı")

    return int(match.group(1))


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

    product_id = get_product_id_from_url(url)

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
