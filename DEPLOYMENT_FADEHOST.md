# GamingMarket — FadeHost + SQLite deployment

## Local development

GamingMarket uses SQLite by default:

`instance/gamingmarket.db`

## Production SQLite

The app supports either `DATABASE_URL` or `SQLITE_DB_PATH`.

If `DATABASE_URL` is set, it takes priority.

Otherwise, if `SQLITE_DB_PATH` is set, the SQLite database is created there.

Otherwise the default remains `instance/gamingmarket.db`.

### Important
SQLite is only persistent if the directory containing the database is on persistent storage provided by the hosting platform. For FadeHost, configure the app's persistent storage/mount path and set `SQLITE_DB_PATH` to the database file inside that persistent path.

Do not put `.env` in GitHub. Configure secrets as FadeHost environment variables.

Required production variables:

- `SECRET_KEY`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `SQLITE_DB_PATH` (only when using a persistent mounted directory)

Optional push variables:

- `VAPID_PUBLIC_KEY`
- `VAPID_PRIVATE_KEY`
- `VAPID_CLAIMS_EMAIL`

Start command:

`python run.py`

The included `run.py` listens on `0.0.0.0` and uses the `PORT` environment variable when provided.
