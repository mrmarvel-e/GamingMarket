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
