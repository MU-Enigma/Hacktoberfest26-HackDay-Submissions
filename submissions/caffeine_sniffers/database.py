"""SQLite persistence for SideQuest."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator, Optional

from werkzeug.security import check_password_hash, generate_password_hash

from year_utils import study_year_from_email

DB_PATH = Path(__file__).resolve().parent / "sidequest.db"
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
SCHEMA_VERSION = "v3"

CATEGORIES = [
    "Coffee",
    "Games",
    "Music",
    "Study",
    "Outdoors",
    "Creative",
    "Tech",
    "Food",
]

CONNECTION_TYPES = ["friends", "dating", "either"]
GENDER_OPTIONS = [
    "woman",
    "man",
    "non_binary",
    "self_describe",
    "prefer_not_to_say",
]
INVITE_POLICIES = ["everyone", "women", "men", "non_binary", "custom"]

DEFAULT_AVATARS = ["star", "blob", "flower", "spark"]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def _parse_list(raw: Any) -> list:
    if isinstance(raw, list):
        return raw
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


def init_db() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / ".gitkeep").touch(exist_ok=True)

    with db() as conn:
        version = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='meta'"
        ).fetchone()
        meldhee_info = None
        if version:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = 'schema_version'"
            ).fetchone()
            if not row or row["value"] != SCHEMA_VERSION:
                # Prototype reset: save existing meldhee admin if present
                users_table = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
                ).fetchone()
                if users_table:
                    m_row = conn.execute(
                        "SELECT * FROM users WHERE email LIKE '%meldhee%' OR (role = 'admin' AND is_demo = 0)"
                    ).fetchone()
                    if m_row:
                        meldhee_info = {
                            "email": "meldhee@sdheeraj.is-cool.dev",
                            "password_hash": m_row["password_hash"],
                            "display_name": m_row["display_name"] or "Campus Moderator",
                            "role": "admin",
                        }
                conn.executescript(
                    """
                    DROP TABLE IF EXISTS reports;
                    DROP TABLE IF EXISTS participants;
                    DROP TABLE IF EXISTS activities;
                    DROP TABLE IF EXISTS users;
                    DROP TABLE IF EXISTS meta;
                    """
                )

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                password_hash TEXT,
                display_name TEXT NOT NULL,
                bio TEXT NOT NULL DEFAULT '',
                interests TEXT NOT NULL DEFAULT '[]',
                preferred_categories TEXT NOT NULL DEFAULT '[]',
                connection_preference TEXT NOT NULL DEFAULT 'either',
                gender TEXT NOT NULL DEFAULT 'prefer_not_to_say',
                gender_self_describe TEXT NOT NULL DEFAULT '',
                avatar_path TEXT,
                default_avatar TEXT NOT NULL DEFAULT 'star',
                role TEXT NOT NULL DEFAULT 'user',
                is_suspended INTEGER NOT NULL DEFAULT 0,
                is_demo INTEGER NOT NULL DEFAULT 0,
                profile_visibility TEXT NOT NULL DEFAULT 'public',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                starts_at TEXT NOT NULL,
                ends_at TEXT,
                venue TEXT NOT NULL,
                capacity INTEGER NOT NULL,
                connection_type TEXT NOT NULL,
                invite_policy TEXT NOT NULL DEFAULT 'everyone',
                invite_genders TEXT NOT NULL DEFAULT '[]',
                interest_tags TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                seed_key TEXT UNIQUE,
                FOREIGN KEY (host_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS participants (
                user_id INTEGER NOT NULL,
                activity_id INTEGER NOT NULL,
                joined_at TEXT NOT NULL,
                PRIMARY KEY (user_id, activity_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER,
                activity_id INTEGER,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                FOREIGN KEY (reporter_id) REFERENCES users(id),
                FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
            (SCHEMA_VERSION,),
        )
    seed_if_needed(preserved_admin=meldhee_info)


def row_to_user(row: sqlite3.Row, *, public: bool = False) -> dict[str, Any]:
    email = row["email"] or ""
    year_info = study_year_from_email(email) if email else {
        "cohort_year": None,
        "study_year": None,
        "study_year_label": None,
        "badge_label": None,
        "branch_name": None,
        "branch_code": None,
        "recognized": False,
    }
    avatar_url = None
    if row["avatar_path"]:
        avatar_url = f"/uploads/{Path(row['avatar_path']).name}"

    full_name = (row["display_name"] or "").strip()
    first_name = full_name.split()[0] if full_name else "Student"
    keys = row.keys()
    profile_visibility = row["profile_visibility"] if "profile_visibility" in keys else "public"
    badge_label = year_info.get("badge_label") or year_info.get("study_year_label")

    user = {
        "id": row["id"],
        "display_name": row["display_name"],
        "first_name": first_name,
        "bio": row["bio"],
        "interests": [str(x) for x in _parse_list(row["interests"])],
        "preferred_categories": [
            str(x) for x in _parse_list(row["preferred_categories"])
        ],
        "connection_preference": row["connection_preference"],
        "default_avatar": row["default_avatar"] or "star",
        "avatar_url": avatar_url,
        "study_year_label": year_info["study_year_label"],
        "badge_label": badge_label,
        "branch_name": year_info.get("branch_name"),
        "study_year": year_info["study_year"],
        "cohort_year": year_info["cohort_year"],
        "is_demo": bool(row["is_demo"]),
        "profile_visibility": profile_visibility,
    }
    if public:
        if profile_visibility == "minimal":
            user["display_name"] = first_name
            user["bio"] = ""
            user["interests"] = []
            user["preferred_categories"] = []
        elif profile_visibility == "first_name_only":
            user["display_name"] = first_name
    else:
        user.update(
            {
                "email": email,
                "gender": row["gender"],
                "gender_self_describe": row["gender_self_describe"] or "",
                "role": row["role"],
                "is_suspended": bool(row["is_suspended"]),
                "created_at": row["created_at"],
            }
        )
    return user


def activity_base(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "host_id": row["host_id"],
        "title": row["title"],
        "description": row["description"],
        "category": row["category"],
        "starts_at": row["starts_at"],
        "ends_at": row["ends_at"],
        "venue": row["venue"],
        "capacity": row["capacity"],
        "connection_type": row["connection_type"],
        "invite_policy": row["invite_policy"] or "everyone",
        "invite_genders": [str(x) for x in _parse_list(row["invite_genders"])],
        "interest_tags": [str(x) for x in _parse_list(row["interest_tags"])],
        "status": row["status"],
        "created_at": row["created_at"],
    }


def invite_label(policy: str, genders: Optional[list] = None) -> str:
    labels = {
        "everyone": "Everyone",
        "women": "Women only",
        "men": "Men only",
        "non_binary": "Non-binary participants only",
        "custom": "Custom guest list",
    }
    if policy == "custom" and genders:
        nice = {
            "woman": "women",
            "man": "men",
            "non_binary": "non-binary",
            "self_describe": "self-described",
        }
        parts = [nice.get(g, g) for g in genders]
        return "Custom: " + ", ".join(parts)
    return labels.get(policy, "Everyone")


def user_eligible_for_activity(
    user: dict[str, Any], activity: dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """Backend eligibility — gender is never exposed to other users via this message."""
    policy = activity.get("invite_policy") or "everyone"
    if policy == "everyone":
        return True, None

    gender = user.get("gender") or "prefer_not_to_say"
    if gender == "prefer_not_to_say":
        return (
            False,
            "this quest has a guest list. set your gender on your profile to check eligibility "
            "(prefer-not-to-say profiles can't join restricted quests).",
        )

    if policy == "women" and gender != "woman":
        return False, "this quest is for women only."
    if policy == "men" and gender != "man":
        return False, "this quest is for men only."
    if policy == "non_binary" and gender != "non_binary":
        return False, "this quest is for non-binary participants only."
    if policy == "custom":
        allowed = activity.get("invite_genders") or []
        if gender not in allowed:
            return False, "you're not on this quest's guest list."
    return True, None


def seed_if_needed(preserved_admin: Optional[dict[str, Any]] = None) -> None:
    with db() as conn:
        seeded = conn.execute(
            "SELECT value FROM meta WHERE key = 'seeded_v3'"
        ).fetchone()
        if seeded:
            return

        now = datetime.now()
        pw = generate_password_hash("demo1234")

        users = [
            # email, name, bio, interests, pref, gender, cats, avatar, role
            (
                "se25ucse100@sdheeraj.is-cool.dev",
                "Aanya Kapoor",
                "second-year CSE vibes. collects stickers, builds weird bots, and overcommits to group chats.",
                ["board games", "coffee", "indie music", "photography"],
                "either",
                "woman",
                ["Games", "Coffee", "Music", "Outdoors"],
                "flower",
                "user",
            ),
            (
                "se24ucse002@sdheeraj.is-cool.dev",
                "Rohan Mehta",
                "building cursed side projects and occasionally sleeping.",
                ["coding", "tech", "late-night study", "anime"],
                "friends",
                "man",
                ["Tech", "Study", "Games"],
                "spark",
                "user",
            ),
            (
                "se26uecm024@sdheeraj.is-cool.dev",
                "Sara Iqbal",
                "walks with a camera, leaves with twelve almost-good shots.",
                ["photography", "outdoors", "creative", "journaling"],
                "friends",
                "woman",
                ["Outdoors", "Creative"],
                "star",
                "user",
            ),
            (
                "se25uaid004@sdheeraj.is-cool.dev",
                "Dev Patel",
                "human espresso. will trade playlists for life advice.",
                ["indie music", "coffee", "food", "conversations"],
                "dating",
                "man",
                ["Music", "Coffee", "Food"],
                "blob",
                "user",
            ),
            (
                "se23ucse005@sdheeraj.is-cool.dev",
                "Maya Sharma",
                "academic comeback arc in progress. snacks are policy.",
                ["study", "drawing", "anime", "board games"],
                "either",
                "non_binary",
                ["Study", "Creative", "Games"],
                "flower",
                "user",
            ),
            (
                "se24umech006@sdheeraj.is-cool.dev",
                "Kabir Nair",
                "badminton crusader. also hungry always.",
                ["sports", "food", "outdoors", "music"],
                "friends",
                "man",
                ["Outdoors", "Food", "Music"],
                "spark",
                "user",
            ),
            (
                "se26ucse007@sdheeraj.is-cool.dev",
                "Priya Sen",
                "first-year explorer. here for chai and chaos.",
                ["coffee", "creative", "friendship"],
                "friends",
                "woman",
                ["Coffee", "Creative"],
                "star",
                "user",
            ),
        ]

        user_ids: list[int] = []
        for email, name, bio, interests, pref, gender, cats, avatar, role in users:
            cur = conn.execute(
                """
                INSERT INTO users (
                    email, password_hash, display_name, bio, interests,
                    preferred_categories, connection_preference, gender,
                    default_avatar, role, is_demo, profile_visibility, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'public', ?)
                """,
                (
                    email,
                    pw,
                    name,
                    bio,
                    json.dumps(interests),
                    json.dumps(cats),
                    pref,
                    gender,
                    avatar,
                    role,
                    _iso(now),
                ),
            )
            user_ids.append(cur.lastrowid)

        # Seed/preserve admin meldhee
        admin_email = "meldhee@sdheeraj.is-cool.dev"
        admin_pw_hash = (
            preserved_admin.get("password_hash")
            if preserved_admin and preserved_admin.get("password_hash")
            else "scrypt:32768:8:1$eFV5WZ3feCW9qkDP$d2d4fe8e3f0265c688cb2d12d782e7931e84685cc594e0749f025557d22c18b9b217500acf33dd28fb7ddd621c1f2ec033069d3ae9171f1a8d04aa8f90b3962b"
        )
        admin_name = (
            preserved_admin.get("display_name")
            if preserved_admin and preserved_admin.get("display_name")
            else "Campus Moderator"
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO users (
                email, password_hash, display_name, bio, interests,
                preferred_categories, connection_preference, gender,
                default_avatar, role, is_demo, profile_visibility, created_at
            ) VALUES (?, ?, ?, ?, '["community", "safety"]', '["Tech", "Coffee"]', 'either', 'prefer_not_to_say', 'star', 'admin', 0, 'public', ?)
            """,
            (
                admin_email,
                admin_pw_hash,
                admin_name,
                "Campus moderation desk · Keeping Mahindra University adventures wholesome and fun.",
                _iso(now),
            ),
        )
        conn.execute("DELETE FROM users WHERE email = 'se24admin@mahindrauniversity.edu.in'")

        activities = [
            (
                "seed-board-game",
                user_ids[0],
                "the most unserious board game night",
                "losing gracefully is optional. snacks are emotionally mandatory.",
                "Games",
                now + timedelta(days=2, hours=4),
                now + timedelta(days=2, hours=7),
                "Student Lounge, Block A",
                8,
                "either",
                "everyone",
                [],
                ["board games", "snacks", "friendship"],
            ),
            (
                "seed-indie-music",
                user_ids[3],
                "indie music exchange",
                "bring three songs. leave with five new obsessions.",
                "Music",
                now + timedelta(days=1, hours=6),
                now + timedelta(days=1, hours=8),
                "Amphitheatre Steps",
                10,
                "either",
                "everyone",
                [],
                ["indie music", "playlists", "conversations"],
            ),
            (
                "seed-coffee",
                user_ids[3],
                "coffee & questionable life decisions",
                "let's overthink absolutely nothing together.",
                "Coffee",
                now + timedelta(days=3, hours=2),
                None,
                "Campus Café Courtyard",
                6,
                "dating",
                "everyone",
                [],
                ["coffee", "conversations", "friendship"],
            ),
            (
                "seed-study",
                user_ids[4],
                "study squad: academic comeback arc",
                "we are locking in. allegedly.",
                "Study",
                now + timedelta(days=1, hours=10),
                now + timedelta(days=1, hours=13),
                "Library Quiet Zone",
                6,
                "friends",
                "everyone",
                [],
                ["study", "late-night study", "focus"],
            ),
            (
                "seed-photo",
                user_ids[2],
                "tiny photography walk",
                "collect pretty corners and pretend we're in an indie film.",
                "Outdoors",
                now + timedelta(days=4, hours=3),
                now + timedelta(days=4, hours=5),
                "Main Gate → Lake Path",
                5,
                "friends",
                "everyone",
                [],
                ["photography", "outdoors", "creative"],
            ),
            (
                "seed-tech",
                user_ids[1],
                "build something cursed",
                "bring your weird project idea. judgment-free zone.",
                "Tech",
                now + timedelta(days=5, hours=5),
                now + timedelta(days=5, hours=8),
                "Innovation Lab",
                8,
                "friends",
                "everyone",
                [],
                ["coding", "tech", "side projects"],
            ),
            (
                "seed-doodle",
                user_ids[4],
                "doodle club",
                "art skills optional. drawing little guys encouraged.",
                "Creative",
                now + timedelta(days=2, hours=8),
                now + timedelta(days=2, hours=10),
                "Art Nook, Creative Space",
                12,
                "either",
                "everyone",
                [],
                ["drawing", "journaling", "creative"],
            ),
            (
                "seed-food",
                user_ids[5],
                "campus food crawl",
                "taste-test three stalls. rate them like film critics.",
                "Food",
                now + timedelta(days=6, hours=1),
                None,
                "Food Court Circuit",
                7,
                "either",
                "everyone",
                [],
                ["food", "conversations", "outdoors"],
            ),
            (
                "seed-badminton",
                user_ids[5],
                "badminton and new friends",
                "casual rallies, zero Olympic pressure, maximum high-fives.",
                "Outdoors",
                now + timedelta(days=3, hours=5),
                now + timedelta(days=3, hours=7),
                "Sports Complex Courts",
                8,
                "friends",
                "everyone",
                [],
                ["sports", "outdoors", "friendship"],
            ),
            (
                "seed-women-circle",
                user_ids[0],
                "cozy women-only journal circle",
                "soft lighting, softer opinions, zero unsolicited advice.",
                "Creative",
                now + timedelta(days=4, hours=8),
                None,
                "Quiet Corner, Block B",
                6,
                "friends",
                "women",
                [],
                ["journaling", "creative", "friendship"],
            ),
            (
                "seed-past",
                user_ids[0],
                "yesterday's coffee chat (archived vibes)",
                "this one already happened — for past adventures demos.",
                "Coffee",
                now - timedelta(days=2),
                now - timedelta(days=2) + timedelta(hours=2),
                "Campus Café Courtyard",
                4,
                "friends",
                "everyone",
                [],
                ["coffee"],
            ),
        ]

        activity_ids: dict[str, int] = {}
        for item in activities:
            (
                seed_key,
                host_id,
                title,
                description,
                category,
                starts,
                ends,
                venue,
                capacity,
                ctype,
                invite,
                invite_g,
                tags,
            ) = item
            ends_at = _iso(ends) if ends else None
            status = "past" if starts < now else "open"
            cur = conn.execute(
                """
                INSERT INTO activities (
                    host_id, title, description, category, starts_at, ends_at,
                    venue, capacity, connection_type, invite_policy, invite_genders,
                    interest_tags, status, created_at, seed_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    host_id,
                    title,
                    description,
                    category,
                    _iso(starts),
                    ends_at,
                    venue,
                    capacity,
                    ctype,
                    invite,
                    json.dumps(invite_g),
                    json.dumps(tags),
                    status,
                    _iso(now - timedelta(days=1)),
                    seed_key,
                ),
            )
            activity_ids[seed_key] = cur.lastrowid

        joins = [
            (user_ids[0], activity_ids["seed-board-game"]),
            (user_ids[1], activity_ids["seed-board-game"]),
            (user_ids[4], activity_ids["seed-board-game"]),
            (user_ids[3], activity_ids["seed-indie-music"]),
            (user_ids[0], activity_ids["seed-indie-music"]),
            (user_ids[3], activity_ids["seed-coffee"]),
            (user_ids[4], activity_ids["seed-study"]),
            (user_ids[1], activity_ids["seed-study"]),
            (user_ids[2], activity_ids["seed-photo"]),
            (user_ids[0], activity_ids["seed-photo"]),
            (user_ids[1], activity_ids["seed-tech"]),
            (user_ids[4], activity_ids["seed-doodle"]),
            (user_ids[5], activity_ids["seed-food"]),
            (user_ids[5], activity_ids["seed-badminton"]),
            (user_ids[1], activity_ids["seed-badminton"]),
            (user_ids[0], activity_ids["seed-women-circle"]),
            (user_ids[2], activity_ids["seed-women-circle"]),
            (user_ids[0], activity_ids["seed-past"]),
            (user_ids[3], activity_ids["seed-past"]),
        ]
        for uid, aid in joins:
            conn.execute(
                """
                INSERT OR IGNORE INTO participants (user_id, activity_id, joined_at)
                VALUES (?, ?, ?)
                """,
                (uid, aid, _iso(now - timedelta(hours=6))),
            )

        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('seeded_v3', ?)",
            (_iso(now),),
        )


def create_user(
    *,
    email: str,
    password: str,
    display_name: str,
    gender: str = "prefer_not_to_say",
    gender_self_describe: str = "",
    connection_preference: str = "either",
    interests: Optional[list] = None,
    role: str = "user",
    profile_visibility: str = "public",
) -> dict[str, Any]:
    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO users (
                email, password_hash, display_name, bio, interests,
                preferred_categories, connection_preference, gender,
                gender_self_describe, default_avatar, role, is_demo,
                profile_visibility, created_at
            ) VALUES (?, ?, ?, ?, ?, '[]', ?, ?, ?, 'star', ?, 0, ?, ?)
            """,
            (
                email.lower().strip(),
                generate_password_hash(password),
                display_name.strip(),
                "",
                json.dumps(interests or []),
                connection_preference,
                gender,
                gender_self_describe,
                role,
                profile_visibility,
                _iso(datetime.now()),
            ),
        )
        uid = cur.lastrowid
    return get_user(uid)  # type: ignore[return-value]


