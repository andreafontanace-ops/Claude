import re

import pytest
from fastapi.testclient import TestClient

from sovweb.app import create_app
from sovweb.settings import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(database_url=f"sqlite:///{tmp_path / 'test.sqlite'}", secret_key="test", data_provider="demo",
                    ingest_token="tok-123")


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    return TestClient(app)


def csrf(client, path):
    html = client.get(path).text
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def signup(client, email="anna@example.com", company="Acme Pharma"):
    token = csrf(client, "/registrati")
    r = client.post("/registrati", data={"csrf": token, "email": email, "password": "password-lunga-1",
                                         "company": company, "name": "Anna"})
    assert r.status_code == 200, r.text  # dopo il redirect: pagina di benvenuto
    return r


def choose(client, categories, sites):
    html = client.get("/benvenuto").text
    token = re.search(r'name="csrf" value="([^"]+)"', html).group(1)
    ids = lambda name, labels: [re.search(rf'name="{name}" value="(\d+)"[^>]*>\s*<span><b>{re.escape(l)}</b>', html).group(1)
                                for l in labels]
    return client.post("/benvenuto", data={"csrf": token, "category": ids("category", categories),
                                           "site": ids("site", sites)})


def set_brands(client, own="", competitor="", skip=False):
    html = client.get("/benvenuto/marchi").text
    token = re.search(r'name="csrf" value="([^"]+)"', html).group(1)
    data = {"csrf": token}
    for cat_id in re.findall(r'name="own_(\d+)"', html):
        data[f"own_{cat_id}"] = own
        data[f"competitor_{cat_id}"] = competitor
    if skip:
        data["skip"] = "1"
    return client.post("/benvenuto/marchi", data=data)
