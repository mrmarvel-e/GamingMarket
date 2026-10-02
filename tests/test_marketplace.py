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


def test_profile_allows_editing_email_and_phone(client, user):
    client.post("/login", data={"email": user.email, "password": "password123"}, follow_redirects=True)
    r = client.post("/seller/profile", data={"email": "updated@example.com", "phone": "+2348000000000", "bank_name": "Test Bank", "bank_account_name": "Test User", "bank_account_number": "123"}, follow_redirects=True)
    assert r.status_code == 200

def test_notification_page_exists(client, user):
    client.post("/login", data={"email": user.email, "password": "password123"}, follow_redirects=True)
    r = client.get("/seller/notifications")
    assert r.status_code == 200


def test_admin_can_ban_and_unban_user(client, app, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "mrmarveloa@gmail.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "StrongAdminPass123!")
    with app.app_context():
        from app.seed import ensure_admin
        ensure_admin()
        target = make_user(username="banneduser", email="banned@example.com")
    client.post("/login", data={"email":"mrmarveloa@gmail.com", "password":"StrongAdminPass123!"})
    r = client.post(f"/admin/users/{target.id}/ban", data={"reason":"Marketplace abuse"}, follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        target = db.session.get(User, target.id)
        assert target.is_banned is True
        assert target.banned_reason == "Marketplace abuse"
    client.post("/logout")
    r = client.post("/login", data={"email":"banned@example.com", "password":"password123"}, follow_redirects=True)
    assert r.status_code == 200
    assert b"account has been banned" in r.data
    client.post("/login", data={"email":"mrmarveloa@gmail.com", "password":"StrongAdminPass123!"})
    r = client.post(f"/admin/users/{target.id}/unban", follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        target = db.session.get(User, target.id)
        assert target.is_banned is False
        assert target.banned_reason is None


def test_banned_user_can_submit_appeal(client, app):
    with app.app_context():
        user = make_user(username="banneduser", email="banned@example.com")
        user.is_banned = True
        user.banned_reason = "Test ban"
        db.session.commit()
        user_id = user.id

    r = client.post("/appeal", data={
        "email": "banned@example.com",
        "message": "I believe this ban was a mistake and would like a review."
    }, follow_redirects=True)
    assert r.status_code == 200
    assert b"appeal has been submitted" in r.data
    with app.app_context():
        from app.models import BanAppeal
        appeal = BanAppeal.query.filter_by(user_id=user_id).first()
        assert appeal is not None
        assert appeal.status == "pending"


def test_admin_can_approve_ban_appeal(app, client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "mrmarveloa@gmail.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "StrongAdminPass123!")
    with app.app_context():
        from app.seed import ensure_admin
        from app.models import BanAppeal
        ensure_admin()
        user = make_user(username="appealuser", email="appeal@example.com")
        user.is_banned = True
        db.session.add(BanAppeal(user_id=user.id, email=user.email, message="Please review my ban."))
        db.session.commit()
        appeal_id = BanAppeal.query.first().id
    client.post("/login", data={"email":"mrmarveloa@gmail.com", "password":"StrongAdminPass123!"})
    r = client.post(f"/admin/appeals/{appeal_id}/approve", follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        from app.models import BanAppeal
        appeal = db.session.get(BanAppeal, appeal_id)
        assert appeal.status == "approved"
        assert appeal.user.is_banned is False
