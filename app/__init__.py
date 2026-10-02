import os
from pathlib import Path
from flask import Flask, redirect, url_for, flash, request
from dotenv import load_dotenv
from .extensions import db, login_manager
from .models import User
from .seed import seed_games, ensure_admin

load_dotenv()

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    sqlite_path = os.getenv("SQLITE_DB_PATH") or str(Path(app.instance_path) / "gamingmarket.db")
    database_url = os.getenv("DATABASE_URL") or "sqlite:///" + sqlite_path

    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-change-me"),
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=int(os.getenv("MAX_CONTENT_LENGTH", "16777216")),
        UPLOAD_FOLDER=os.getenv("UPLOAD_FOLDER", str(Path(app.instance_path) / "uploads")),
        VAPID_PUBLIC_KEY=os.getenv("VAPID_PUBLIC_KEY", ""),
    )
    if test_config:
        app.config.update(test_config)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from .routes.auth import auth_bp
    from .routes.marketplace import market_bp
    from .routes.seller import seller_bp
    from .routes.admin import admin_bp
    from .routes.api import api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(seller_bp, url_prefix="/seller")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_globals():
        from flask_login import current_user, logout_user
        unread = 0
        if current_user.is_authenticated:
            from .models import Notification
            unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return {"unread_notifications": unread, "vapid_public_key": app.config["VAPID_PUBLIC_KEY"]}

    @app.before_request
    def block_banned_users():
        if current_user.is_authenticated and getattr(current_user, "is_banned", False):
            # Admins cannot be banned, but keep the exception explicit so a
            # malformed database row cannot lock an administrator out of the panel.
            if not current_user.is_admin and request.endpoint not in {"auth.logout", "static"}:
                logout_user()
                flash("This GamingMarket account has been banned. Contact Admin if you believe this is a mistake.", "error")
                return redirect(url_for("auth.login"))

    with app.app_context():
        db.create_all()
        # Lightweight SQLite migration for existing deployments. SQLAlchemy's
        # create_all() does not add new columns to an existing table.
        from sqlalchemy import inspect, text
        user_columns = {col["name"] for col in inspect(db.engine).get_columns("user")}
        migrations = {
            "is_banned": "BOOLEAN NOT NULL DEFAULT 0",
            "banned_at": "DATETIME",
            "banned_reason": "VARCHAR(500)",
        }
        for name, definition in migrations.items():
            if name not in user_columns:
                db.session.execute(text(f"ALTER TABLE user ADD COLUMN {name} {definition}"))
        db.session.commit()
        seed_games()
        ensure_admin()

    return app
