# GamingMarket

GamingMarket is a Flask + SQLite Nigerian gaming-account marketplace.

## V1.1 replacement build

- Black and red visual theme
- GamingMarket red/black favicon
- Normal login automatically recognizes the configured admin email
- Admin is redirected to the Admin Panel after normal login
- Corrected route imports (`app.routes` now correctly imports from the parent `app` package)
- NGN pricing
- Marketplace browsing without login
- Seller accounts, referrals, Premium, verification, listings, deal chats and admin tools

## Run on Windows

```powershell
cd C:\path\to\GamingMarket
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python run.py
```

Open http://127.0.0.1:5000

### Admin

Use the normal `/login` page with the email configured by `ADMIN_EMAIL` (default: `mrmarveloa@gmail.com`). A successful login for that email is recognized as the admin and redirects directly to `/admin/`.

Set a strong `ADMIN_PASSWORD` in `.env` before use.

### SQLite

The default database is created at `instance/gamingmarket.db`.

## Production / FadeHost

- Runtime: Python + Flask
- Database: SQLite by default
- Local database: `instance/gamingmarket.db`
- For hosted persistence, mount persistent storage and set `SQLITE_DB_PATH` to a file in that mounted directory.
- Never commit `.env`, `instance/gamingmarket.db`, or uploaded files.
- Start command: `python run.py`

## Account Bans

Administrators can ban or unban non-admin accounts from **Admin Panel → Users**. A banned account:

- cannot log in
- is logged out if already signed in and attempts another protected request
- cannot use seller/deal features
- has its marketplace listings hidden while the ban is active
- keeps its listings, deals, chats, and history intact for review

Admins can optionally record a ban reason. Admin accounts cannot be banned from the Users page.
