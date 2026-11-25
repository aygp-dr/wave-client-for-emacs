"""Browser views (src/wave_client_server/web.py): /login, /admin and /app.

The pages take HTTP Basic or the /login mock cookie, and redirect to /login
without either. Each test that needs
a user inserts its own uniquely named one, and removes it afterwards.
"""

import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from wave_client_server.wave_server import SessionLocal, Wave, Wavelet, app

client = TestClient(app)
SCITTLE_URL = "https://cdn.jsdelivr.net/npm/scittle@0.8.33/dist/scittle.js"


@pytest.fixture
def user_address():
    tag = uuid.uuid4().hex[:6]
    address = f"web{tag}@localhost"
    wave_id = f"localhost!w+web{tag}"
    now = datetime.utcnow()
    db = SessionLocal()
    db.add(Wave(wave_id=wave_id, creator=address))
    db.add(Wavelet(wave_id=wave_id, wavelet_id="localhost!conv+root", creator=address,
                   creation_time=now, last_modified_time=now, version=1,
                   participants=[address], docs={"main": {"content": ["hello"]}}))
    db.commit()
    db.close()
    yield address
    db = SessionLocal()
    db.query(Wavelet).filter_by(wave_id=wave_id).delete()
    db.query(Wave).filter_by(wave_id=wave_id).delete()
    db.commit()
    db.close()


def local_part(address):
    return address.split("@")[0]


@pytest.mark.parametrize("path, realm", [("/admin", "wave-admin"), ("/app", "wave")])
def test_no_credentials_with_mock_login_off_is_401_with_challenge(path, realm, monkeypatch):
    monkeypatch.setenv("WAVE_MOCK_LOGIN", "0")
    response = client.get(path, follow_redirects=False)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == f'Basic realm="{realm}"'
    assert client.get("/login").status_code == 404


@pytest.mark.parametrize("path", ["/admin", "/app"])
def test_no_credentials_redirects_to_login(path):
    response = TestClient(app).get(path, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_api_without_credentials_stays_401():
    assert TestClient(app).get("/api/me").status_code == 401


@pytest.fixture
def mock_users(monkeypatch):
    """An admin and a plain user sharing one wave, offered on /login."""
    tag = uuid.uuid4().hex[:6]
    admin, plain = f"adm{tag}@localhost", f"pln{tag}@localhost"
    wave_id = f"localhost!w+mock{tag}"
    now = datetime.utcnow()
    db = SessionLocal()
    db.add(Wave(wave_id=wave_id, creator=admin))
    db.add(Wavelet(wave_id=wave_id, wavelet_id="localhost!conv+root", creator=admin,
                   creation_time=now, last_modified_time=now, version=1,
                   participants=[admin, plain], docs={"main": {"content": ["hello"]}}))
    db.commit()
    db.close()
    monkeypatch.setenv("WAVE_MOCK_USERS", f"{local_part(admin)},{local_part(plain)},ghost{tag}")
    monkeypatch.setenv("WAVE_ADMINS", local_part(admin))
    yield admin, plain
    db = SessionLocal()
    db.query(Wavelet).filter_by(wave_id=wave_id).delete()
    db.query(Wave).filter_by(wave_id=wave_id).delete()
    db.commit()
    db.close()


def test_login_page_lists_known_mock_users_and_marks_admin(mock_users):
    admin, plain = mock_users
    text = TestClient(app).get("/login").text
    assert f'<option value="{admin}">{local_part(admin)} (admin)</option>' in text
    assert f'<option value="{plain}">{local_part(plain)}</option>' in text
    assert "ghost" not in text, "users in no wave cannot sign in, so are not offered"


def test_mock_login_opens_app_and_api(mock_users):
    _, plain = mock_users
    browser = TestClient(app)
    response = browser.post("/login", data={"user": plain, "to": "/app"}, follow_redirects=False)
    assert (response.status_code, response.headers["location"]) == (303, "/app")
    assert browser.get("/app").status_code == 200
    me = browser.get("/api/me").json()
    assert (me["address"], me["is_admin"]) == (plain, False)
    assert browser.get("/admin", follow_redirects=False).headers["location"] == "/login?error=not-admin"
    assert browser.get("/api/admin/stats").status_code == 401
    browser.get("/logout")
    assert browser.get("/app", follow_redirects=False).status_code == 303


def test_mock_admin_reaches_admin_page_and_api(mock_users):
    admin, _ = mock_users
    browser = TestClient(app)
    response = browser.post("/login", data={"user": admin, "to": "/admin"}, follow_redirects=False)
    assert response.headers["location"] == "/admin"
    assert browser.get("/admin").status_code == 200
    assert browser.get("/api/admin/stats").status_code == 200
    assert browser.get("/api/me").json()["is_admin"] is True


def test_admin_user_by_basic_auth_reaches_admin(mock_users):
    admin, plain = mock_users
    assert client.get("/api/admin/stats", auth=(local_part(admin), local_part(admin))).status_code == 200
    assert client.get("/api/admin/stats", auth=(local_part(plain), local_part(plain))).status_code == 401


def test_login_rejects_users_not_offered(mock_users):
    browser = TestClient(app)
    response = browser.post("/login", data={"user": "mallory"}, follow_redirects=False)
    assert response.headers["location"] == "/login?error=unknown"
    assert "wave_mock_user" not in browser.cookies


def test_admin_wrong_credentials_is_401():
    response = client.get("/admin", auth=("admin", "not-the-password"))
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == 'Basic realm="wave-admin"'


def test_app_wrong_credentials_is_401(user_address):
    response = client.get("/app", auth=(local_part(user_address), "wrong"))
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == 'Basic realm="wave"'


def test_app_unknown_user_is_401():
    response = client.get("/app", auth=("nobody-" + uuid.uuid4().hex[:6], "x"))
    assert response.status_code == 401


def test_user_credentials_on_admin_is_401(user_address):
    name = local_part(user_address)
    assert client.get("/app", auth=(name, name)).status_code == 200
    response = client.get("/admin", auth=(name, name))
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == 'Basic realm="wave-admin"'


def test_admin_page_with_admin_credentials():
    response = client.get("/admin", auth=("admin", "admin"))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert SCITTLE_URL in response.text
    assert 'type="application/x-scittle" src="/web/admin.cljs"' in response.text
    assert "admin:admin" not in response.text


def test_app_page_with_user_credentials(user_address):
    name = local_part(user_address)
    response = client.get("/app", auth=(name, name))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert SCITTLE_URL in response.text
    assert 'type="application/x-scittle" src="/web/app.cljs"' in response.text
    assert name not in response.text


@pytest.mark.parametrize("file_name, namespace", [("app.cljs", "(ns wave.app"),
                                                   ("admin.cljs", "(ns wave.admin")])
def test_cljs_sources_are_served(file_name, namespace):
    response = client.get(f"/web/{file_name}")
    assert response.status_code == 200
    assert namespace in response.text


@pytest.mark.parametrize("file_name", ["app.html", "../web.py", "secret.cljs"])
def test_only_listed_sources_are_served(file_name):
    assert client.get(f"/web/{file_name}").status_code == 404


def test_pages_are_not_in_openapi():
    paths = client.get("/api/openapi.json").json()["paths"]
    assert "/admin" not in paths and "/app" not in paths
