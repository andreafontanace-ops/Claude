"""Applicazione web: `uvicorn sovweb.app:create_app --factory` (in produzione dietro un proxy HTTPS, più processi)."""

from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from amazon_sov.parser import SerpItem
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from . import exports
from .alerts import KINDS, add_default_rules
from .catalog import seed_catalog
from .charts import trend_svg
from .collector import ingest_run, run_feed, update_feed_interval
from .db import Database
from .models import (AlertRule, BrandSov, Category, Feed, Notification, ProductSov, Run, Site, Subscription, User,
                     Workspace, WorkspaceBrand, utcnow)
from .plans import PLANS, TRIAL_DAYS, get_plan, trial_expired
from .providers import get_provider
from .security import csrf_ok, csrf_token, hash_password, verify_password
from .settings import Settings

HERE = Path(__file__).parent
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.check()
    db = Database(settings.database_url)
    db.create_all()
    with db.Session() as s:
        seed_catalog(s)
    provider = get_provider(settings.data_provider)

    app = FastAPI(title="Share of voice e-commerce", docs_url=None, redoc_url=None)
    app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, same_site="lax",
                       https_only=settings.production, max_age=14 * 24 * 3600)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")
    templates.env.filters["pct"] = lambda v, d=1: "–" if v is None else f"{v * 100:.{d}f}%".replace(".", ",")
    templates.env.filters["pp"] = lambda v: "" if v is None else (
        f"{'▲' if v > 0 else '▼' if v < 0 else '='} {abs(v) * 100:.1f} pp".replace(".", ","))
    templates.env.filters["label"] = lambda b: {
        "(non pertinenti)": "Prodotti non pertinenti", "(senza marchio)": "Senza marchio",
        "(marchio da verificare)": "Marchio da verificare", "(non indicato)": "Non indicato"}.get(b, b)
    templates.env.filters["num"] = lambda v: "–" if v is None else str(v).replace(".", ",")
    templates.env.filters["dt"] = lambda d: d.strftime("%d/%m/%Y %H:%M") if d else "–"

    def get_session():
        yield from db.session()

    def render(request: Request, name: str, **ctx) -> HTMLResponse:
        session = ctx.pop("_db", None)
        ctx.setdefault("user", current_user(request, session))
        unread = 0
        if ctx["user"] is not None and session is not None:
            unread = session.scalar(select(func.count(Notification.id)).where(
                Notification.workspace_id == ctx["user"].workspace_id, Notification.read.is_(False))) or 0
        return templates.TemplateResponse(
            request, name, {"csrf": csrf_token(request.session), "plans": PLANS, "unread": unread, **ctx})

    def current_user(request: Request, session: Session | None) -> User | None:
        uid = request.session.get("uid")
        if not uid or session is None:
            return None
        return session.get(User, uid)

    def require_user(request: Request, session: Session = Depends(get_session)) -> User:
        user = current_user(request, session)
        if user is None:
            raise HTTPException(status_code=303, headers={"Location": "/accedi"})
        return user

    async def check_csrf(request: Request) -> None:
        form = await request.form()
        if not csrf_ok(request.session, form.get("csrf")):
            raise HTTPException(status_code=400, detail="Modulo scaduto: ricarica la pagina e riprova.")

    # ------------------------------------------------------------------ pagine pubbliche

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request, session: Session = Depends(get_session)):
        if current_user(request, session):
            return RedirectResponse("/dashboard", status_code=303)
        cats = session.scalars(select(Category).order_by(Category.name)).all()
        sites = session.scalars(select(Site).order_by(Site.id)).all()
        return render(request, "home.html", _db=session, categories=cats, sites=sites)

    @app.get("/prezzi", response_class=HTMLResponse)
    def pricing(request: Request, session: Session = Depends(get_session)):
        return render(request, "pricing.html", _db=session)

    @app.get("/salute")
    def health():
        return {"ok": True}

    # ------------------------------------------------------------------ account

    @app.get("/registrati", response_class=HTMLResponse)
    def register_form(request: Request, session: Session = Depends(get_session)):
        return render(request, "register.html", _db=session, error=None, form={})

    @app.post("/registrati", dependencies=[Depends(check_csrf)])
    def register(request: Request, email: str = Form(...), password: str = Form(...), company: str = Form(...),
                 name: str = Form(""), session: Session = Depends(get_session)):
        email = email.strip().lower()
        form = {"email": email, "company": company, "name": name}
        error = None
        if not EMAIL_RE.match(email):
            error = "Indirizzo email non valido."
        elif len(password) < 10:
            error = "La password deve avere almeno 10 caratteri."
        elif not company.strip():
            error = "Indica il nome dell'azienda."
        elif session.scalar(select(User).where(User.email == email)):
            error = "Esiste già un account con questa email: accedi."
        if error:
            return render(request, "register.html", _db=session, error=error, form=form)
        ws = Workspace(name=company.strip(), plan="prova", trial_ends_at=utcnow() + timedelta(days=TRIAL_DAYS))
        user = User(email=email, name=name.strip(), password_hash=hash_password(password), workspace=ws)
        session.add_all([ws, user])
        session.flush()
        session.add_all(add_default_rules(ws))
        session.commit()
        request.session.clear()
        request.session["uid"] = user.id
        return RedirectResponse("/benvenuto", status_code=303)

    @app.get("/accedi", response_class=HTMLResponse)
    def login_form(request: Request, session: Session = Depends(get_session)):
        return render(request, "login.html", _db=session, error=None)

    @app.post("/accedi", dependencies=[Depends(check_csrf)])
    def login(request: Request, email: str = Form(...), password: str = Form(...),
              session: Session = Depends(get_session)):
        user = session.scalar(select(User).where(User.email == email.strip().lower()))
        if user is None or not verify_password(password, user.password_hash):
            return render(request, "login.html", _db=session, error="Email o password non corretti.")
        request.session.clear()
        request.session["uid"] = user.id
        return RedirectResponse("/dashboard", status_code=303)

    @app.post("/esci", dependencies=[Depends(check_csrf)])
    def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/", status_code=303)

    # ------------------------------------------------------------------ avvio guidato

    @app.get("/benvenuto", response_class=HTMLResponse)
    def onboarding(request: Request, user: User = Depends(require_user), session: Session = Depends(get_session)):
        cats = session.scalars(select(Category).order_by(Category.name)).all()
        sites = session.scalars(select(Site).order_by(Site.id)).all()
        chosen = {(s.feed.category_id, s.feed.site_id) for s in user.workspace.subscriptions}
        return render(request, "onboarding.html", _db=session, user=user, categories=cats, sites=sites,
                      chosen_cats={c for c, _ in chosen}, chosen_sites={s for _, s in chosen},
                      plan=get_plan(user.workspace.plan), error=None)

    @app.post("/benvenuto", dependencies=[Depends(check_csrf)])
    async def onboarding_save(request: Request, user: User = Depends(require_user),
                              session: Session = Depends(get_session)):
        form = await request.form()
        cat_ids = {int(v) for v in form.getlist("category")}
        site_ids = {int(v) for v in form.getlist("site")}
        plan = get_plan(user.workspace.plan)
        error = None
        if not cat_ids or not site_ids:
            error = "Scegli almeno una categoria e un sito."
        elif len(cat_ids) > plan.categories or len(site_ids) > plan.sites:
            cats = "1 categoria" if plan.categories == 1 else f"{plan.categories} categorie"
            error = (f"Il piano {plan.name} comprende {cats} e {plan.sites} siti: "
                     "togline qualcuno o passa a un piano superiore.")
        if error:
            cats = session.scalars(select(Category).order_by(Category.name)).all()
            sites = session.scalars(select(Site).order_by(Site.id)).all()
            return render(request, "onboarding.html", _db=session, user=user, categories=cats, sites=sites,
                          chosen_cats=cat_ids, chosen_sites=site_ids, plan=plan, error=error)
        ws = user.workspace
        wanted = {(c, s) for c in cat_ids for s in site_ids}
        for sub in list(ws.subscriptions):
            if (sub.feed.category_id, sub.feed.site_id) not in wanted:
                session.delete(sub)
        have = {(s.feed.category_id, s.feed.site_id) for s in ws.subscriptions}
        for c, s in wanted - have:
            feed = session.scalar(select(Feed).where(Feed.category_id == c, Feed.site_id == s))
            if feed is None:
                feed = Feed(category_id=c, site_id=s, next_run_at=utcnow())
                session.add(feed)
                session.flush()
            session.add(Subscription(workspace=ws, feed=feed))
        session.flush()
        for feed in {sub.feed for sub in ws.subscriptions}:
            update_feed_interval(session, feed)
        session.commit()
        return RedirectResponse("/benvenuto/marchi", status_code=303)

    @app.get("/benvenuto/marchi", response_class=HTMLResponse)
    def onboarding_brands(request: Request, user: User = Depends(require_user),
                          session: Session = Depends(get_session)):
        cats = _workspace_categories(user.workspace)
        current = defaultdict(lambda: {"own": [], "competitor": []})
        for b in user.workspace.brands:
            current[b.category_id][b.role].append(b.name)
        suggestions = {c.id: _brand_suggestions(session, c.id) for c in cats}
        return render(request, "onboarding_brands.html", _db=session, user=user, categories=cats,
                      current=current, suggestions=suggestions)

    @app.post("/benvenuto/marchi", dependencies=[Depends(check_csrf)])
    async def onboarding_brands_save(request: Request, user: User = Depends(require_user),
                                     session: Session = Depends(get_session)):
        form = await request.form()
        ws = user.workspace
        for cat in ([] if form.get("skip") else _workspace_categories(ws)):
            for role in ("own", "competitor"):
                names = _split_names(form.get(f"{role}_{cat.id}", ""))
                for old in [b for b in ws.brands if b.category_id == cat.id and b.role == role]:
                    session.delete(old)
                session.flush()
                for n in names:
                    session.add(WorkspaceBrand(workspace=ws, category_id=cat.id, name=n, role=role))
        session.commit()
        # prima raccolta subito, così la dashboard non è vuota
        for sub in ws.subscriptions:
            feed = sub.feed
            if feed.last_run_at is None:
                if provider.name == "demo":
                    run_feed(session, feed, provider)
                else:
                    feed.next_run_at = utcnow()
        session.commit()
        return RedirectResponse("/dashboard", status_code=303)

    # ------------------------------------------------------------------ dashboard

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard(request: Request, user: User = Depends(require_user), session: Session = Depends(get_session)):
        ws = user.workspace
        if not ws.subscriptions:
            return RedirectResponse("/benvenuto", status_code=303)
        cards = []
        for sub in sorted(ws.subscriptions, key=lambda s: (s.feed.category.name, s.feed.site_id)):
            feed = sub.feed
            run = _latest_run(session, feed.id)
            rows = session.scalars(select(BrandSov).where(BrandSov.run_id == run.id)).all() if run else []
            own = _own_brands(ws, feed.category_id)
            leader = next((r for r in rows if r.rank == 1), None)
            mine = [r for r in rows if r.brand.lower() in own]
            cards.append({"feed": feed, "run": run, "leader": leader, "mine": mine})
        return render(request, "dashboard.html", _db=session, user=user, cards=cards, plan=get_plan(ws.plan),
                      expired=trial_expired(ws.plan, ws.trial_ends_at, utcnow()))

    @app.get("/dashboard/{feed_id}", response_class=HTMLResponse)
    def feed_detail(feed_id: int, request: Request, user: User = Depends(require_user),
                    session: Session = Depends(get_session), standalone: bool = False):
        ws = user.workspace
        feed = _subscribed_feed(ws, feed_id)
        plan = get_plan(ws.plan)
        run = _latest_run(session, feed.id)
        if run is None:
            return render(request, "feed.html", _db=session, user=user, feed=feed, run=None)
        brands = session.scalars(select(BrandSov).where(BrandSov.run_id == run.id)
                                 .order_by(BrandSov.rank.is_(None), BrandSov.rank)).all()
        prev = session.scalar(select(Run).where(Run.feed_id == feed.id, Run.status == "ok", Run.id < run.id)
                              .order_by(Run.id.desc()))
        prev_sov = {b.brand: b.sov_total for b in session.scalars(select(BrandSov).where(BrandSov.run_id == prev.id))} if prev else {}
        own = _own_brands(ws, feed.category_id)
        competitors = _competitor_brands(ws, feed.category_id)
        products = session.scalars(select(ProductSov).where(ProductSov.run_id == run.id)
                                   .order_by(ProductSov.rank).limit(25)).all()
        # andamento: primi 5 marchi + i propri + i concorrenti scelti
        since = utcnow() - timedelta(days=plan.history_days)
        show = [b.brand for b in brands if b.rank and b.rank <= 5]
        show = list(dict.fromkeys([b.brand for b in brands if b.brand.lower() in own] + show
                                  + [b.brand for b in brands if b.brand.lower() in competitors]))[:8]
        hist = session.execute(
            select(Run.started_at, BrandSov.brand, BrandSov.sov_total).join(BrandSov, BrandSov.run_id == Run.id)
            .where(Run.feed_id == feed.id, Run.status == "ok", Run.started_at >= since, BrandSov.brand.in_(show))
            .order_by(Run.started_at)
        ).all()
        series: dict[str, list] = {b: [] for b in show}
        for t, b, v in hist:
            series[b].append((t, v))
        chart = trend_svg(series, {b for b in show if b.lower() in own})
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8") if standalone else ""
        return render(request, "feed.html", _db=session, user=user, feed=feed, run=run, brands=brands,
                      prev_sov=prev_sov, own=own, competitors=competitors, products=products, chart=chart,
                      plan=plan, max_sov=max((b.sov_total for b in brands if b.rank), default=0) or 1,
                      standalone=standalone, inline_css=css)

    @app.get("/dashboard/{feed_id}/scarica/{fmt}")
    def download(feed_id: int, fmt: str, request: Request, tabella: str = "marchi",
                 user: User = Depends(require_user), session: Session = Depends(get_session)):
        ws = user.workspace
        plan = get_plan(ws.plan)
        if not plan.export:
            raise HTTPException(status_code=403, detail="Lo scaricamento dei dati è incluso dal piano Base in su.")
        feed = _subscribed_feed(ws, feed_id)
        data = exports.collect(session, feed, _own_brands(ws, feed.category_id), plan.history_days)
        base = f"sov_{feed.category.slug}_{feed.site.slug}_{utcnow():%Y%m%d}"
        if fmt == "xlsx":
            return Response(exports.to_xlsx(data),
                            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            headers={"Content-Disposition": f'attachment; filename="{base}.xlsx"'})
        if fmt == "csv":
            if tabella not in exports.TABLES:
                raise HTTPException(status_code=404, detail="Tabella sconosciuta")
            rows = {"marchi": data.brands, "prodotti": data.products, "andamento": data.history}[tabella]
            return Response(exports.to_csv(rows, exports.TABLES[tabella]), media_type="text/csv; charset=utf-8",
                            headers={"Content-Disposition": f'attachment; filename="{base}_{tabella}.csv"'})
        if fmt == "html":
            page = feed_detail(feed_id, request, user, session, standalone=True)
            return Response(page.body, media_type="text/html; charset=utf-8",
                            headers={"Content-Disposition": f'attachment; filename="{base}.html"'})
        raise HTTPException(status_code=404, detail="Formato non disponibile")

    # ------------------------------------------------------------------ avvisi

    @app.get("/avvisi", response_class=HTMLResponse)
    def alerts_page(request: Request, user: User = Depends(require_user), session: Session = Depends(get_session)):
        ws_id = user.workspace_id
        items = session.scalars(select(Notification).where(Notification.workspace_id == ws_id)
                                .order_by(Notification.id.desc()).limit(100)).all()
        rules = {r.kind: r for r in session.scalars(select(AlertRule).where(AlertRule.workspace_id == ws_id))}
        page = render(request, "alerts.html", _db=session, user=user, items=items, rules=rules, kinds=KINDS,
                      email_on=bool(settings.smtp_host))
        for n in items:  # aperte = lette
            n.read = True
        session.commit()
        return page

    @app.post("/avvisi", dependencies=[Depends(check_csrf)])
    async def alerts_save(request: Request, user: User = Depends(require_user), session: Session = Depends(get_session)):
        form = await request.form()
        rules = {r.kind: r for r in session.scalars(select(AlertRule).where(AlertRule.workspace_id == user.workspace_id))}
        for kind in KINDS:
            rule = rules.get(kind) or AlertRule(workspace_id=user.workspace_id, kind=kind)
            rule.active = form.get(f"on_{kind}") == "1"
            rule.email = form.get(f"email_{kind}") == "1"
            if kind == "own_drop":
                try:
                    rule.threshold = max(0.1, min(50.0, float(str(form.get("threshold", "2")).replace(",", ".")))) / 100
                except ValueError:
                    pass
            session.add(rule)
        session.commit()
        return RedirectResponse("/avvisi?salvato=1", status_code=303)

    # ------------------------------------------------------------------ API di caricamento

    @app.post("/api/ingest")
    async def api_ingest(request: Request, session: Session = Depends(get_session)):
        """Carica i risultati di una raccolta esterna. Solo con il token di servizio (SOV_INGEST_TOKEN)."""
        auth = request.headers.get("authorization", "")
        if not settings.ingest_token or auth != f"Bearer {settings.ingest_token}":
            raise HTTPException(status_code=401, detail="Token non valido")
        data = await request.json()
        cat = session.scalar(select(Category).where(Category.slug == data.get("category")))
        site = session.scalar(select(Site).where(Site.slug == data.get("site")))
        if cat is None or site is None:
            raise HTTPException(status_code=422, detail="Categoria o sito sconosciuti")
        feed = session.scalar(select(Feed).where(Feed.category_id == cat.id, Feed.site_id == site.id))
        if feed is None:
            feed = Feed(category_id=cat.id, site_id=site.id)
            session.add(feed)
            session.flush()
        results = {}
        for kw, items in (data.get("results") or {}).items():
            results[kw] = [SerpItem(
                asin=str(it["id"])[:40], slot=i, title=str(it.get("title", ""))[:600],
                brand_raw=it.get("brand"), sponsored=bool(it.get("sponsored")),
                placement="sponsored" if it.get("sponsored") else "organic", price=it.get("price"),
                rating=it.get("rating"), reviews=it.get("reviews"),
            ) for i, it in enumerate(items, 1)]
        collected_at = None
        if data.get("collected_at"):
            try:
                collected_at = datetime.fromisoformat(str(data["collected_at"]))
                if collected_at.tzinfo is not None:  # la piattaforma ragiona in UTC
                    collected_at = collected_at.astimezone(timezone.utc).replace(tzinfo=None)
            except ValueError:
                raise HTTPException(status_code=422, detail="collected_at non valido (formato ISO 8601)")
        if not results or not any(results.values()):
            raise HTTPException(status_code=422, detail="Nessun risultato da caricare")
        run = ingest_run(session, feed, results, collected_at)
        return JSONResponse({"run_id": run.id, "status": run.status, "keywords": run.keywords_scored})

    return app


