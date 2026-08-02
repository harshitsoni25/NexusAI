"""Deterministic, in-memory mock websites for controlled tests.

These are pure Python builders that return the exact bytes a controlled site
would serve, with no network and no external process: static pages, paginated
listings (page-number, offset and cursor styles), a JSON API, JSON-LD metadata,
tables, cards, malformed and empty documents, duplicates, a robots.txt and a
sitemap. Tests drive the framework's parsers, extractors and analysers against
these fixtures so behaviour is reproducible and never depends on a public site.

Nothing here fetches anything. A "site" is a mapping from path to bytes, and the
helpers assemble that mapping for a given scenario.
"""

from __future__ import annotations

import json
from collections.abc import Mapping


def static_page(*, title: str = "Sample", body: str = "<p>content</p>") -> bytes:
    """Return a minimal, well-formed static HTML page."""
    return (
        f"<html><head><title>{title}</title></head>" f"<body><h1>{title}</h1>{body}</body></html>"
    ).encode()


def product_listing(count: int) -> bytes:
    """Return an HTML listing of ``count`` product cards."""
    cards = "".join(
        f'<div class="product" data-id="{i}">'
        f'<span class="name">Item {i}</span>'
        f'<span class="price">{i}.99</span>'
        f'<a class="detail" href="/item/{i}">details</a>'
        f"</div>"
        for i in range(count)
    )
    return f"<html><body><ul class='products'>{cards}</ul></body></html>".encode()


def paginated_page(page: int, *, total_pages: int, per_page: int = 5) -> bytes:
    """Return one page of a page-number-paginated listing with a next link."""
    start = page * per_page
    items = "".join(
        f'<li class="row"><span class="name">Row {start + i}</span></li>' for i in range(per_page)
    )
    next_link = (
        f'<a rel="next" href="/list?page={page + 1}">next</a>' if page + 1 < total_pages else ""
    )
    return f"<html><body><ul>{items}</ul>{next_link}</body></html>".encode()


def table_page(rows: int) -> bytes:
    """Return an HTML page with a data table of ``rows`` rows."""
    body = "".join(f"<tr><td>Name {i}</td><td>{i}</td></tr>" for i in range(rows))
    return (
        "<html><body><table><thead><tr><th>name</th><th>value</th></tr></thead>"
        f"<tbody>{body}</tbody></table></body></html>"
    ).encode()


def json_ld_page(*, name: str = "Widget", price: str = "9.99") -> bytes:
    """Return an HTML page carrying a JSON-LD Product block."""
    payload = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": name,
            "offers": {"@type": "Offer", "price": price, "priceCurrency": "USD"},
        }
    )
    return (
        "<html><head>"
        f'<script type="application/ld+json">{payload}</script>'
        "</head><body><h1>Product</h1></body></html>"
    ).encode()


def json_api_response(count: int, *, cursor: str | None = None) -> bytes:
    """Return a JSON API payload of ``count`` records with an optional cursor."""
    return json.dumps(
        {
            "records": [{"id": i, "name": f"Item {i}"} for i in range(count)],
            "next_cursor": cursor,
        }
    ).encode()


def malformed_html() -> bytes:
    """Return deliberately malformed HTML (unclosed tags)."""
    return b"<html><body><div><p>oops<span></body>"


def empty_page() -> bytes:
    """Return an empty document."""
    return b""


def duplicate_listing() -> bytes:
    """Return a listing where two records are exact duplicates."""
    return (
        b"<html><body><ul>"
        b'<li class="row"><span class="name">Same</span></li>'
        b'<li class="row"><span class="name">Same</span></li>'
        b'<li class="row"><span class="name">Different</span></li>'
        b"</ul></body></html>"
    )


def robots_txt(*, allow_all: bool = True) -> bytes:
    """Return a robots.txt, permissive or restrictive."""
    if allow_all:
        return b"User-agent: *\nAllow: /\nSitemap: https://mock.local/sitemap.xml\n"
    return b"User-agent: *\nDisallow: /private\nCrawl-delay: 2\n"


def sitemap_xml(paths: tuple[str, ...]) -> bytes:
    """Return a sitemap listing the given paths."""
    urls = "".join(f"<url><loc>https://mock.local{p}</loc></url>" for p in paths)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    ).encode()


def site_catalogue() -> Mapping[str, bytes]:
    """Assemble a small multi-page site as a path-to-bytes mapping."""
    return {
        "/": static_page(title="Home", body='<a href="/list?page=0">catalogue</a>'),
        "/list?page=0": paginated_page(0, total_pages=3),
        "/list?page=1": paginated_page(1, total_pages=3),
        "/list?page=2": paginated_page(2, total_pages=3),
        "/products": product_listing(10),
        "/table": table_page(5),
        "/product.jsonld": json_ld_page(),
        "/robots.txt": robots_txt(),
        "/sitemap.xml": sitemap_xml(("/", "/products", "/table")),
    }
