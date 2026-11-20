import re

from sqlalchemy import select

from amazon_sov.parser import SerpItem
from conftest import choose, set_brands, signup
from sovweb.collector import ingest_run
from sovweb.db import Database
from sovweb.models import Feed, Notification


def item(i, brand):
    return SerpItem(asin=f"P{brand}{i}", slot=i, title=f"{brand} ferro 30 compresse", brand_raw=brand,
                    sponsored=False, placement="organic")


def test_alerts_after_second_run(client, settings):
    signup(client)
    choose(client, ["Ferro"], ["TopFarmacia"])
    set_brands(client, own="Alfa")
    database = Database(settings.database_url)
    with database.Session() as s:
        feed = s.scalar(select(Feed))
        kw = feed.category.config["keywords"][0]["term"]
        ingest_run(s, feed, {kw: [item(1, "Alfa"), item(2, "Beta"), item(3, "Gamma"), item(4, "Delta")]})
        ingest_run(s, feed, {kw: [item(1, "Nuovo"), item(2, "Beta"), item(3, "Alfa"), item(4, "Gamma")]})
        texts = [n.text for n in s.scalars(select(Notification))]
    joined = "\n".join(texts)
    assert "Alfa scende da" in joined  # perde quota
    assert "Alfa passa dalla posizione 1 alla 3" in joined
    assert "Nuovo entra al 1° posto" in joined
    assert "nuovo marchio Nuovo al 1° posto" in joined
    assert all(t.startswith("TopFarmacia · Ferro:") for t in texts)

    page = client.get("/avvisi").text
    assert "Alfa passa dalla posizione 1 alla 3" in page
    assert '<span class="count">' not in client.get("/avvisi").text  # aperti = letti


def test_alert_settings_are_saved(client):
    signup(client)
    html = client.get("/avvisi").text
    token = re.search(r'name="csrf" value="([^"]+)"', html).group(1)
    r = client.post("/avvisi", data={"csrf": token, "on_own_drop": "1", "threshold": "5", "on_new_top10": "1"})
    assert "Impostazioni salvate" in r.text
    assert 'name="threshold" inputmode="decimal" value="5"' in r.text
    assert re.search(r'name="on_competitor_top3" value="1"\s*>', r.text)  # spenta
    assert re.search(r'name="on_new_top10" value="1"\s*checked', r.text)  # accesa
