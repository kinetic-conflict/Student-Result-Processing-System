"""Small helpers shared by route modules."""
from flask import request

from services.validation import ValidationError, parse_int


def optional_id(name):
    """A positive id from the query string, or None when absent or junk."""
    try:
        return parse_int(name, request.args.get(name), minimum=1, required=False)
    except ValidationError:
        return None


def client_ip():
    return request.remote_addr
