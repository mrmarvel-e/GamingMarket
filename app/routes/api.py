from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from ..extensions import db
from ..models import Notification, PushSubscription

api_bp = Blueprint("api", __name__)

@api_bp.get("/notifications")
@login_required
def notifications():
    rows = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(50).all()
    return jsonify([{"id": n.id, "title": n.title, "body": n.body, "url": n.url, "read": n.is_read} for n in rows])

@api_bp.post("/notifications/read")
@login_required
def mark_read():
    for n in Notification.query.filter_by(user_id=current_user.id, is_read=False).all():
        n.is_read = True
    db.session.commit()
    return jsonify({"ok": True})

@api_bp.post("/push/subscribe")
@login_required
def subscribe():
    data = request.get_json(force=True)
    endpoint = data["endpoint"]
    keys = data["keys"]
    row = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if not row:
        row = PushSubscription(user_id=current_user.id, endpoint=endpoint,
                               p256dh=keys["p256dh"], auth=keys["auth"])
        db.session.add(row)
    else:
        row.user_id = current_user.id
        row.p256dh = keys["p256dh"]
        row.auth = keys["auth"]
    db.session.commit()
    return jsonify({"ok": True})
