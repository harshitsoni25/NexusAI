"""Detection of observable site characteristics from retrieved content.

The analyzer inspects HTML that was already retrieved through approved means and
reports what it observes -- static content, signs of client-side rendering,
pagination shapes, tables, card lists, structured metadata, downloadable links.
It looks only at public markup; it performs no protection bypass, no stealth, and
no probing beyond what retrieval already fetched.

Every detection carries a confidence, because these are heuristics on markup, not
guarantees. A ``<link rel="next">`` is strong evidence of pagination; a bare
"Load more" string is weaker. Reporting that difference honestly is the point --
the recommender downstream weighs confidence, and a caller can set a threshold.
"""

from __future__ import annotations

import re

from nexusai.domain.model.analysis import (
    AnalysisResult,
    Characteristic,
    Confidence,
    Observation,
)

_SCRIPT_HEAVY = re.compile(rb"<script[^>]*>", re.IGNORECASE)
_JSON_LD = re.compile(rb'<script[^>]*type=["\']application/ld\+json["\']', re.IGNORECASE)
_TABLE = re.compile(rb"<table[\s>]", re.IGNORECASE)
_NEXT_LINK = re.compile(rb'rel=["\']next["\']', re.IGNORECASE)
_PAGE_PARAM = re.compile(rb"[?&](page|p)=", re.IGNORECASE)
_OFFSET_PARAM = re.compile(rb"[?&](offset|start|skip)=", re.IGNORECASE)
_CURSOR_PARAM = re.compile(rb"[?&](cursor|after|before)=", re.IGNORECASE)
_INFINITE = re.compile(rb"infinite[\s-]?scroll|data-infinite", re.IGNORECASE)
_LOAD_MORE = re.compile(rb"load[\s-]?more", re.IGNORECASE)
_LAZY = re.compile(rb'loading=["\']lazy["\']|data-src=', re.IGNORECASE)
_CARD = re.compile(rb'class=["\'][^"\']*(card|product|item|listing)', re.IGNORECASE)
_META = re.compile(rb'<meta[^>]+property=["\']og:', re.IGNORECASE)
_DOWNLOAD = re.compile(rb'href=["\'][^"\']+\.(csv|pdf|xlsx?|zip|json)["\']', re.IGNORECASE)
_APP_JSON = re.compile(rb"fetch\(|application/json|/api/", re.IGNORECASE)
_GRAPHQL = re.compile(rb"/graphql|graphql query", re.IGNORECASE)


def analyse_html(target: str, content: bytes) -> AnalysisResult:
    """Detect observable characteristics in ``content`` for ``target``.

    Args:
        target: The URL the content came from.
        content: The raw HTML bytes already retrieved.
    """
    observations: list[Observation] = []
    warnings: list[str] = []

    text_length = len(re.sub(rb"<[^>]+>", b"", content).strip())
    script_count = len(_SCRIPT_HEAVY.findall(content))

    if text_length > 200:
        observations.append(
            Observation(
                characteristic=Characteristic.STATIC_HTML,
                confidence=Confidence.HIGH,
                evidence=f"{text_length} bytes of text present in the static response",
            )
        )
    if script_count >= 5 and text_length < 400:
        observations.append(
            Observation(
                characteristic=Characteristic.JS_RENDERING,
                confidence=Confidence.MEDIUM,
                evidence=f"{script_count} script tags with little static text",
            )
        )

    _add_if(
        observations,
        _NEXT_LINK,
        content,
        Characteristic.PAGINATION,
        Confidence.HIGH,
        "a rel=next link",
    )
    _add_if(
        observations,
        _PAGE_PARAM,
        content,
        Characteristic.PAGINATION,
        Confidence.MEDIUM,
        "a page query parameter",
    )
    _add_if(
        observations,
        _OFFSET_PARAM,
        content,
        Characteristic.OFFSET_PAGINATION,
        Confidence.MEDIUM,
        "an offset parameter",
    )
    _add_if(
        observations,
        _CURSOR_PARAM,
        content,
        Characteristic.CURSOR_PAGINATION,
        Confidence.MEDIUM,
        "a cursor parameter",
    )
    _add_if(
        observations,
        _INFINITE,
        content,
        Characteristic.INFINITE_SCROLL,
        Confidence.MEDIUM,
        "infinite-scroll markup",
    )
    _add_if(
        observations,
        _LOAD_MORE,
        content,
        Characteristic.LOAD_MORE,
        Confidence.LOW,
        "a 'load more' control",
    )
    _add_if(
        observations,
        _LAZY,
        content,
        Characteristic.LAZY_LOADING,
        Confidence.MEDIUM,
        "lazy-loaded resources",
    )
    _add_if(
        observations,
        _TABLE,
        content,
        Characteristic.TABLES,
        Confidence.HIGH,
        "one or more HTML tables",
    )
    _add_if(
        observations,
        _CARD,
        content,
        Characteristic.CARD_LIST,
        Confidence.MEDIUM,
        "repeated card/list structures",
    )
    _add_if(
        observations,
        _JSON_LD,
        content,
        Characteristic.JSON_LD,
        Confidence.HIGH,
        "a JSON-LD script block",
    )
    _add_if(
        observations,
        _META,
        content,
        Characteristic.STRUCTURED_METADATA,
        Confidence.MEDIUM,
        "Open Graph metadata",
    )
    _add_if(
        observations,
        _DOWNLOAD,
        content,
        Characteristic.DOWNLOADABLE,
        Confidence.MEDIUM,
        "downloadable resource links",
    )
    _add_if(
        observations,
        _APP_JSON,
        content,
        Characteristic.REST_ENDPOINT,
        Confidence.LOW,
        "references to a JSON API",
    )
    _add_if(
        observations,
        _GRAPHQL,
        content,
        Characteristic.GRAPHQL_ENDPOINT,
        Confidence.LOW,
        "references to a GraphQL endpoint",
    )

    if not observations:
        warnings.append("no recognisable structure was detected in the response")

    return AnalysisResult(
        target=target,
        observations=observations,
        warnings=warnings,
        limitations=(
            "detection is heuristic and based only on the retrieved markup",
            "dynamic behaviour is inferred, not executed",
        ),
    )


def _add_if(
    observations: list[Observation],
    pattern: re.Pattern[bytes],
    content: bytes,
    characteristic: Characteristic,
    confidence: Confidence,
    evidence: str,
) -> None:
    if pattern.search(content):
        observations.append(
            Observation(characteristic=characteristic, confidence=confidence, evidence=evidence)
        )
