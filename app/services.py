import os, secrets, string
from datetime import datetime, timedelta
from flask import current_app
from .extensions import db
from .models import Notification, PushSubscription

def make_referral_code():
    chars = string.ascii_uppercase + string.digits
    while True:
        code = "GM-" + "".join(secrets.choice(chars) for _ in range(6))
        from .models import User
        if not User.query.filter_by(referral_code=code).first():
            return code

def notify(user, title, body, url="/"):
    n = Notification(user_id=user.id, title=title, body=body, url=url)
    db.session.add(n)
    db.session.commit()
    # Push delivery is best-effort; the in-site notification is always retained.
    send_push(user, title, body, url)

def send_push(user, title, body, url):
    public = current_app.config.get("VAPID_PUBLIC_KEY")
    private = os.getenv("VAPID_PRIVATE_KEY")
    subject = os.getenv("VAPID_SUBJECT")
    if not (public and private and subject):
        return
    try:
        from pywebpush import webpush
        for sub in PushSubscription.query.filter_by(user_id=user.id).all():
            webpush(
                subscription_info={"endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
                data={"title": title, "body": body, "url": url},
                vapid_private_key=private,
                vapid_claims={"sub": subject},
            )
    except Exception:
        # Push should never break marketplace transactions.
        pass
