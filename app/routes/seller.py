import os, uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app, send_from_directory
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from ..extensions import db
from ..models import Game, Listing, ListingPhoto, Deal, Message, PremiumPayment, User, Notification, Review, DealCredentialVault
from ..services import notify

seller_bp = Blueprint("seller", __name__)

def seller_only():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    return None

@seller_bp.get("/")
@login_required
def dashboard():
    listings = Listing.query.filter_by(seller_id=current_user.id).order_by(Listing.created_at.desc()).all()
    deals = Deal.query.filter((Deal.seller_id==current_user.id)|(Deal.buyer_id==current_user.id)).order_by(Deal.updated_at.desc()).limit(20).all()
    return render_template("seller/dashboard.html", listings=listings, deals=deals)

@seller_bp.get("/notifications")
@login_required
def notifications():
    rows = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(100).all()
    for row in rows:
        row.is_read = True
    db.session.commit()
    return render_template("seller/notifications.html", notifications=rows)

@seller_bp.route("/listing/new", methods=["GET","POST"])
@login_required
def new_listing():
    if not current_user.has_premium_features and current_user.listing_credits <= 0:
        flash("You have used your 10 free listing credits. Upgrade to Premium or receive referral credits.", "error")
        return redirect(url_for("seller.dashboard"))
    games = Game.query.order_by(Game.name).all()
    if request.method == "POST":
        game = db.session.get(Game, int(request.form["game_id"])) or abort(400)
        photos = request.files.getlist("photos")
        photos = [p for p in photos if p and p.filename]
        if len(photos) < 2:
            flash("Every listing requires at least 2 photos.", "error")
            return render_template("seller/new_listing.html", games=games)
        try:
            price = int(request.form["price"])
        except ValueError:
            price = 0
        if price <= 0:
            flash("Enter a valid NGN price.", "error")
            return render_template("seller/new_listing.html", games=games)
        attributes = {f: request.form.get(f,"").strip() for f in (game.fields or {}).keys()}
        if game.slug == "free-fire":
            # Free Fire Prime and Evo Guns are numeric account stats.
            for field, label in (("account_prime", "Account's Prime"), ("evo_guns", "Evo Guns")):
                raw = attributes.get(field, "")
                if raw:
                    try:
                        value = int(raw)
                    except ValueError:
                        flash(f"{label} must be a number.", "error")
                        return render_template("seller/new_listing.html", games=games)
                    if value < 0:
                        flash(f"{label} cannot be negative.", "error")
                        return render_template("seller/new_listing.html", games=games)
                    attributes[field] = str(value)
        title = request.form.get("title", "").strip()
        if not title:
            flash("Enter a listing title.", "error")
            return render_template("seller/new_listing.html", games=games)
        listing = Listing(seller_id=current_user.id, game_id=game.id,
                          title=title, description="",
                          price=price, attributes=attributes)
        db.session.add(listing)
        db.session.flush()
        folder = os.path.join(current_app.config["UPLOAD_FOLDER"], str(listing.id))
        os.makedirs(folder, exist_ok=True)
        for i, photo in enumerate(photos[:10]):
            name = f"{uuid.uuid4().hex}_{secure_filename(photo.filename)}"
            photo.save(os.path.join(folder, name))
            db.session.add(ListingPhoto(listing_id=listing.id, filename=name, is_cover=(i==0)))
        if not current_user.has_premium_features:
            current_user.listing_credits -= 1
        db.session.commit()
        flash("Listing created.", "success")
        return redirect(url_for("market.listing_detail", listing_id=listing.id))
    return render_template("seller/new_listing.html", games=games)

@seller_bp.get("/media/<int:listing_id>/<filename>")
def media(listing_id, filename):
    return send_from_directory(os.path.join(current_app.config["UPLOAD_FOLDER"], str(listing_id)), filename)

@seller_bp.post("/listing/<int:listing_id>/pin")
@login_required
def pin_listing(listing_id):
    listing = db.session.get(Listing, listing_id) or abort(404)
    if listing.seller_id != current_user.id:
        abort(403)
    if current_user.status != "green":
        flash("Only Green sellers can use permanent top slots.", "error")
        return redirect(url_for("seller.dashboard"))
    count = Listing.query.filter_by(seller_id=current_user.id, top_pinned=True, status="active").count()
    if not listing.top_pinned and count >= 2:
        flash("You can keep only 2 permanent Top Listings.", "error")
    else:
        listing.top_pinned = not listing.top_pinned
        db.session.commit()
    return redirect(url_for("seller.dashboard"))

@seller_bp.get("/deal/<int:deal_id>")
@login_required
def deal(deal_id):
    d = db.session.get(Deal, deal_id) or abort(404)
    if current_user.id not in (d.buyer_id, d.seller_id) and not current_user.is_admin:
        abort(403)
    messages = Message.query.filter_by(deal_id=d.id).order_by(Message.created_at.asc()).all()
    return render_template("seller/deal.html", deal=d, messages=messages)

