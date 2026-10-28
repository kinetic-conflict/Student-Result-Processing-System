"""Page arithmetic for list screens. Bad input is clamped, never an error."""
from collections import namedtuple

Page = namedtuple('Page', 'page pages per_page offset total has_prev has_next')

DEFAULT_PER_PAGE = 25


def paginate(total, raw_page, per_page=DEFAULT_PER_PAGE):
    pages = max(1, -(-total // per_page))
    try:
        page = int(raw_page)
    except (TypeError, ValueError):
        page = 1
    page = min(max(page, 1), pages)
    return Page(page, pages, per_page, (page - 1) * per_page, total, page > 1, page < pages)
