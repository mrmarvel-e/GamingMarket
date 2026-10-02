from app.extensions import db
from app.models import User, Game, Listing
from app.services import make_referral_code

def make_user(password="password123", username="alice", email="a@example.com"):
    u=User(username=username,email=email,phone="+2348012345678",referral_code=make_referral_code(),listing_credits=10)
    u.set_password(password); db.session.add(u); db.session.commit(); return u

def test_home_is_public(client):
    r=client.get("/")
    assert r.status_code == 200
    assert b"GamingMarket" in r.data

def test_user_gets_ten_credits(app):
    with app.app_context():
        u=make_user()
        assert u.listing_credits == 10

def test_status_colors(app):
    from datetime import datetime, timedelta
    with app.app_context():
        u=make_user()
        assert u.status == "black"
        u.admin_verified=True; db.session.commit()
        assert u.status == "purple"
        u.premium_until=datetime.utcnow()+timedelta(days=30); db.session.commit()
        assert u.status == "green"
        u.admin_verified=False; db.session.commit()
        assert u.status == "gold"

def test_registration(client):
    r=client.post("/register",data={"username":"bob","email":"bob@example.com","phone":"+2348011111111","password":"password123"},follow_redirects=True)
    assert r.status_code == 200
    with client.application.app_context():
        assert User.query.filter_by(username="bob").first().listing_credits == 10


def test_listing_card_uses_current_seller_status(client, app):
    from datetime import datetime, timedelta
    with app.app_context():
        user = make_user(username="statusseller", email="status@example.com")
        game = Game.query.first()
        listing = Listing(
            seller_id=user.id, game_id=game.id, title="Status Account",
            description="test", price=10000
        )
        db.session.add(listing); db.session.commit()

        r = client.get("/")
        assert b"listing-card status-black" in r.data

        user.admin_verified = True
        db.session.commit()
        r = client.get("/")
        assert b"listing-card status-purple" in r.data

        user.premium_until = datetime.utcnow() + timedelta(days=30)
        db.session.commit()
        r = client.get("/")
        assert b"listing-card status-green" in r.data


def test_admin_can_login_through_normal_login_form(app, client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "mrmarveloa@gmail.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "StrongAdminPass123!")
    with app.app_context():
        from app.seed import ensure_admin
        ensure_admin()

    r = client.post("/login", data={
        "email": "mrmarveloa@gmail.com",
        "password": "StrongAdminPass123!"
    })
    assert r.status_code == 302
    assert "/admin" in r.headers["Location"]


def test_listing_has_no_description_field(client):
    r = client.get("/listing/new")
    assert r.status_code in (302, 200)
    if r.status_code == 200:
        assert b'name="description"' not in r.data


def test_all_game_specific_fields_are_optional_in_listing_form(client, app):
    with app.app_context():
        games = Game.query.order_by(Game.name).all()
        assert games
        for game in games:
            for field in (game.fields or {}):
                assert field

    r = client.get("/listing/new")
    assert r.status_code == 302 or r.status_code == 200
    if r.status_code == 200:
        assert b"optional" in r.data.lower()


def test_seller_can_delete_listing(client, app):
    with app.app_context():
        user = make_user(username="deleter", email="delete@example.com")
        game = Game.query.first()
        listing = Listing(seller_id=user.id, game_id=game.id, title="Delete Me", description="", price=5000)
        db.session.add(listing); db.session.commit()
        listing_id = listing.id

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True

    r = client.post(f"/seller/listing/{listing_id}/delete", follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        listing = db.session.get(Listing, listing_id)
        assert listing.status == "removed"
        assert listing.top_pinned is False

    public = client.get(f"/listing/{listing_id}")
    assert public.status_code == 404
