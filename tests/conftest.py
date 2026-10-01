import pytest
from app import create_app
from app.extensions import db
from app.models import User

@pytest.fixture()
def app(tmp_path):
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path/"test.db"), "SECRET_KEY":"test"})
    with app.app_context():
        db.drop_all(); db.create_all()
        from app.seed import seed_games
        seed_games()
    yield app

@pytest.fixture()
def client(app):
    return app.test_client()
