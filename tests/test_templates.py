"""Static checks on the template sources."""
import pathlib
import re

TEMPLATES = pathlib.Path(__file__).resolve().parent.parent / 'templates'
POST_FORM = re.compile(r'<form\b[^>]*method="post"[^>]*>(.*?)</form>', re.IGNORECASE | re.DOTALL)


def test_every_post_form_carries_a_csrf_token():
    checked = 0
    for path in TEMPLATES.rglob('*.html'):
        for body in POST_FORM.findall(path.read_text(encoding='utf-8')):
            checked += 1
            assert 'csrf_input()' in body, f'{path.relative_to(TEMPLATES)} has a POST form without a CSRF token'
    assert checked >= 10


def test_templates_use_no_inline_scripts_or_handlers():
    """The content security policy forbids them, so they would silently not run."""
    for path in TEMPLATES.rglob('*.html'):
        text = path.read_text(encoding='utf-8')
        assert not re.search(r'<script(?![^>]*\bsrc=)', text), path.name
        assert not re.search(r'\son[a-z]+="', text), path.name
        assert 'style="' not in text, path.name


def test_nothing_is_marked_safe():
    for path in TEMPLATES.rglob('*.html'):
        assert '|safe' not in path.read_text(encoding='utf-8'), path.name
