import os, secrets
from .extensions import db
from .models import Game, User, Listing

GAMES = [
    ("Free Fire", "free-fire", ["account_level","rank","characters","evo_guns","gun_skins","emotes","account_prime","region","platform"]),
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
            continue

        # Keep the existing SQLite game record in sync with the current
        # Free Fire field names without deleting any other game settings.
        if slug == "free-fire":
            current = dict(game.fields or {})
            if "rare_skins" in current and "evo_guns" not in current:
                current["evo_guns"] = current.pop("rare_skins")
            if "diamonds" in current and "account_prime" not in current:
                current["account_prime"] = current.pop("diamonds")
            ordered = {}
            for field in fields:
                ordered[field] = current.get(field, "")
            game.fields = ordered

            # Migrate existing Free Fire listing attributes too, so older
            # listings display the new labels/keys instead of the retired
            # Diamonds and Rare Skins fields.
            listings = Listing.query.filter_by(game_id=game.id).all()
            for listing in listings:
                attrs = dict(listing.attributes or {})
                changed = False
                if "rare_skins" in attrs:
                    if "evo_guns" not in attrs:
                        attrs["evo_guns"] = attrs["rare_skins"]
                    attrs.pop("rare_skins", None)
                    changed = True
                if "diamonds" in attrs:
                    if "account_prime" not in attrs:
                        attrs["account_prime"] = attrs["diamonds"]
                    attrs.pop("diamonds", None)
                    changed = True
                if changed:
                    listing.attributes = attrs

    db.session.commit()

def ensure_admin():
    """Ensure the configured admin identity exists and has admin privileges.

    The admin always uses the normal /login form.  ADMIN_PASSWORD is optional
    for existing installations, but when it is supplied it becomes the
    authoritative password for the configured admin account.  This lets a
    deployment repair an existing admin account without deleting the SQLite
    database.
    """
    email = os.getenv("ADMIN_EMAIL", "mrmarveloa@gmail.com").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "").strip()

    admin = User.query.filter_by(email=email).first()

    if not admin:
        if not password:
            # Do not create an account with a known/default password.
            # The next deployment with ADMIN_PASSWORD set will provision it.
            return
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
        # Repair/admin-enable an existing account without touching listings,
        # deals, payments, or other user data.
        admin.is_admin = True
        admin.admin_verified = True
        if password:
            admin.set_password(password)

    db.session.commit()
