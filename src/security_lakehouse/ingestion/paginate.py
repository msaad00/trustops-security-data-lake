"""Generic cursor-pagination iterator.

Different APIs cursor differently (Okta ``Link: rel="next"``, Jira
``startAt``/``total``, AWS ``NextToken``). :func:`paginate` factors out the loop
so a runner supplies three small callables and gets a flat item stream, with a
page cap as a runaway guard.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any, TypeVar

Page = TypeVar("Page")
Item = TypeVar("Item")


def paginate(
    fetch_page: Callable[[Any | None], Page],
    extract_items: Callable[[Page], Iterable[Item]],
    next_cursor: Callable[[Page], Any | None],
    *,
    start_cursor: Any | None = None,
    max_pages: int = 1000,
) -> Iterator[Item]:
    """Yield items across pages until ``next_cursor`` returns None or the cap.

    ``fetch_page(cursor)`` returns a page; ``extract_items(page)`` its rows;
    ``next_cursor(page)`` the next cursor or None when exhausted.
    """
    cursor = start_cursor
    for _ in range(max_pages):
        page = fetch_page(cursor)
        yield from extract_items(page)
        cursor = next_cursor(page)
        if cursor is None:
            return
