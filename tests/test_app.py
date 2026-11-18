import pytest
from fastapi.testclient import TestClient

from bits_and_bots import database
from bits_and_bots.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/about",
        "/blog",
        "/microbit",
        "/python",
        "/resources",
        "/safety/online",
        "/safety/ai",
        "/donate",
        "/contact",
        "/consent",
    ],
)
def test_public_pages_render(client, path):
    response = client.get(path)

    assert response.status_code == 200
    assert "Bits and Bots Code Club" in response.text


def test_shared_theme_is_rendered_as_raw_css(client):
    response = client.get("/")
    stylesheet = client.get("/static/styles.css")

    assert response.status_code == 200
    assert 'href="/static/styles.css"' in response.text
    assert stylesheet.status_code == 200
    assert "--paper:#fbff91" in stylesheet.text
    assert "--font:'Space Grotesk'" in stylesheet.text
    assert "transform:none" in stylesheet.text


def test_contact_form_stores_message(client):
    response = client.post(
        "/contact",
        data={
            "name": "Parent Example",
            "email": "parent@example.test",
            "phone": "01234567890",
            "child_year_group": "Year 4",
            "message": "Please contact me about joining.",
        },
    )

    assert response.status_code == 200
    assert "Thank you" in response.text
    with database.db() as conn:
        message = conn.execute(
            "SELECT name, email, message FROM contact_messages"
        ).fetchone()
    assert tuple(message) == (
        "Parent Example",
        "parent@example.test",
        "Please contact me about joining.",
    )


def test_consent_form_stores_submission(client):
    response = client.post(
        "/consent",
        data={
            "child_first_name": "Taylor",
            "child_last_initial": "R",
            "child_year_group": "Year 4",
            "parent_name": "Parent Example",
            "parent_email": "parent@example.test",
            "parent_phone": "01234567890",
            "emergency_contact": "Second Parent 01234567891",
            "medical_notes": "",
            "photo_consent": "no",
            "walking_home_alone": "no",
            "ai_tools_consent": "yes",
            "signature_name": "Parent Example",
            "signed_date": "2026-11-13",
        },
    )

    assert response.status_code == 200
    assert "Consent received" in response.text
    with database.db() as conn:
        submission = conn.execute(
            "SELECT child_first_name, parent_email, ai_tools_consent "
            "FROM consent_submissions"
        ).fetchone()
    assert tuple(submission) == ("Taylor", "parent@example.test", "yes")


def test_volunteer_dashboard_requires_login(client):
    response = client.get("/volunteers", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/volunteers/login"


def test_seeded_admin_can_log_in_and_view_dashboard(client):
    response = client.post(
        "/volunteers/login",
        data={"email": "admin@yourcodeclub.org.uk", "password": "change-me-now"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/volunteers"
    dashboard = client.get("/volunteers")
    assert dashboard.status_code == 200
    assert "Club Admin" in dashboard.text
