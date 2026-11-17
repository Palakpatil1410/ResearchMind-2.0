import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def scrape_page(url: str, max_chars: int = 5000) -> str:
    """Return cleaned readable text from a URL. Never raises."""
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return ""
    try:
        resp = requests.get(url, timeout=12, headers=HEADERS)
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "").lower()
        if ctype and not any(k in ctype for k in ("text/html", "application/xhtml+xml")):
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "noscript", "svg"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        if len(text) < 300:
            print(f"[scrape] very little text from {url} (JS-rendered page?)")
            return ""
        return text[:max_chars]
    except Exception as e:
        print(f"[scrape] failed {url}: {e}")
        return ""