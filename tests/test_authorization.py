"""Whole-app access rules, driven by the routes the app really registers."""
import pytest

from security import PUBLIC_ENDPOINTS, allowed_roles
from tests.helpers import csrf

ROLES = ('admin', 'faculty', 'student')


def route_calls(app):
    """Every (endpoint, method, url) the app serves, with `1` for any path parameter."""
    adapter = app.url_map.bind('localhost')
    for rule in app.url_map.iter_rules():
        if rule.endpoint in PUBLIC_ENDPOINTS:
            continue
        url = adapter.build(rule.endpoint, {name: 1 for name in rule.arguments})
        for method in sorted(rule.methods - {'HEAD', 'OPTIONS'}):
            yield rule.endpoint, method, url


def call(client, method, url):
    if method == 'POST':
        return client.post(url, data={'csrf_token': csrf(client)})
    return client.open(url, method=method)


def test_there_are_routes_to_check(app):
    assert len(list(route_calls(app))) > 20


def test_every_route_sends_anonymous_visitors_to_the_login_page(app):
    anonymous = app.test_client()
    for endpoint, method, url in route_calls(app):
        response = call(anonymous, method, url)
        assert response.status_code == 302, (endpoint, method)
        assert response.headers['Location'].startswith('/login'), (endpoint, method)


@pytest.mark.parametrize('role', ROLES)
def test_a_role_is_refused_everywhere_its_blueprint_does_not_list_it(app, sign_in, role):
    who = sign_in(role)
    refused = 0
    for endpoint, method, url in route_calls(app):
        allowed = allowed_roles(app, endpoint)
        if allowed is not None and role not in allowed:
            assert call(who.client, method, url).status_code == 403, (endpoint, method)
            refused += 1
    assert refused or role == 'admin'


@pytest.mark.parametrize('role', ROLES)
def test_allowed_routes_never_crash_on_an_empty_database(app, sign_in, role):
    who = sign_in(role)
    for endpoint, method, url in route_calls(app):
        allowed = allowed_roles(app, endpoint)
        if allowed is None or role in allowed:
            status = call(who.client, method, url).status_code
            assert status < 500, (role, endpoint, method, status)


def test_a_tampered_session_role_does_nothing(app, sign_in):
    """The role comes from the database on every request, never from the cookie."""
    student = sign_in('student')
    with student.client.session_transaction() as session:
        session['role'] = 'admin'
        session['uid'] = session['uid']
    assert student.client.get('/students').status_code == 403
