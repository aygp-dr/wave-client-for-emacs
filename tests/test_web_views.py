"""Browser views (src/wave_client_server/web.py): /admin and /app.

The pages themselves require HTTP Basic, so the browser prompts on first load
and reuses the credentials for the page's /api fetches. Each test that needs
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
def test_no_credentials_is_401_with_challenge(path, realm):
    response = client.get(path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == f'Basic realm="{realm}"'


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