def authenticate(email: str, password: str) -> Optional[dict[str, Any]]:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
        ).fetchone()
        if not row:
            return None
        if row["is_suspended"]:
            return {"__error__": "suspended"}
        if not row["password_hash"] or not check_password_hash(
            row["password_hash"], password
        ):
            return None
        return row_to_user(row)


def get_user(user_id: int, *, public: bool = False) -> Optional[dict[str, Any]]:
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return None
        user = row_to_user(row, public=public)
        joined = conn.execute(
            "SELECT COUNT(*) AS c FROM participants WHERE user_id = ?", (user_id,)
        ).fetchone()["c"]
        hosted = conn.execute(
            "SELECT COUNT(*) AS c FROM activities WHERE host_id = ?", (user_id,)
        ).fetchone()["c"]
        user["joined_count"] = joined
        user["hosted_count"] = hosted
        return user


def get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
        ).fetchone()
        if not row:
            return None
        return row_to_user(row)


def update_user(user_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return None
        fields = {
            "display_name": data.get("display_name", row["display_name"]),
            "bio": data.get("bio", row["bio"]),
            "interests": json.dumps(
                data.get("interests", _parse_list(row["interests"]))
            ),
            "preferred_categories": json.dumps(
                data.get(
                    "preferred_categories", _parse_list(row["preferred_categories"])
                )
            ),
            "connection_preference": data.get(
                "connection_preference", row["connection_preference"]
            ),
            "gender": data.get("gender", row["gender"]),
            "gender_self_describe": data.get(
                "gender_self_describe", row["gender_self_describe"]
            ),
            "default_avatar": data.get("default_avatar", row["default_avatar"]),
            "avatar_path": data.get("avatar_path", row["avatar_path"])
            if "avatar_path" in data
            else row["avatar_path"],
            "profile_visibility": data.get(
                "profile_visibility",
                row["profile_visibility"] if "profile_visibility" in row.keys() else "public",
            ),
        }
        if data.get("clear_avatar"):
            fields["avatar_path"] = None
        conn.execute(
            """
            UPDATE users SET
                display_name=?, bio=?, interests=?, preferred_categories=?,
                connection_preference=?, gender=?, gender_self_describe=?,
                default_avatar=?, avatar_path=?, profile_visibility=?
            WHERE id=?
            """,
            (
                fields["display_name"],
                fields["bio"],
                fields["interests"],
                fields["preferred_categories"],
                fields["connection_preference"],
                fields["gender"],
                fields["gender_self_describe"],
                fields["default_avatar"],
                fields["avatar_path"],
                fields["profile_visibility"],
                user_id,
            ),
        )
    return get_user(user_id)


def set_user_suspended(user_id: int, suspended: bool) -> Optional[dict[str, Any]]:
    with db() as conn:
        conn.execute(
            "UPDATE users SET is_suspended = ? WHERE id = ?",
            (1 if suspended else 0, user_id),
        )
    return get_user(user_id)


def list_users() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
        return [row_to_user(r) for r in rows]


def _enrich_activity(
    conn: sqlite3.Connection, row: sqlite3.Row, viewer_id: Optional[int] = None
) -> dict[str, Any]:
    activity = activity_base(row)
    host = conn.execute(
        "SELECT * FROM users WHERE id = ?", (activity["host_id"],)
    ).fetchone()
    participants = conn.execute(
        """
        SELECT u.id, u.display_name, u.default_avatar, u.avatar_path, u.email, u.bio, u.interests, u.profile_visibility
        FROM participants p
        JOIN users u ON u.id = p.user_id
        WHERE p.activity_id = ?
        ORDER BY p.joined_at
        """,
        (activity["id"],),
    ).fetchall()
    count = len(participants)
    host_public = row_to_user(host, public=True)
    activity["host"] = {
        "id": host_public["id"],
        "display_name": host_public["display_name"],
        "first_name": host_public["first_name"],
        "avatar_url": host_public["avatar_url"],
        "default_avatar": host_public["default_avatar"],
        "study_year_label": host_public["study_year_label"],
        "badge_label": host_public["badge_label"],
        "profile_visibility": host_public.get("profile_visibility", "public"),
    }
    activity["participant_count"] = count
    activity["spots_left"] = max(0, activity["capacity"] - count)
    activity["is_full"] = count >= activity["capacity"]
    activity["invite_label"] = invite_label(
        activity["invite_policy"], activity["invite_genders"]
    )
    activity["participants"] = []
    for p in participants:
        year = study_year_from_email(p["email"] or "")
        avatar_url = (
            f"/uploads/{Path(p['avatar_path']).name}" if p["avatar_path"] else None
        )
        full_name = (p["display_name"] or "").strip()
        fname = full_name.split()[0] if full_name else "Student"
        p_vis = p["profile_visibility"] if "profile_visibility" in p.keys() else "public"
        shown_name = fname if p_vis in ("first_name_only", "minimal") else full_name

        activity["participants"].append(
            {
                "id": p["id"],
                "first_name": fname,
                "display_name": shown_name,
                "full_name": full_name,
                "avatar_url": avatar_url,
                "default_avatar": p["default_avatar"],
                "study_year_label": year["study_year_label"],
                "badge_label": year["badge_label"],
                "bio": p["bio"] if p_vis != "minimal" else "",
                "interests": [str(x) for x in _parse_list(p["interests"])] if p_vis != "minimal" else [],
                "profile_visibility": p_vis,
            }
        )
    activity["joined"] = False
    activity["is_host"] = False
    activity["eligible"] = True
    activity["eligibility_message"] = None
    if viewer_id is not None:
        activity["joined"] = any(p["id"] == viewer_id for p in participants)
        activity["is_host"] = activity["host_id"] == viewer_id
        viewer = conn.execute(
            "SELECT * FROM users WHERE id = ?", (viewer_id,)
        ).fetchone()
        if viewer:
            ok, msg = user_eligible_for_activity(row_to_user(viewer), activity)
            activity["eligible"] = ok
            activity["eligibility_message"] = msg
    try:
        starts = datetime.fromisoformat(activity["starts_at"])
        if starts < datetime.now() and activity["status"] == "open":
            activity["status"] = "past"
            conn.execute(
                "UPDATE activities SET status = 'past' WHERE id = ?",
                (activity["id"],),
            )
    except ValueError:
        pass
    return activity


def list_activities(
    *,
    category: Optional[str] = None,
    connection_type: Optional[str] = None,
    include_past: bool = False,
    viewer_id: Optional[int] = None,
    include_removed: bool = False,
) -> list[dict[str, Any]]:
    with db() as conn:
        if include_removed:
            rows = conn.execute(
                "SELECT * FROM activities ORDER BY starts_at ASC"
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM activities
                WHERE status != 'cancelled'
                ORDER BY starts_at ASC
                """
            ).fetchall()
        results = []
        now = datetime.now()
        for row in rows:
            activity = _enrich_activity(conn, row, viewer_id)
            starts = datetime.fromisoformat(activity["starts_at"])
            is_past = starts < now or activity["status"] == "past"
            if not include_past and is_past:
                continue
            if category and category != "All" and activity["category"] != category:
                continue
            if connection_type and connection_type != "all":
                ct = activity["connection_type"]
                if connection_type == "friends" and ct not in ("friends", "either"):
                    continue
                elif connection_type == "dating" and ct not in ("dating", "either"):
                    continue
                elif connection_type == "either" and ct != "either":
                    continue
            results.append(activity)
        return results


def get_activity(
    activity_id: int, viewer_id: Optional[int] = None
) -> Optional[dict[str, Any]]:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM activities WHERE id = ?", (activity_id,)
        ).fetchone()
        if not row:
            return None
        return _enrich_activity(conn, row, viewer_id)


def create_activity(host_id: int, data: dict[str, Any]) -> dict[str, Any]:
    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO activities (
                host_id, title, description, category, starts_at, ends_at,
                venue, capacity, connection_type, invite_policy, invite_genders,
                interest_tags, status, created_at, seed_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, NULL)
            """,
            (
                host_id,
                data["title"],
                data["description"],
                data["category"],
                data["starts_at"],
                data.get("ends_at"),
                data["venue"],
                data["capacity"],
                data["connection_type"],
                data.get("invite_policy", "everyone"),
                json.dumps(data.get("invite_genders", [])),
                json.dumps(data.get("interest_tags", [])),
                _iso(datetime.now()),
            ),
        )
        activity_id = cur.lastrowid
        conn.execute(
            """
            INSERT INTO participants (user_id, activity_id, joined_at)
            VALUES (?, ?, ?)
            """,
            (host_id, activity_id, _iso(datetime.now())),
        )
    return get_activity(activity_id, host_id)  # type: ignore[return-value]


def cancel_activity(activity_id: int) -> Optional[dict[str, Any]]:
    with db() as conn:
        conn.execute(
            "UPDATE activities SET status = 'cancelled' WHERE id = ?",
            (activity_id,),
        )
    return get_activity(activity_id)


def join_activity(activity_id: int, user_id: int) -> tuple[bool, str, Optional[dict]]:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row:
            return False, "user_not_found", None
        if row["is_suspended"]:
            return False, "suspended", None
        user = row_to_user(row)
        act_row = conn.execute(
            "SELECT * FROM activities WHERE id = ?", (activity_id,)
        ).fetchone()
        if not act_row:
            return False, "quest_not_found", None
        activity = _enrich_activity(conn, act_row, user_id)
        if activity["status"] == "cancelled":
            return False, "cancelled", activity
        if datetime.fromisoformat(activity["starts_at"]) < datetime.now():
            return False, "past", activity
        if activity["joined"]:
            return False, "already_joined", activity
        if activity["is_full"]:
            return False, "full", activity
        ok, _msg = user_eligible_for_activity(user, activity)
        if not ok:
            return False, "ineligible", activity
        conn.execute(
            """
            INSERT INTO participants (user_id, activity_id, joined_at)
            VALUES (?, ?, ?)
            """,
            (user_id, activity_id, _iso(datetime.now())),
        )
    return True, "joined", get_activity(activity_id, user_id)


def leave_activity(activity_id: int, user_id: int) -> tuple[bool, str, Optional[dict]]:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM activities WHERE id = ?", (activity_id,)
        ).fetchone()
        if not row:
            return False, "quest_not_found", None
        activity = _enrich_activity(conn, row, user_id)
        if activity["host_id"] == user_id:
            return False, "host_cannot_leave", activity
        if not activity["joined"]:
            return False, "not_joined", activity
        conn.execute(
            "DELETE FROM participants WHERE user_id = ? AND activity_id = ?",
            (user_id, activity_id),
        )
    return True, "left", get_activity(activity_id, user_id)


