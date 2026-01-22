#!/usr/bin/env python3
"""Reset database and seed with initial data."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.factory import create_app
from app.extensions import db
from app.seeds.seed_roles import seed_roles
from app.seeds.seed_users import seed_users

def reset_db():
    app = create_app()
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("Recreating tables...")
        db.create_all()
        print("Tables recreated successfully.")
        
        print("\nSeeding roles...")
        seed_roles()
        
        print("\nSeeding users...")
        seed_users()

if __name__ == "__main__":
    reset_db()
