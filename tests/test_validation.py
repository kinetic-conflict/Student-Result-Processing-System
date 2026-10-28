from datetime import date
from decimal import Decimal

import pytest

from services.validation import (ValidationError, clean_text, parse_date, parse_decimal,
                                 parse_int)


def test_clean_text_trims_whitespace():
    assert clean_text('Name', '  Asha  ', 50) == 'Asha'


def test_clean_text_rejects_blank_when_required():
    with pytest.raises(ValidationError, match='Name is required'):
        clean_text('Name', '   ', 50)


def test_clean_text_returns_none_for_blank_optional():
    assert clean_text('Email', '', 100, required=False) is None
    assert clean_text('Email', None, 100, required=False) is None


def test_clean_text_enforces_max_length():
    with pytest.raises(ValidationError, match='at most 5 characters'):
        clean_text('Code', 'abcdef', 5)


def test_parse_decimal_accepts_plain_numbers():
    assert parse_decimal('Marks', '42.5') == Decimal('42.5')
    assert parse_decimal('Marks', ' 0 ') == Decimal('0')


@pytest.mark.parametrize('bad', ['abc', 'nan', 'NaN', 'inf', '-Infinity', '1,5', '1 000',
                                 '1_000', '1e3', '0x10', '٣', '--1', '.'])
def test_parse_decimal_rejects_anything_that_is_not_a_plain_number(bad):
    with pytest.raises(ValidationError, match='Marks must be a number'):
        parse_decimal('Marks', bad)


def test_parse_decimal_blank_is_an_error_unless_optional():
    with pytest.raises(ValidationError, match='Marks is required'):
        parse_decimal('Marks', '')
    assert parse_decimal('Marks', '', required=False) is None


def test_parse_decimal_range_is_inclusive_and_names_the_bounds():
    assert parse_decimal('Marks', '0', minimum=0, maximum=50) == 0
    assert parse_decimal('Marks', '50', minimum=0, maximum=50) == 50
    with pytest.raises(ValidationError, match='at least 0'):
        parse_decimal('Marks', '-0.01', minimum=0, maximum=50)
    with pytest.raises(ValidationError, match='at most 50'):
        parse_decimal('Marks', '50.01', minimum=0, maximum=50)


def test_parse_decimal_limits_decimal_places():
    assert parse_decimal('Marks', '1.25') == Decimal('1.25')
    with pytest.raises(ValidationError, match='at most 2 decimal places'):
        parse_decimal('Marks', '1.255')


def test_parse_int():
    assert parse_int('Semester', '3', minimum=1, maximum=10) == 3
    for bad in ('3.5', 'x', '', '1e2'):
        with pytest.raises(ValidationError):
            parse_int('Semester', bad)
    with pytest.raises(ValidationError, match='at most 10'):
        parse_int('Semester', '11', minimum=1, maximum=10)


def test_parse_date():
    assert parse_date('Exam date', '2025-12-15') == date(2025, 12, 15)
    assert parse_date('Exam date', '', required=False) is None
    with pytest.raises(ValidationError, match='YYYY-MM-DD'):
        parse_date('Exam date', '15/12/2025')
    with pytest.raises(ValidationError, match='YYYY-MM-DD'):
        parse_date('Exam date', '2025-02-30')


def test_parse_email():
    from services.validation import parse_email
    assert parse_email('Email', ' a.b@example.test ') == 'a.b@example.test'
    assert parse_email('Email', '', required=False) is None
    for bad in ('nope', 'a@b', 'a b@c.d', '@x.y', 'a@@x.y'):
        with pytest.raises(ValidationError, match='valid email'):
            parse_email('Email', bad)
    with pytest.raises(ValidationError, match='at most 100'):
        parse_email('Email', 'a' * 96 + '@x.yz')


def test_parse_academic_year():
    from services.validation import parse_academic_year
    assert parse_academic_year('Academic year', '2024-2025') == '2024-2025'
    assert parse_academic_year('Academic year', '', required=False) is None
    for bad in ('2024-2026', '2025-2024', '24-25', '2024/2025', '2024-25', 'abcd-efgh'):
        with pytest.raises(ValidationError, match='YYYY-YYYY'):
            parse_academic_year('Academic year', bad)
