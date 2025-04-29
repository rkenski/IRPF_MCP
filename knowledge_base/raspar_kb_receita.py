#!/usr/bin/env python3
"""Crawler and extractor for Receita Federal IRPF portal.

- Traverses only pages below the configured BASE_URL
- Stores HTML and structured json using *trafilatura*
- Designed for reuse as a library **or** CLI script.

Usage:
    python irpf_crawler.py --output knowledge_base/textos_receita.json
"""

from __future__ import annotations
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Set
from urllib.parse import urljoin, urlparse
from tqdm import tqdm

try:
    from trafilatura import extract, fetch_url
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "trafilatura"])

try:
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])

from requests.adapters import HTTPAdapter, Retry

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
BASE_URL = (
    "https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; IRPF-crawler/1.0)"}

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #


def _build_session(retries: int = 3, backoff: float = 0.5) -> requests.Session:
    """Return a *requests* session with retries and timeouts configured."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(HEADERS)
    return session


SESSION = _build_session()

# --------------------------------------------------------------------------- #
# Page object
# --------------------------------------------------------------------------- #


@dataclass
class IRPFPage:
    """Represents a single IRPF page."""

    url: str
    html: str | None = field(init=False, default=None, repr=False)
    soup: BeautifulSoup | None = field(init=False, default=None, repr=False)

    def _scrape(self) -> None:
        logger.debug("Scraping %s", self.url)
        response = SESSION.get(self.url, timeout=20)
        response.raise_for_status()
        self.html = response.text
        self.soup = BeautifulSoup(self.html, "html.parser")

    # Public helpers -------------------------------------------------------- #

    @property
    def soup_obj(self) -> BeautifulSoup:
        if self.soup is None:
            self._scrape()
        return self.soup  # type: ignore

    def iter_links(self) -> Iterable[str]:
        """Yield absolute URLs for in‑domain links discovered on the page."""
        for tag in self.soup_obj.find_all("a", href=True):
            href = tag["href"]
            full_url = urljoin(self.url, href)
            if urlparse(full_url).netloc.endswith("gov.br"):
                yield full_url.split("#", 1)[0]

    def title(self) -> str | None:
        title_tag = self.soup_obj.find("title")
        return title_tag.get_text(strip=True) if title_tag else None

    def description(self) -> str | None:
        meta = self.soup_obj.find("meta", attrs={"name": "description"})
        return meta["content"].strip() if meta and meta.has_attr("content") else None

    def text(self) -> str:
        # Remove scripts/style tags for a cleaner body text
        for el in self.soup_obj(["script", "style"]):
            el.decompose()
        return self.soup_obj.get_text(separator=" ", strip=True)

    # --------------------------------------------------------------------- #
    # Convenience
    # --------------------------------------------------------------------- #

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title(),
            "description": self.description(),
            "text": self.text(),
        }


# --------------------------------------------------------------------------- #
# Crawler
# --------------------------------------------------------------------------- #


def crawl(start_url: str = BASE_URL) -> list[IRPFPage]:
    """Breadth‑first crawl limited to the IRPF area of *gov.br* site."""
    queue: Set[str] = {start_url}
    seen: Set[str] = set()
    pages: list[IRPFPage] = []

    progress = tqdm(desc="Crawling", unit="page")
    while queue:
        url = queue.pop()
        if url in seen:
            continue
        progress.set_postfix_str(url[:60])
        page = IRPFPage(url)
        try:
            page._scrape()
        except requests.HTTPError as exc:
            logger.warning("Failed to fetch %s (%s)", url, exc)
            continue

        pages.append(page)
        seen.add(url)

        for link in page.iter_links():
            if link.startswith(start_url) and link not in seen:
                queue.add(link)

        progress.update()
    progress.close()
    logger.info("Crawled %d pages", len(pages))
    return pages


# --------------------------------------------------------------------------- #
# Extraction helpers
# --------------------------------------------------------------------------- #


def extract_structured(pages: Iterable[IRPFPage]) -> list[dict]:
    """Download each IRPF page again with *trafilatura* to extract metadata.

    *trafilatura* does its own fetching; the returned string is processed to JSON.
    """
    structured: list[dict] = []
    for page in tqdm(pages, desc="Extracting", unit="page"):
        raw = fetch_url(page.url)
        if raw is None:
            logger.warning("Trafilatura failed for %s", page.url)
            continue
        data = extract(raw, output_format="json", with_metadata=True)
        if data:
            structured.append(data)
    logger.info("Extracted %d JSON items", len(structured))
    return structured


# --------------------------------------------------------------------------- #
# CLI entry‑point
# --------------------------------------------------------------------------- #


def _parse_cli_args(argv: list[str]) -> Path:
    import argparse

    parser = argparse.ArgumentParser(description="IRPF crawler/extractor")
    parser.add_argument(
        "--output", "-o", type=Path, default=Path("knowledge_base/dados/textos_receita.json"),
        help="Path to write the extracted JSON (default: %(default)s)",
    )
    args = parser.parse_args(argv)
    return args.output


def main(argv: list[str] | None = None) -> None:
    argv = argv or sys.argv[1:]
    output_path = _parse_cli_args(argv)

    pages = crawl()
    structured_data = extract_structured(pages)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fp:
        json.dump(structured_data, fp, ensure_ascii=False, indent=2)

    logger.info("Saved knowledge base to %s", output_path.resolve())

if __name__ == "__main__":  # pragma: no cover
    main()