def my_quests(user_id: int) -> dict[str, list[dict[str, Any]]]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT a.*
            FROM activities a
            LEFT JOIN participants p ON p.activity_id = a.id
            WHERE (a.host_id = ? OR p.user_id = ?) AND a.status != 'cancelled'
            ORDER BY a.starts_at ASC
            """,
            (user_id, user_id),
        ).fetchall()
        coming_up: list[dict[str, Any]] = []
        hosted: list[dict[str, Any]] = []
        past: list[dict[str, Any]] = []
        now = datetime.now()
        for row in rows:
            activity = _enrich_activity(conn, row, user_id)
            is_past = (
                datetime.fromisoformat(activity["starts_at"]) < now
                or activity["status"] == "past"
            )
            if activity["host_id"] == user_id:
                hosted.append(activity)
            if is_past:
                past.append(activity)
            elif activity["joined"] or activity["host_id"] == user_id:
                coming_up.append(activity)
        return {"coming_up": coming_up, "hosted": hosted, "past": past}


def score_activity(user: dict[str, Any], activity: dict[str, Any]) -> dict[str, Any]:
    user_interests = {i.lower() for i in user.get("interests", [])}
    tags = {t.lower() for t in activity.get("interest_tags", [])}
    shared = sorted(user_interests & tags)
    score = 0
    reasons: list[str] = []

    if shared:
        score += 10 * len(shared)
        if len(shared) >= 2:
            reasons.append(f"{shared[0]} + {shared[1]}")
        else:
            reasons.append(shared[0])

    preferred = {c.lower() for c in user.get("preferred_categories", [])}
    if activity["category"].lower() in preferred:
        score += 8
        reasons.append(f"{activity['category'].lower()} chaos")

    pref = user.get("connection_preference", "either")
    ctype = activity["connection_type"]
    if pref == "either" or ctype == "either" or pref == ctype:
        score += 4
    elif pref != ctype:
        score -= 5

    if not activity.get("is_full"):
        score += 2
    else:
        score -= 20

    if activity.get("eligible") is False:
        score -= 15

    if reasons:
        explanation = (
            "this one's right up your alley: " + " + ".join(reasons[:2]) + " ✿"
        )
    else:
        explanation = "coming up on campus soon — worth a peek ✿"

    return {
        "score": score,
        "shared_interests": shared,
        "explanation": explanation,
    }


def recommend_activities(user_id: int, limit: int = 6) -> list[dict[str, Any]]:
    user = get_user(user_id)
    if not user:
        return []
    activities = list_activities(viewer_id=user_id)
    ranked = []
    for activity in activities:
        if activity.get("joined"):
            continue
        meta = score_activity(user, activity)
        ranked.append({**activity, "recommendation": meta})
    ranked.sort(key=lambda a: (-a["recommendation"]["score"], a["starts_at"]))
    return ranked[:limit]


def icebreaker_for(user: dict[str, Any], activity: dict[str, Any]) -> dict[str, Any]:
    shared = sorted(
        {i.lower() for i in user.get("interests", [])}
        & {t.lower() for t in activity.get("interest_tags", [])}
    )
    prompts = {
        "photography": "you both love photography. who gets to be the designated photographer and who gets to look mysterious?",
        "indie music": "shared indie-music brainrot. which song is currently living rent-free in your head?",
        "board games": "board-game allies! cooperative chaos or gleeful betrayal?",
        "coffee": "coffee overlap unlocked. hot take: best campus drink order?",
        "coding": "fellow builders — what's the cursed idea you'd ship this semester?",
        "study": "study-squad energy. which subject's currently bullying you?",
        "drawing": "little-guys energy. what do you doodle when lectures get long?",
        "anime": "anime overlap. comfort rewatch or current obsession?",
        "food": "foodie alignment. which stall is secretly elite?",
        "outdoors": "outdoor souls. sunrise walk or golden-hour wander?",
        "sports": "sporty crossover. competitive or just vibes?",
        "journaling": "journal club detected. prompts or free-write chaos?",
    }
    if shared:
        topic = shared[0]
        prompt = prompts.get(
            topic,
            f"you both like {topic}. wild opener: what's your most niche take on it?",
        )
        return {"prompt": prompt, "shared_interests": shared, "source": "overlap"}
    return {
        "prompt": "icebreaker: if this quest had a movie title, what would it be?",
        "shared_interests": [],
        "source": "general",
    }


def create_report(reporter_id: int, activity_id: int, reason: str) -> dict[str, Any]:
    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO reports (reporter_id, activity_id, reason, status, created_at)
            VALUES (?, ?, ?, 'open', ?)
            """,
            (reporter_id, activity_id, reason.strip()[:500], _iso(datetime.now())),
        )
        rid = cur.lastrowid
    return get_report(rid)  # type: ignore[return-value]