# ---------------------------------------------------------------------- utilità


def _workspace_categories(ws: Workspace) -> list[Category]:
    return sorted({s.feed.category for s in ws.subscriptions}, key=lambda c: c.name)


def _own_brands(ws: Workspace, category_id: int) -> set[str]:
    return {b.name.lower() for b in ws.brands if b.category_id == category_id and b.role == "own"}


def _competitor_brands(ws: Workspace, category_id: int) -> set[str]:
    return {b.name.lower() for b in ws.brands if b.category_id == category_id and b.role == "competitor"}


def _subscribed_feed(ws: Workspace, feed_id: int) -> Feed:
    for sub in ws.subscriptions:
        if sub.feed_id == feed_id:
            return sub.feed
    raise HTTPException(status_code=404, detail="Non trovato")


def _latest_run(session: Session, feed_id: int) -> Run | None:
    return session.scalar(select(Run).where(Run.feed_id == feed_id, Run.status == "ok").order_by(Run.id.desc()))


def _brand_suggestions(session: Session, category_id: int, n: int = 12) -> list[str]:
    """Marchi più visibili nell'ultima raccolta della categoria (su qualsiasi sito)."""
    last_runs = select(func.max(Run.id)).join(Feed, Feed.id == Run.feed_id).where(
        Feed.category_id == category_id, Run.status == "ok").group_by(Run.feed_id)
    rows = session.execute(
        select(BrandSov.brand, func.sum(BrandSov.sov_total)).where(BrandSov.run_id.in_(last_runs), BrandSov.rank.isnot(None))
        .group_by(BrandSov.brand).order_by(func.sum(BrandSov.sov_total).desc()).limit(n)
    ).all()
    return [b for b, _ in rows]


def _split_names(text: str) -> list[str]:
    names = [" ".join(n.split()) for n in re.split(r"[,\n;]", text or "")]
    return list(dict.fromkeys(n for n in names if n))[:30]

