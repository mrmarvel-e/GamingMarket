from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user, login_required
from sqlalchemy import or_
from ..extensions import db
from ..models import Game, Listing, ListingPhoto, Deal, Message, Review, User
from ..services import notify

market_bp = Blueprint("market", __name__)

@market_bp.get("/")
def home():
    q = request.args.get("q","").strip()
    game = request.args.get("game","")
    query = Listing.query.filter_by(status="active")
    if q:
        query = query.filter(or_(Listing.title.ilike(f"%{q}%"), Listing.description.ilike(f"%{q}%")))
    if game:
        query = query.join(Game).filter(Game.slug == game)
    listings = query.all()
    # Green pinned listings first, then Premium, then Admin Verified, then normal.
    def key(x):
        s = x.seller.status
        return (0 if (s=="green" and x.top_pinned) else 1,
                1 if s=="green" else 2 if s=="gold" else 3 if s=="purple" else 4,
                -x.created_at.timestamp())
    listings.sort(key=key)
    return render_template("market/home.html", listings=listings, games=Game.query.order_by(Game.name).all(), q=q, game=game)

@market_bp.get("/listing/<int:listing_id>")
def listing_detail(listing_id):
    listing = db.session.get(Listing, listing_id) or abort(404)
    reviews = Review.query.filter_by(seller_id=listing.seller_id).order_by(Review.created_at.desc()).limit(10).all()
    return render_template("market/listing.html", listing=listing, reviews=reviews)

@market_bp.post("/listing/<int:listing_id>/deal")
@login_required
def deal_request(listing_id):
    listing = db.session.get(Listing, listing_id) or abort(404)
    if listing.seller_id == current_user.id:
        flash("You cannot send a deal request to yourself.", "error")
        return redirect(url_for("market.listing_detail", listing_id=listing.id))
    deal = Deal(listing_id=listing.id, buyer_id=current_user.id, seller_id=listing.seller_id)
    db.session.add(deal)
    db.session.flush()
    msg = Message(deal_id=deal.id, sender_id=current_user.id, recipient_id=listing.seller_id,
                  body=request.form.get("message","I'm interested in this account."))
    db.session.add(msg)
    db.session.commit()
    notify(listing.seller, "New Deal Request", f"{current_user.username} is interested in {listing.title}.",
           url_for("seller.deal", deal_id=deal.id))
    flash("Deal request sent. Continue in chat.", "success")
    return redirect(url_for("seller.deal", deal_id=deal.id))

@market_bp.get("/seller/<int:user_id>")
def seller_profile(user_id):
    seller = db.session.get(User, user_id) or abort(404)
    listings = Listing.query.filter_by(seller_id=user_id, status="active").order_by(Listing.created_at.desc()).all()
    reviews = Review.query.filter_by(seller_id=user_id).order_by(Review.created_at.desc()).all()
    return render_template("market/seller.html", seller=seller, listings=listings, reviews=reviews)
