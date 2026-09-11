"""Termination rules for the shared page-iteration helper.

The interesting case is a page that comes back *short* without being the
last one. That happens whenever row-level validation drops rows from a full
upstream page: the caller sees fewer items than it asked for, which looks
exactly like the tail of the stream. Ending there truncates the data and
never raises, so the declared total is what has to settle it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from datagokr.services.pagination import iter_pages


@dataclass
class FakePage:
    items: list[Any] = field(default_factory=list)
    num_of_rows: int = 10
    total_count: int | None = 0
    total_count_known: bool = True

    @property
    def total_pages(self) -> int:
        if not self.total_count or self.num_of_rows <= 0:
            return 0
        return (self.total_count + self.num_of_rows - 1) // self.num_of_rows


def _pager(pages: list[FakePage]) -> tuple[Any, list[int]]:
    requested: list[int] = []

    def list_fn(*, page_no: int, num_of_rows: Any, **_filters: Any) -> FakePage:
        requested.append(page_no)
        return pages[page_no - 1]

    return list_fn, requested


def test_a_filtered_full_page_does_not_end_the_stream() -> None:
    # 30 rows upstream, 10 per page, but page 1 lost one row to validation.
    list_fn, requested = _pager(
        [
            FakePage(items=[object()] * 9, num_of_rows=10, total_count=30),
            FakePage(items=[object()] * 10, num_of_rows=10, total_count=30),
            FakePage(items=[object()] * 10, num_of_rows=10, total_count=30),
        ]
    )

    pages = list(iter_pages(list_fn, num_of_rows=10, max_pages=None, filters={}))

    assert requested == [1, 2, 3]
    assert sum(len(page.items) for page in pages) == 29


def test_a_short_page_that_accounts_for_the_total_ends_the_stream() -> None:
    list_fn, requested = _pager(
        [
            FakePage(items=[object()] * 10, num_of_rows=10, total_count=14),
            FakePage(items=[object()] * 4, num_of_rows=10, total_count=14),
        ]
    )

    pages = list(iter_pages(list_fn, num_of_rows=10, max_pages=None, filters={}))

    assert requested == [1, 2]
    assert sum(len(page.items) for page in pages) == 14


def test_without_a_trustworthy_total_an_empty_page_ends_the_stream() -> None:
    # StandardOpenApiService.list sets total_count_known=False when upstream
    # omitted totalCount. A short page then proves nothing.
    list_fn, requested = _pager(
        [
            FakePage(items=[object()] * 9, num_of_rows=10, total_count_known=False),
            FakePage(items=[object()] * 9, num_of_rows=10, total_count_known=False),
            FakePage(items=[], num_of_rows=10, total_count_known=False),
        ]
    )

    pages = list(iter_pages(list_fn, num_of_rows=10, max_pages=None, filters={}))

    assert requested == [1, 2, 3]
    assert sum(len(page.items) for page in pages) == 18


def test_max_pages_still_caps_the_walk() -> None:
    list_fn, requested = _pager(
        [
            FakePage(items=[object()] * 9, num_of_rows=10, total_count=100),
            FakePage(items=[object()] * 9, num_of_rows=10, total_count=100),
            FakePage(items=[object()] * 9, num_of_rows=10, total_count=100),
        ]
    )

    list(iter_pages(list_fn, num_of_rows=10, max_pages=2, filters={}))

    assert requested == [1, 2]
