"""Development convenience: create tables directly with SQLAlchemy.

This is a shortcut for a quick *local* start only. The supported way to create
and evolve the schema – in development and production alike – is Flask-Migrate:

    flask db upgrade

Do not use this script against a production database.
"""
from app import app
from extensions import db

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Development tables created. For production use: flask db upgrade")
