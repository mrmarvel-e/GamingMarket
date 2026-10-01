import os, secrets
from .extensions import db
from .models import Game, User

GAMES = [
    ("Free Fire", "free-fire", ["account_level","rank","characters","rare_skins","gun_skins","emotes","diamonds","region","platform"]),
    ("Call of Duty", "call-of-duty", ["level","rank","weapons","operator_skins","blueprints","cp","region","platform"]),
    ("Lords Mobile", "lords-mobile", ["might","castle_level","heroes","troops","research","gems","region"]),
    ("eFootball", "efootball", ["team","team_strength","epic_players","legendary_players","coins","gp","division","region"]),
    ("FC Mobile", "fc-mobile", ["ovr","players","coins","gems","rank","team","league"]),
    ("Dream League Soccer", "dream-league-soccer", ["team_rating","players","coins","gems","stadium","league"]),
    ("GTA", "gta", ["edition","level","cash","vehicles","properties","platform","region"]),
    ("PUBG", "pubg", ["level","rank","skins","outfits","uc","region","platform"]),
    ("Offline Games", "offline-games", ["game_title","platform","version","save_progress","extras"]),
]

def seed_games():
    for name, slug, fields in GAMES:
        game = Game.query.filter_by(slug=slug).first()
        if not game:
            db.session.add(Game(name=name, slug=slug, fields={f: "" for f in fields}))
    db.session.commit()

def ensure_admin():
    email = os.getenv("ADMIN_EMAIL", "mrmarveloa@gmail.com").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "change-this-before-use")
    admin = User.query.filter_by(email=email).first()
    if not admin:
        admin = User(
            username="Admin",
            email=email,
            phone="+2340000000000",
            referral_code="ADMIN",
            listing_credits=0,
            is_admin=True,
            admin_verified=True,
        )
        admin.set_password(password)
        db.session.add(admin)
    else:
        admin.is_admin = True
        admin.admin_verified = True
        if password and password != "change-this-before-use":
            admin.set_password(password)
    db.session.commit()
