from __future__ import annotations

import json

from typing import List
from pathlib import Path
from datetime import datetime
from filelock import FileLock
from contextlib import contextmanager
from platformdirs import user_data_path
from pydantic import BaseModel, EmailStr, Field

SCHEMA_VERSION = 1

class ServerInfo(BaseModel):
    ip: str
    name: str
    secret: str | None = None # key for legacy auth
    token: str | None = None  # JWT token
    username: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Database(BaseModel):
    version: int = SCHEMA_VERSION
    servers: List[ServerInfo] = Field(default_factory=list)

APP_NAME = "hecaton"
APP_AUTHOR = "Just1truc"

def data_dir() -> Path:
    d = user_data_path(appname=APP_NAME, appauthor=APP_AUTHOR, roaming=False)
    d.mkdir(parents=True, exist_ok=True)
    return d

def db_path() -> Path:
    return data_dir() / "db.json"

def lock_path() -> Path:
    return data_dir() / "db.lock"

def load_db() -> Database:
    p = db_path()
    if not p.exists():
        return Database()
    raw = json.loads(p.read_text(encoding="utf-8"))
    return Database.model_validate(raw)

def _atomic_write(path: Path, data: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)

def save_db(db: Database) -> None:
    text = db.model_dump_json(indent=2, by_alias=True)
    _atomic_write(db_path(), text)

@contextmanager
def with_locked_db(mutate: bool = False):
    """Read DB under a lock; optionally write back on exit if mutate=True."""
    lock = FileLock(str(lock_path()))
    with lock:
        db = load_db()
        yield db
        if mutate:
            save_db(db)