def get_report(report_id: int) -> Optional[dict[str, Any]]:
    with db() as conn:
        row = conn.execute(
            """
            SELECT r.*, u.display_name AS reporter_name, a.title AS activity_title
            FROM reports r
            LEFT JOIN users u ON u.id = r.reporter_id
            LEFT JOIN activities a ON a.id = r.activity_id
            WHERE r.id = ?
            """,
            (report_id,),
        ).fetchone()
        if not row:
            return None
        return dict(row)


def list_reports(status: Optional[str] = None) -> list[dict[str, Any]]:
    with db() as conn:
        if status:
            rows = conn.execute(
                """
                SELECT r.*, u.display_name AS reporter_name, a.title AS activity_title
                FROM reports r
                LEFT JOIN users u ON u.id = r.reporter_id
                LEFT JOIN activities a ON a.id = r.activity_id
                WHERE r.status = ?
                ORDER BY r.created_at DESC
                """,
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT r.*, u.display_name AS reporter_name, a.title AS activity_title
                FROM reports r
                LEFT JOIN users u ON u.id = r.reporter_id
                LEFT JOIN activities a ON a.id = r.activity_id
                ORDER BY r.created_at DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]


def set_report_status(report_id: int, status: str) -> Optional[dict[str, Any]]:
    with db() as conn:
        conn.execute(
            "UPDATE reports SET status = ? WHERE id = ?", (status, report_id)
        )
    return get_report(report_id)


