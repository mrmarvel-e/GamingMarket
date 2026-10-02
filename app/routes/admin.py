from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user, login_required
from datetime import datetime, timedelta
from ..extensions import db
from ..models import User, Listing, Deal, Message, PremiumPayment, Notification, Review, BanAppeal
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
    users = User.query.order_by(User.created_at.desc()).all()
    appeals = BanAppeal.query.filter_by(status="pending").order_by(BanAppeal.created_at.desc()).all()
    return render_template("admin/users.html", users=users, appeals=appeals)

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

@admin_bp.post("/users/<int:user_id>/ban")
def ban_user(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.is_admin or user.id == current_user.id:
        flash("Admin accounts cannot be banned.", "error")
        return redirect(url_for("admin.users"))
    reason = request.form.get("reason", "").strip()[:500]
    user.is_banned = True
    user.banned_at = datetime.utcnow()
    user.banned_reason = reason or None
    # Marketplace visibility is automatically suppressed for banned sellers;
    # keep their listings and deal history intact so an unban does not destroy data.
    db.session.commit()
    flash(f"{user.username} has been banned.", "success")
    return redirect(url_for("admin.users"))

@admin_bp.post("/users/<int:user_id>/unban")
def unban_user(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.is_admin:
        flash("Admin accounts cannot be changed here.", "error")
        return redirect(url_for("admin.users"))
    user.is_banned = False
    user.banned_at = None
    user.banned_reason = None
    db.session.commit()
    flash(f"{user.username} has been unbanned. Their existing listings are visible again if they are still active.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.post("/appeals/<int:appeal_id>/approve")
def approve_ban_appeal(appeal_id):
    appeal = db.session.get(BanAppeal, appeal_id) or abort(404)
    user = appeal.user
    if appeal.status != "pending":
        flash("That appeal has already been reviewed.", "error")
        return redirect(url_for("admin.users"))
    appeal.status = "approved"
    appeal.reviewed_at = datetime.utcnow()
    user.is_banned = False
    user.banned_at = None
    user.banned_reason = None
    db.session.commit()
    notify(user, "Ban Appeal Approved", "Your ban appeal was approved. Your GamingMarket account has been unbanned.", url_for("market.home"))
    flash(f"Appeal approved and {user.username} has been unbanned.", "success")
    return redirect(url_for("admin.users"))

@admin_bp.post("/appeals/<int:appeal_id>/reject")
def reject_ban_appeal(appeal_id):
    appeal = db.session.get(BanAppeal, appeal_id) or abort(404)
    if appeal.status != "pending":
        flash("That appeal has already been reviewed.", "error")
        return redirect(url_for("admin.users"))
    response = request.form.get("response", "").strip()[:2000]
    appeal.status = "rejected"
    appeal.admin_response = response or None
    appeal.reviewed_at = datetime.utcnow()
    db.session.commit()
    flash(f"Appeal from {appeal.user.username} was rejected.", "success")
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
