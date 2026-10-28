"""Server-side input checks. Every message here is safe to show to the user."""
import re
from datetime import datetime
from decimal import Decimal

NUMBER = re.compile(r'[+-]?(\d+(\.\d*)?|\.\d+)', re.ASCII)
INTEGER = re.compile(r'[+-]?\d+', re.ASCII)
EMAIL = re.compile(r'[^@\s]+@[^@\s]+\.[^@\s]+')
ACADEMIC_YEAR = re.compile(r'(\d{4})-(\d{4})', re.ASCII)
EMAIL_MAX_LENGTH = 100


class ValidationError(ValueError):
    """A form value is missing or unacceptable."""


def _blank(raw):
    return raw is None or str(raw).strip() == ''


def _check_range(label, number, minimum, maximum):
    if minimum is not None and number < minimum:
        raise ValidationError(f'{label} must be at least {minimum}.')
    if maximum is not None and number > maximum:
        raise ValidationError(f'{label} must be at most {maximum}.')


def clean_text(label, raw, max_length, required=True):
    value = '' if raw is None else str(raw).strip()
    if not value:
        if required:
            raise ValidationError(f'{label} is required.')
        return None
    if len(value) > max_length:
        raise ValidationError(f'{label} must be at most {max_length} characters.')
    return value


def parse_decimal(label, raw, minimum=None, maximum=None, places=2, required=True):
    """Parse a plain decimal such as `42.5`. Rejects nan, inf, exponents and separators."""
    if _blank(raw):
        if required:
            raise ValidationError(f'{label} is required.')
        return None
    text = str(raw).strip()
    if not NUMBER.fullmatch(text):
        raise ValidationError(f'{label} must be a number.')
    number = Decimal(text)
    if -number.as_tuple().exponent > places:
        raise ValidationError(f'{label} can have at most {places} decimal places.')
    _check_range(label, number, minimum, maximum)
    return number


def parse_int(label, raw, minimum=None, maximum=None, required=True):
    if _blank(raw):
        if required:
            raise ValidationError(f'{label} is required.')
        return None
    text = str(raw).strip()
    if not INTEGER.fullmatch(text):
        raise ValidationError(f'{label} must be a whole number.')
    number = int(text)
    _check_range(label, number, minimum, maximum)
    return number


def parse_date(label, raw, required=True):
    if _blank(raw):
        if required:
            raise ValidationError(f'{label} is required.')
        return None
    try:
        return datetime.strptime(str(raw).strip(), '%Y-%m-%d').date()
    except ValueError:
        raise ValidationError(f'{label} must be a date in YYYY-MM-DD format.') from None


def parse_email(label, raw, required=False):
    value = clean_text(label, raw, EMAIL_MAX_LENGTH, required)
    if value is not None and not EMAIL.fullmatch(value):
        raise ValidationError(f'{label} must be a valid email address.')
    return value


def parse_academic_year(label, raw, required=False):
    """`2024-2025` style: two years, the second one year after the first."""
    value = clean_text(label, raw, 9, required)
    if value is None:
        return None
    match = ACADEMIC_YEAR.fullmatch(value)
    if not match or int(match.group(2)) != int(match.group(1)) + 1:
        raise ValidationError(f'{label} must look like 2024-2025 (YYYY-YYYY, consecutive years).')
    return value