def admin_stats() -> dict[str, Any]:
    with db() as conn:
        users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        activities = conn.execute(
            "SELECT COUNT(*) AS c FROM activities WHERE status != 'cancelled'"
        ).fetchone()["c"]
        open_reports = conn.execute(
            "SELECT COUNT(*) AS c FROM reports WHERE status = 'open'"
        ).fetchone()["c"]
        suspended = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE is_suspended = 1"
        ).fetchone()["c"]
    return {
        "users": users,
        "activities": activities,
        "open_reports": open_reports,
        "suspended_users": suspended,
    }


def get_user_public_profile(user_id: int) -> Optional[dict[str, Any]]:
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return None
        user = row_to_user(row, public=False)
        vis = user.get("profile_visibility", "public")

        # Strip private auth fields
        user.pop("password_hash", None)
        user.pop("gender_self_describe", None)
        user.pop("role", None)
        user.pop("is_suspended", None)
        user.pop("is_demo", None)

        if vis == "minimal":
            user["display_name"] = user["first_name"]
            user["bio"] = ""
            user["interests"] = []
            user["preferred_categories"] = []
            user["email"] = ""
            user["gender"] = "undisclosed"
        elif vis == "first_name_only":
            user["display_name"] = user["first_name"]
            user["email"] = ""
            user["gender"] = "undisclosed"
        else:  # public
            user["email"] = user.get("email", "")

        # Hosted activities
        hosted_rows = conn.execute(
            "SELECT * FROM activities WHERE host_id = ? AND status != 'cancelled' ORDER BY starts_at ASC",
            (user_id,),
        ).fetchall()
        user["hosted_activities"] = [_enrich_activity(conn, r) for r in hosted_rows]

        # Joined activities
        joined_rows = conn.execute(
            """
            SELECT a.* FROM activities a
            JOIN participants p ON p.activity_id = a.id
            WHERE p.user_id = ? AND a.host_id != ? AND a.status != 'cancelled'
            ORDER BY a.starts_at ASC
            """,
            (user_id, user_id),
        ).fetchall()
        user["joined_activities"] = [_enrich_activity(conn, r) for r in joined_rows]
        user["joined_count"] = len(user["joined_activities"])
        user["hosted_count"] = len(user["hosted_activities"])
        return user


