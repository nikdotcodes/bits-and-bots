import re
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from bits_and_bots import database
from bits_and_bots.main import app
from bits_and_bots.passwords import hash_password, verify_password
from bits_and_bots import security


class FakeQuery:
    def __init__(self):
        self.payload = None

    def insert(self, payload):
        self.payload = payload
        return self

    def execute(self):
        return SimpleNamespace(data=[{"id": 101}])


class FakeSupabase:
    def table(self, name):
        return FakeQuery()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(database, "get_client", lambda: FakeSupabase())
    with TestClient(app) as test_client:
        yield test_client


def csrf_token(response):
    match = re.search(
        r'name="_csrf" value="([^"]+)"', response.text
    )
    assert match, "form should contain a CSRF token"
    return match.group(1)


@pytest.mark.parametrize(
    "path",
    [
        "/", "/about", "/blog", "/microbit", "/python", "/resources",
        "/safety/online", "/safety/ai", "/donate", "/contact",
        "/consent", "/privacy-notice", "/volunteers/login",
    ],
)
def test_public_pages_render(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert "Bits and Bots Code Club" in response.text
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_csrf_token_is_present_and_cookie_is_set(client):
    response = client.get("/contact")
    assert response.status_code == 200
    assert csrf_token(response)
    assert "club_csrf" in response.cookies


def test_csrf_rejects_missing_token(client):
    client.get("/contact")
    response = client.post(
        "/contact",
        data={
            "name": "Example", "email": "parent@example.test",
            "message": "Please contact me",
        },
    )
    assert response.status_code == 403


def test_contact_form_accepts_valid_csrf_token(client):
    page = client.get("/contact")
    token = csrf_token(page)
    response = client.post(
        "/contact",
        data={
            "_csrf": token,
            "name": "Example Parent",
            "email": "parent@example.test",
            "phone": "",
            "child_year_group": "Year 4",
            "message": "Please contact me about joining.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/contact?sent=true"


def test_volunteer_dashboard_requires_login(client):
    response = client.get("/volunteers", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/volunteers/login"


def test_logout_is_not_available_as_get(client):
    response = client.get("/volunteers/logout", follow_redirects=False)
    assert response.status_code == 405


def test_password_hash_round_trip():
    encoded = hash_password("A-long-test-password-123!")
    assert encoded.startswith("scrypt$")
    assert verify_password("A-long-test-password-123!", encoded) == (True, False)
    assert verify_password("wrong-password", encoded) == (False, False)


def test_password_hash_rejects_extreme_length():
    with pytest.raises(ValueError):
        hash_password("x" * 1025)



def test_csrf_accepts_multipart_form_token(client):
    page = client.get("/consent")
    token = csrf_token(page)
    response = client.post(
        "/consent",
        data={
            "_csrf": token,
            "child_first_name": "Example",
            "child_last_initial": "E",
            "child_year_group": "Year 4",
            "parent_name": "Parent",
            "parent_email": "parent@example.test",
            "signature_name": "Parent",
            "signed_date": "2026-11-18",
        },
        files={"consent_file": ("scan.pdf", b"%PDF-test", "application/pdf")},
        follow_redirects=False,
    )
    # The fake Supabase client cannot store files; reaching the route's generic
    # failure redirect proves the multipart CSRF token was accepted.
    assert response.status_code == 303
    assert response.headers["location"] == "/consent?error=true"


def test_non_admin_is_rejected(monkeypatch):
    monkeypatch.setattr(
        security, "get_current_volunteer",
        lambda request: {
            "id": 1, "email": "volunteer@example.test", "is_admin": False,
        },
    )
    with TestClient(app) as test_client:
        response = test_client.get("/volunteers")
    assert response.status_code == 403
