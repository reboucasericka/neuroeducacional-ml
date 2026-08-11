"""Paginação server-side reutilizável."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from flask import request


ALLOWED_PER_PAGE = (20, 50, 100)
DEFAULT_PER_PAGE = 20


@dataclass
class PageResult:
    items: list[Any]
    page: int
    per_page: int
    total: int
    pages: int

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def prev_num(self) -> int | None:
        return self.page - 1 if self.has_prev else None

    @property
    def next_num(self) -> int | None:
        return self.page + 1 if self.has_next else None


def parse_page_args(
    *,
    default_per_page: int = DEFAULT_PER_PAGE,
    allowed: tuple[int, ...] = ALLOWED_PER_PAGE,
) -> tuple[int, int]:
    try:
        page = max(1, int(request.args.get("page") or 1))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = int(request.args.get("per_page") or default_per_page)
    except (TypeError, ValueError):
        per_page = default_per_page
    if per_page not in allowed:
        per_page = default_per_page
    return page, per_page


def paginate_query(query, *, page: int | None = None, per_page: int | None = None) -> PageResult:
    if page is None or per_page is None:
        page, per_page = parse_page_args()
    total = int(query.count())
    pages = max(1, (total + per_page - 1) // per_page) if total else 1
    if page > pages:
        page = pages
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    return PageResult(
        items=items,
        page=page,
        per_page=per_page,
        total=total,
        pages=pages,
    )


def pagination_query_string(*, page: int | None = None, per_page: int | None = None, **extra) -> str:
    """Preserva filtros atuais da query string ao mudar página/tamanho."""
    args = request.args.to_dict(flat=True)
    args.update({k: v for k, v in extra.items() if v is not None and v != ""})
    if page is not None:
        args["page"] = str(page)
    if per_page is not None:
        args["per_page"] = str(per_page)
    return urlencode(args)
