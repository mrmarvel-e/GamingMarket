from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from ..extensions import db
from ..models import User, Referral
from ..services import make_referral_code

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["GET","POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("market.home"))
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip().lower()
        phone = request.form["phone"].strip()
        password = request.form["password"]
        referral = request.form.get("referral_code","").strip().upper()
        if User.query.filter((User.email==email)|(User.username==username)).first():
            flash("Username or email already exists.", "error")
            return render_template("auth/register.html")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("auth/register.html")
        user = User(username=username, email=email, phone=phone,
                    referral_code=make_referral_code(), listing_credits=10)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        if referral:
            referrer = User.query.filter_by(referral_code=referral).first()
            if referrer and referrer.id != user.id:
                referrer.listing_credits += 1
                db.session.add(Referral(referrer_id=referrer.id, referred_id=user.id))
        db.session.commit()
        login_user(user)
        return redirect(url_for("market.home"))
    return render_template("auth/register.html")

@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"].strip().lower()).first()
        if user and user.check_password(request.form["password"]):
            # The configured GamingMarket admin uses the normal login form.
            # Recognize the admin by email and send them directly to the Admin Panel.
            import os
            admin_email = os.getenv("ADMIN_EMAIL", "mrmarveloa@gmail.com").strip().lower()
            if user.email.lower() == admin_email:
                user.is_admin = True
                user.admin_verified = True
                db.session.commit()
            login_user(user, remember=True)
            if user.is_admin:
                return redirect(url_for("admin.dashboard"))
            return redirect(request.args.get("next") or url_for("market.home"))
        flash("Invalid email or password.", "error")
    return render_template("auth/login.html")

@auth_bp.post("/logout")
def logout():
    logout_user()
    return redirect(url_for("market.home"))