def admin_update_user(user_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return None

        display_name = data.get("display_name", row["display_name"])
        email = data.get("email", row["email"])
        role = data.get("role", row["role"])
        bio = data.get("bio", row["bio"])
        gender = data.get("gender", row["gender"])
        gender_self = data.get("gender_self_describe", row["gender_self_describe"])
        pref = data.get("connection_preference", row["connection_preference"])
        is_suspended = (
            1
            if ("is_suspended" in data and bool(data["is_suspended"]))
            else (1 if row["is_suspended"] else 0)
        )
        visibility = data.get(
            "profile_visibility",
            row["profile_visibility"]
            if "profile_visibility" in row.keys()
            else "public",
        )

        conn.execute(
            """
            UPDATE users SET
                display_name = ?,
                email = ?,
                role = ?,
                bio = ?,
                gender = ?,
                gender_self_describe = ?,
                connection_preference = ?,
                is_suspended = ?,
                profile_visibility = ?
            WHERE id = ?
            """,
            (
                display_name,
                email,
                role,
                bio,
                gender,
                gender_self,
                pref,
                is_suspended,
                visibility,
                user_id,
            ),
        )
    return get_user(user_id)


def reset_database_to_default() -> bool:
    with db() as conn:
        # Preserve meldhee admin user if present
        meldhee_row = conn.execute(
            "SELECT * FROM users WHERE email LIKE '%meldhee%' OR (role = 'admin' AND is_demo = 0)"
        ).fetchone()
        meldhee_info = None
        if meldhee_row:
            meldhee_info = {
                "email": "meldhee@sdheeraj.is-cool.dev",
                "password_hash": meldhee_row["password_hash"],
                "display_name": meldhee_row["display_name"] or "Campus Moderator",
                "role": "admin",
            }

        conn.executescript(
            """
            DELETE FROM reports;
            DELETE FROM participants;
            DELETE FROM activities;
            DELETE FROM users;
            DELETE FROM meta WHERE key = 'seeded_v3';
            """
        )
    seed_if_needed(preserved_admin=meldhee_info)
    return True
