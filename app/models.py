from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db

def now():
    return datetime.utcnow()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    referral_code = db.Column(db.String(20), unique=True, nullable=False)
    listing_credits = db.Column(db.Integer, default=10, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    admin_verified = db.Column(db.Boolean, default=False)
    premium_until = db.Column(db.DateTime)
    bank_name = db.Column(db.String(120))
    bank_account_name = db.Column(db.String(160))
    bank_account_number = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=now)
    is_banned = db.Column(db.Boolean, default=False, nullable=False)
    banned_at = db.Column(db.DateTime)
    banned_reason = db.Column(db.String(500))

    def set_password(self, value):
        self.password_hash = generate_password_hash(value)

    def check_password(self, value):
        return check_password_hash(self.password_hash, value)

    @property
    def premium_active(self):
        return bool(self.premium_until and self.premium_until > now())

    @property
    def has_premium_features(self):
        return self.admin_verified or self.premium_active

    @property
    def status(self):
        if self.admin_verified and self.premium_active:
            return "green"
        if self.premium_active:
            return "gold"
        if self.admin_verified:
            return "purple"
        return "black"

    @property
    def badge_labels(self):
        labels = []
        if self.admin_verified:
            labels.append("✓ Verified Seller")
        if self.premium_active:
            labels.append("★ Premium")
        return labels

class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    referred_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=now)


class BanAppeal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="pending", nullable=False)
    admin_response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=now)
    reviewed_at = db.Column(db.DateTime)
    user = db.relationship("User", backref=db.backref("ban_appeals", lazy=True))

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.Text, default="")
    fields = db.Column(db.JSON, default=dict)

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey("game.id"), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), default="active", nullable=False)
    attributes = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)

    seller = db.relationship("User", backref="listings")
    game = db.relationship("Game", backref="listings")
    photos = db.relationship("ListingPhoto", backref="listing", cascade="all, delete-orphan")
    top_pinned = db.Column(db.Boolean, default=False, nullable=False)

    @property
    def seller_status(self):
        """Current seller status used for marketplace card styling."""
        return self.seller.status if self.seller else "black"

class ListingPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listing.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    is_cover = db.Column(db.Boolean, default=False)

class Deal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listing.id"), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(30), default="requested", nullable=False)
    offer_amount = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)
    listing = db.relationship("Listing")
    buyer = db.relationship("User", foreign_keys=[buyer_id])
    seller = db.relationship("User", foreign_keys=[seller_id])

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.Integer, db.ForeignKey("deal.id"))
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    body = db.Column(db.Text, nullable=False)
    is_admin_support = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=now)
    sender = db.relationship("User", foreign_keys=[sender_id])
    recipient = db.relationship("User", foreign_keys=[recipient_id])
    deal = db.relationship("Deal")

class DealCredentialVault(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.Integer, db.ForeignKey("deal.id"), nullable=False, unique=True)
    ciphertext = db.Column(db.Text, nullable=False)
    iv = db.Column(db.String(64), nullable=False)
    salt = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)
    deal = db.relationship("Deal", backref=db.backref("credential_vault", uselist=False))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.String(500), nullable=False)
    url = db.Column(db.String(255), default="/")
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=now)

class PushSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    endpoint = db.Column(db.Text, nullable=False, unique=True)
    p256dh = db.Column(db.Text, nullable=False)
    auth = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=now)

class PremiumPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receipt_filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(30), default="pending", nullable=False)
    submitted_at = db.Column(db.DateTime, default=now)
    reviewed_at = db.Column(db.DateTime)
    user = db.relationship("User")

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    deal_id = db.Column(db.Integer, db.ForeignKey("deal.id"), nullable=False, unique=True)
    rating = db.Column(db.Integer, nullable=False)
    body = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=now)
    seller = db.relationship("User", foreign_keys=[seller_id])
    buyer = db.relationship("User", foreign_keys=[buyer_id])
    deal = db.relationship("Deal")

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey("listing.id"))
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="open")
    created_at = db.Column(db.DateTime, default=now)
