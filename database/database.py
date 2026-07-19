"""
database/database.py
---------------------
Modules 9 & 10 — Favorites/Wishlist and Recently Viewed (both optional
per the MVP doc, both SQLite-backed as specified).

Responsibility:
    All SQLite reads/writes for this project go through this one
    module — the GUI never runs raw SQL itself, matching the same
    "one module owns one concern" principle as api/api_client.py
    owning all network calls.

Design decision — storing full product JSON, not a rigid schema:
    Normalized products (see recommendation/filters.py) already have a
    well-defined shape, but it may grow over time (e.g. future fields).
    Rather than creating a wide SQL table with a column per field —
    which would need a migration every time the product shape changes —
    each row stores the product as a single JSON text column. This is
    a common, pragmatic pattern for small local-storage use cases like
    a wishlist, where we always read/write whole product records, never
    query by individual product fields at the SQL level.

Design decision — database path resolution:
    We build DB_PATH from this file's own location (`__file__`) rather
    than a relative path like "database/wishlist.db". A relative path
    would only work if the app happens to be launched from the project
    root — exactly the kind of "works from one folder, breaks from
    another" bug we already hit once with Python module imports. Using
    __file__ makes the database path correct regardless of the current
    working directory the app was launched from.

Design decision — fail gracefully, never crash the app over local storage:
    Wishlist/Recently-Viewed are explicitly optional MVP features. If
    SQLite ever fails for some environment-specific reason (permissions,
    disk full, locked file), the app should degrade — e.g. wishlist
    button silently doesn't save — rather than crashing the entire GUI
    over a non-essential feature. Every public function here catches
    its own exceptions and returns a safe default.
"""

import os
import json
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "wishlist.db")

RECENTLY_VIEWED_LIMIT = 10  # per MVP doc: "Stores the last 10 viewed products"


def _get_connection():
    return sqlite3.connect(DB_PATH)


def initialize_database():
    """
    Create both tables if they don't already exist. Safe to call every
    time the app starts — CREATE TABLE IF NOT EXISTS is a no-op if the
    schema already exists.
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wishlist (
                product_id TEXT PRIMARY KEY,
                product_json TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recently_viewed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                product_json TEXT NOT NULL,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"[database] Failed to initialize database: {e}")
        return False


# ---------------------------------------------------------------------------
# Module 9 — Wishlist / Favorites
# ---------------------------------------------------------------------------

def add_to_wishlist(product):
    """Save a product to the wishlist. Overwrites if already present."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO wishlist (product_id, product_json) VALUES (?, ?)",
            (product["id"], json.dumps(product)),
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"[database] Failed to add to wishlist: {e}")
        return False


def remove_from_wishlist(product_id):
    """Remove a product from the wishlist by its id."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM wishlist WHERE product_id = ?", (product_id,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"[database] Failed to remove from wishlist: {e}")
        return False


def is_in_wishlist(product_id):
    """Check whether a product is currently saved to the wishlist."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM wishlist WHERE product_id = ?", (product_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except sqlite3.Error as e:
        print(f"[database] Failed to check wishlist: {e}")
        return False


def get_wishlist():
    """Return all wishlisted products (most recently added first)."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT product_json FROM wishlist ORDER BY added_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [json.loads(row[0]) for row in rows]
    except sqlite3.Error as e:
        print(f"[database] Failed to load wishlist: {e}")
        return []


# ---------------------------------------------------------------------------
# Module 10 — Recently Viewed
# ---------------------------------------------------------------------------

def add_recently_viewed(product):
    """
    Record that a product was viewed. If it was already in the recently
    viewed list, its old entry is removed and a fresh one is added at
    the top — viewing the same product twice should bump it up, not
    clutter the list with repeats.

    Design decision — ordering by auto-increment id, not timestamp:
        SQLite's CURRENT_TIMESTAMP only has 1-second resolution. Two
        products viewed within the same second (very plausible — e.g.
        quickly clicking through search results) would get IDENTICAL
        timestamps, making "most recent first" ordering ambiguous and
        breaking the trim-to-10 logic (it could keep the wrong 10 rows
        entirely). We hit this exact bug during testing. Using the
        table's own auto-incrementing `id` column for ordering instead
        guarantees a strict, unambiguous insertion order regardless of
        how fast products are viewed.

    After inserting, trims the table down to the most recent
    RECENTLY_VIEWED_LIMIT entries.
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()

        # Remove any existing entry for this product first, so re-viewing
        # it creates a NEW (higher) id and naturally sorts to the top.
        cursor.execute("DELETE FROM recently_viewed WHERE product_id = ?", (product["id"],))
        cursor.execute(
            "INSERT INTO recently_viewed (product_id, product_json) VALUES (?, ?)",
            (product["id"], json.dumps(product)),
        )

        # Trim to the last N by id, not by timestamp (see design note above).
        cursor.execute("""
            DELETE FROM recently_viewed
            WHERE id NOT IN (
                SELECT id FROM recently_viewed
                ORDER BY id DESC
                LIMIT ?
            )
        """, (RECENTLY_VIEWED_LIMIT,))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"[database] Failed to record recently viewed: {e}")
        return False


def get_recently_viewed():
    """Return the most recently viewed products, most recent first."""
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT product_json FROM recently_viewed ORDER BY id DESC LIMIT ?",
            (RECENTLY_VIEWED_LIMIT,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [json.loads(row[0]) for row in rows]
    except sqlite3.Error as e:
        print(f"[database] Failed to load recently viewed: {e}")
        return []


# ---------------------------------------------------------------------------
# Quick manual test (no network needed — pure SQLite)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    initialize_database()

    sample_product = {
        "id": "test-1", "source": "fakestore", "title": "Test Product",
        "price": 19.99, "category": "electronics", "rating": 4.5,
        "review_count": 10, "discount_percentage": 0, "stock": -1,
        "brand": "", "image": "", "description": "A test product.",
    }

    print("Adding to wishlist:", add_to_wishlist(sample_product))
    print("Is in wishlist:", is_in_wishlist("test-1"))
    print("Wishlist contents:", [p["title"] for p in get_wishlist()])

    print("\nAdding to recently viewed:", add_recently_viewed(sample_product))
    print("Recently viewed:", [p["title"] for p in get_recently_viewed()])

    print("\nRemoving from wishlist:", remove_from_wishlist("test-1"))
    print("Is in wishlist after removal:", is_in_wishlist("test-1"))