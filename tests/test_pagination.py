import pytest

from services.pagination import paginate


def test_first_page_of_several():
    page = paginate(total=95, raw_page='1', per_page=25)
    assert (page.page, page.pages, page.offset, page.per_page) == (1, 4, 0, 25)
    assert not page.has_prev and page.has_next


def test_middle_and_last_pages():
    assert paginate(95, '2', 25).offset == 25
    last = paginate(95, '4', 25)
    assert last.offset == 75 and last.has_prev and not last.has_next


def test_exact_multiple_does_not_add_an_empty_page():
    assert paginate(50, '1', 25).pages == 2


@pytest.mark.parametrize('raw', [None, '', 'abc', '0', '-3', '1.5', '9' * 30])
def test_junk_or_out_of_range_input_is_clamped_not_an_error(raw):
    page = paginate(total=95, raw_page=raw, per_page=25)
    assert 1 <= page.page <= page.pages


def test_page_beyond_the_end_shows_the_last_page():
    assert paginate(95, '99', 25).page == 4


def test_no_rows_is_one_empty_page():
    page = paginate(0, '1', 25)
    assert (page.page, page.pages, page.offset) == (1, 1, 0)
    assert not page.has_prev and not page.has_next