@seller_bp.post("/deal/<int:deal_id>/message")
@login_required
def deal_message(deal_id):
    d = db.session.get(Deal, deal_id) or abort(404)
    if current_user.id not in (d.buyer_id, d.seller_id) and not current_user.is_admin:
        abort(403)
    recipient_id = d.seller_id if current_user.id == d.buyer_id else d.buyer_id
    body = request.form["body"].strip()
    if body:
        db.session.add(Message(deal_id=d.id, sender_id=current_user.id, recipient_id=recipient_id, body=body))
        db.session.commit()
        recipient = db.session.get(User, recipient_id)
        notify(recipient, "New Deal Message", f"{current_user.username} sent you a message about {d.listing.title}.",
               url_for("seller.deal", deal_id=d.id))
    return redirect(url_for("seller.deal", deal_id=d.id))

@seller_bp.post("/deal/<int:deal_id>/status")
@login_required
def deal_status(deal_id):
    d = db.session.get(Deal, deal_id) or abort(404)
    if current_user.id not in (d.buyer_id, d.seller_id) and not current_user.is_admin:
        abort(403)
    status = request.form.get("status")
    if status not in {"accepted","declined","completed"}:
        abort(400)
    d.status = status
    if status == "completed":
        d.listing.status = "sold"
        notify(d.buyer, "Deal Completed", f"Your deal for {d.listing.title} is complete.", url_for("seller.dashboard"))
        notify(d.seller, "Deal Completed", f"Your sale of {d.listing.title} is complete.", url_for("seller.dashboard"))
    else:
        other = d.buyer if current_user.id == d.seller_id else d.seller
        notify(other, f"Deal {status.title()}", f"The deal for {d.listing.title} was {status}.", url_for("seller.deal", deal_id=d.id))
    db.session.commit()
    return redirect(url_for("seller.deal", deal_id=d.id))

@seller_bp.post("/deal/<int:deal_id>/credential-vault")
@login_required
def save_credential_vault(deal_id):
    d = db.session.get(Deal, deal_id) or abort(404)
    if current_user.id not in (d.buyer_id, d.seller_id):
        abort(403)
    ciphertext = request.form.get("ciphertext", "").strip()
    iv = request.form.get("iv", "").strip()
    salt = request.form.get("salt", "").strip()
    if not ciphertext or not iv or not salt:
        abort(400)
    vault = DealCredentialVault.query.filter_by(deal_id=d.id).first()
    if not vault:
        vault = DealCredentialVault(deal_id=d.id, ciphertext=ciphertext, iv=iv, salt=salt)
        db.session.add(vault)
    else:
        vault.ciphertext, vault.iv, vault.salt = ciphertext, iv, salt
    db.session.commit()
    flash("Encrypted account-access container saved. GamingMarket cannot read its contents.", "success")
    return redirect(url_for("seller.deal", deal_id=d.id))

@seller_bp.post("/deal/<int:deal_id>/credential-vault/delete")
@login_required
def delete_credential_vault(deal_id):
    d = db.session.get(Deal, deal_id) or abort(404)
    if current_user.id not in (d.buyer_id, d.seller_id):
        abort(403)
    vault = DealCredentialVault.query.filter_by(deal_id=d.id).first()
    if vault:
        db.session.delete(vault)
        db.session.commit()
    return redirect(url_for("seller.deal", deal_id=d.id))

@seller_bp.route("/premium", methods=["GET","POST"])
@login_required
def premium():
    if request.method == "POST":
        receipt = request.files.get("receipt")
        if not receipt or not receipt.filename:
            flash("Upload your bank-transfer receipt.", "error")
            return redirect(url_for("seller.premium"))
        name = f"{uuid.uuid4().hex}_{secure_filename(receipt.filename)}"
        folder = os.path.join(current_app.config["UPLOAD_FOLDER"], "premium")
        os.makedirs(folder, exist_ok=True)
        receipt.save(os.path.join(folder, name))
        db.session.add(PremiumPayment(user_id=current_user.id, receipt_filename=name))
        db.session.commit()
        admins = User.query.filter_by(is_admin=True).all()
        for admin in admins:
            notify(admin, "Premium Payment Awaiting Review", f"{current_user.username} submitted a ₦10,000 Premium receipt.",
                   url_for("admin.premium"))
        flash("Receipt submitted. Awaiting Admin Confirmation (2–24 hours).", "success")
        return redirect(url_for("seller.dashboard"))
    return render_template("seller/premium.html")

@seller_bp.route("/profile", methods=["GET","POST"])
@login_required
def profile():
    if request.method == "POST":
        new_email = request.form.get("email", current_user.email).strip().lower()
        new_phone = request.form.get("phone", current_user.phone).strip()
        existing = User.query.filter(User.email == new_email, User.id != current_user.id).first()
        if existing:
            flash("That email is already in use by another account.", "error")
            return render_template("seller/profile.html")
        current_user.email = new_email
        current_user.phone = new_phone
        current_user.bank_name = request.form.get("bank_name","").strip()
        current_user.bank_account_name = request.form.get("bank_account_name","").strip()
        current_user.bank_account_number = request.form.get("bank_account_number","").strip()
        db.session.commit()
        flash("Profile updated.", "success")
    return render_template("seller/profile.html")
