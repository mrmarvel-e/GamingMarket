from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user, login_required
from datetime import datetime, timedelta
from ..extensions import db
from ..models import User, Listing, Deal, Message, PremiumPayment, Notification, Review
from ..services import notify

admin_bp = Blueprint("admin", __name__)

def admin_required():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)

@admin_bp.before_request
def guard():
    admin_required()

@admin_bp.get("/")
def dashboard():
    return render_template("admin/dashboard.html",
        users=User.query.count(), listings=Listing.query.count(),
        deals=Deal.query.count(), pending=PremiumPayment.query.filter_by(status="pending").count())

@admin_bp.get("/users")
def users():
    return render_template("admin/users.html", users=User.query.order_by(User.created_at.desc()).all())

@admin_bp.post("/users/<int:user_id>/verify")
def verify(user_id):
    user = db.session.get(User, user_id) or abort(404)
    user.admin_verified = True
    db.session.commit()
    notify(user, "Seller Verified", "Your GamingMarket seller profile is now Admin Verified.", url_for("market.seller_profile", user_id=user.id))
    return redirect(url_for("admin.users"))

@admin_bp.post("/users/<int:user_id>/unverify")
def unverify(user_id):
    user = db.session.get(User, user_id) or abort(404)
    user.admin_verified = False
    db.session.commit()
    return redirect(url_for("admin.users"))

@admin_bp.get("/premium")
def premium():
    payments = PremiumPayment.query.order_by(PremiumPayment.submitted_at.desc()).all()
    return render_template("admin/premium.html", payments=payments)

@admin_bp.post("/premium/<int:payment_id>/approve")
def approve_premium(payment_id):
    p = db.session.get(PremiumPayment, payment_id) or abort(404)
    p.status = "approved"
    p.reviewed_at = datetime.utcnow()
    p.user.premium_until = datetime.utcnow() + timedelta(days=30)
    db.session.commit()
    notify(p.user, "Premium Activated", "Your GamingMarket Premium subscription is active for 30 days.", url_for("seller.dashboard"))
    return redirect(url_for("admin.premium"))

@admin_bp.post("/premium/<int:payment_id>/reject")
def reject_premium(payment_id):
    p = db.session.get(PremiumPayment, payment_id) or abort(404)
    p.status = "rejected"
    p.reviewed_at = datetime.utcnow()
    db.session.commit()
    notify(p.user, "Premium Payment Rejected", "Your Premium payment receipt was not approved. Please contact Admin if needed.", url_for("seller.premium"))
    return redirect(url_for("admin.premium"))

@admin_bp.get("/chats")
def chats():
    messages = Message.query.order_by(Message.created_at.desc()).limit(200).all()
    return render_template("admin/chats.html", messages=messages)

@admin_bp.post("/contact/<int:user_id>")
def contact_user(user_id):
    user = db.session.get(User, user_id) or abort(404)
    body = request.form["body"].strip()
    if body:
        db.session.add(Message(sender_id=current_user.id, recipient_id=user.id, body=body, is_admin_support=True))
        db.session.commit()
        notify(user, "Message from GamingMarket Admin", body, url_for("seller.dashboard"))
    return redirect(url_for("admin.chats"))
