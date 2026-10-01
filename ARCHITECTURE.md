# GamingMarket Architecture

## Stack
- Flask
- SQLAlchemy
- SQLite
- Jinja templates
- Vanilla CSS/JS
- Web Push via pywebpush

## Core status model
- black: normal seller
- purple: admin verified
- gold: premium
- green: admin verified + premium

`User.has_premium_features` is true for Admin Verified OR active Premium, matching the agreed rule that Admin Verified users receive Premium-equivalent marketplace features.

## Green top listings
`Listing.top_pinned` is only usable by green sellers. The seller is limited to 2 active pinned listings. Marketplace ordering puts those listings first.

## Notifications
Notifications are persisted in SQLite. Browser push subscriptions are stored in `PushSubscription`. Push delivery is best-effort and never blocks marketplace actions.

## Security notes
- Passwords use Werkzeug password hashing.
- Seller bank details are never rendered on public listing pages.
- Admin-only routes are protected by `is_admin`.
- Deal chat access is limited to participants/admin.
- Uploaded filenames are sanitized and randomized.
