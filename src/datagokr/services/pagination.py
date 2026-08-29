"""Shared response-envelope parsing and page-iteration helpers.

``services.openapi`` and ``services.standard`` each implement a ``list()``
method against a different data.go.kr response convention (different
envelope key casing, different total-count/error-code semantics, different
filter/param naming) -- that part is genuinely endpoint-specific and is
intentionally NOT unified here.

What *is* identical between the two modules is (a) decoding the raw JSON/XML
response body into a plain mapping plus a handful of small coercion helpers,
and (b) the page-by-page iteration loop that decides when to stop paging once
a ``list()`` method exists. Both are extracted here so the two service
modules stay in sync instead of drifting independently.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Mapping
from typing import Any, Protocol, TypeVar
from xml.etree import ElementTree


def parse_response(content: bytes) -> Mapping[str, Any]:
    """Decode a raw data.go.kr response body (JSON or XML) into a mapping."""
    stripped = content.lstrip()
    if stripped.startswith((b"{", b"[")):
        loaded = json.loads(content.decode("utf-8-sig"))
        return loaded if isinstance(loaded, Mapping) else {"response": {"body": {"items": loaded}}}
    return xml_to_mapping(content)


def xml_to_mapping(content: bytes) -> Mapping[str, Any]:
    root = ElementTree.fromstring(content)
    return {root.tag: element_to_value(root)}


def element_to_value(element: ElementTree.Element) -> Any:
    children = list(element)
    text = (element.text or "").strip()
    if not children:
        return text
    grouped: dict[str, Any] = {}
    for child in children:
        value = element_to_value(child)
        existing = grouped.get(child.tag)
        if existing is None:
            grouped[child.tag] = value
        elif isinstance(existing, list):
            existing.append(value)
        else:
            grouped[child.tag] = [existing, value]
    return grouped


def first(raw: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = raw.get(key)
        if value not in (None, ""):
            return value
    return None


def int_value(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default


def optional_int_value(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class _PageLike(Protocol):
    items: list[Any]
    num_of_rows: int

    @property
    def total_pages(self) -> int: ...


PageT = TypeVar("PageT", bound=_PageLike)


def iter_pages(
    list_fn: Callable[..., PageT],
    *,
    num_of_rows: Any,
    max_pages: int | None,
    filters: Mapping[str, Any],
) -> Iterator[PageT]:
    """Page through ``list_fn`` until an end-of-results condition is hit.

    ``list_fn`` is expected to accept ``page_no``/``num_of_rows`` keyword
    arguments plus arbitrary filters -- this is exactly ``self.list`` on
    each of the two service classes.

    Stops when: a page comes back with no items, ``max_pages`` is reached,
    the declared total page count is reached (only trusted when the page
    has no ``total_count_known`` attribute, or has one that is truthy --
    see ``StandardOpenApiService.list``, which sets it to ``False`` when the
    upstream response omitted ``totalCount``), or a short page is returned.
    """
    page_no = 1
    while True:
        page = list_fn(page_no=page_no, num_of_rows=num_of_rows, **filters)
        yield page
        if not page.items:
            return
        if max_pages is not None and page_no >= max_pages:
            return
        total_count_known = getattr(page, "total_count_known", True)
        if total_count_known and page.total_pages and page_no >= page.total_pages:
            return
        if len(page.items) < page.num_of_rows:
            return
        page_no += 1


def iter_all(
    iter_pages_fn: Callable[..., Iterator[PageT]],
    *,
    num_of_rows: Any,
    max_pages: int | None,
    filters: Mapping[str, Any],
) -> Iterator[Any]:
    """Flatten ``iter_pages_fn``'s pages into a single item stream."""
    for page in iter_pages_fn(num_of_rows=num_of_rows, max_pages=max_pages, **filters):
        yield from page.items
