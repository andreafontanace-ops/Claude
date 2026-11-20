import os
import re

import pytest
from fastapi.testclient import TestClient

from sovweb.app import create_app
from sovweb.settings import Settings


PG_URL = os.environ.get("SOV_TEST_DATABASE_URL", "")


@pytest.fixture
def settings(tmp_path):
    url = PG_URL or f"sqlite:///{tmp_path / 'test.sqlite'}"
    if PG_URL:  # database Postgres vero: si riparte da zero a ogni test
        from sovweb.db import Base, Database
        from sovweb import models  # noqa: F401

        Base.metadata.drop_all(Database(PG_URL).engine)
    return Settings(database_url=url, secret_key="test", data_provider="demo",
                    ingest_token="tok-123-prova-abcdefghijklmnop")


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
