import sqlite3


def get_db() -> sqlite3.Connection:
    db = sqlite3.connect("db.sqlite3")
    db.execute("PRAGMA foreign_keys = ON")
    return db