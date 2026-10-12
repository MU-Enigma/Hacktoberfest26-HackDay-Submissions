#!/usr/bin/env python3
"""Create an administrator account (development helper).

Usage:
  export ADMIN_EMAIL=se24admin@mahindrauniversity.edu.in
  export ADMIN_PASSWORD='choose-a-strong-password'
  export ADMIN_NAME='Campus Admin'
  python create_admin.py
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

import database as db

load_dotenv()


def main() -> int:
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "")
    name = os.getenv("ADMIN_NAME", "SideQuest Admin").strip() or "SideQuest Admin"
    domain = os.getenv("UNIVERSITY_EMAIL_DOMAIN", "mahindrauniversity.edu.in").lower()

    if not email or not password:
        print("Set ADMIN_EMAIL and ADMIN_PASSWORD environment variables.", file=sys.stderr)
        return 1
    if "@" not in email or email.split("@", 1)[1] != domain:
        print(f"ADMIN_EMAIL must use @{domain}", file=sys.stderr)
        return 1
    if len(password) < 8:
        print("ADMIN_PASSWORD must be at least 8 characters.", file=sys.stderr)
        return 1

    db.init_db()
    existing = db.get_user_by_email(email)
    if existing:
        with db.db() as conn:
            conn.execute(
                "UPDATE users SET role = 'admin', password_hash = ?, is_suspended = 0 WHERE email = ?",
                (generate_password_hash(password), email),
            )
        print(f"Updated existing user {email} to admin.")
        return 0

    user = db.create_user(
        email=email,
        password=password,
        display_name=name,
        role="admin",
    )
    print(f"Created admin user id={user['id']} email={email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
