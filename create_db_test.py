
import sqlite3
import os
import time

if os.path.exists("job.db"):
  os.remove("job.db")

conn = sqlite3.connect("job.db", timeout=30, isolation_level=None)  # autocommit
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")
conn.executescript("""
        CREATE TABLE IF NOT EXISTS workers(
          id TEXT PRIMARY KEY,
          status TEXT NOT NULL CHECK(status IN ('IDLE', 'REQUESTED', 'DEAD', 'RUNNING', 'INITIALIZING')),
          updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );
        CREATE TABLE IF NOT EXISTS jobs(
          id TEXT PRIMARY KEY,
          assigned_worker INTEGER,
          status TEXT NOT NULL CHECK(status IN ('IN_QUEUE', 'ASSIGNED', 'IN_PROGRESS','FINISHED','FAILED','CANCELLED')),
          payload TEXT NOT NULL,
          attempts INTEGER NOT NULL DEFAULT 0,
          last_error TEXT,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
          updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
          FOREIGN KEY(assigned_worker) REFERENCES workers(id)
        );
        CREATE TABLE IF NOT EXISTS images(
          id INTEGER PRIMARY KEY,
          image_name TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS jobs_status_created_idx ON jobs(status, created_at);
""")
conn.execute("INSERT INTO workers(id, status) VALUES (1, 'REQUESTED')")
conn.execute("INSERT INTO workers(id, status) VALUES (2, 'RUNNING')")
conn.execute("INSERT INTO jobs(id, status, payload, assigned_worker) VALUES ('job-1', 'ASSIGNED', 'text', 1)")
conn.execute("INSERT INTO jobs(id, status, payload, assigned_worker) VALUES ('job-2', 'IN_PROGRESS', 'text', 2)")

workers = conn.execute("SELECT * FROM workers").fetchall()
jobs = conn.execute("SELECT * FROM jobs").fetchall()

print("Workers:", workers)
print("Jobs:", jobs)

conn.execute("""
    UPDATE jobs
    SET status = 'IN_QUEUE'
    WHERE (strftime('%s','now') - strftime('%s', updated_at)) > ?
      AND assigned_worker IN (
          SELECT id
          FROM workers
          WHERE status = 'REQUESTED'
      );
""", (10,))
    
conn.execute("""
    UPDATE workers
    SET status = 'DEAD'
    WHERE status = 'REQUESTED'
      AND (strftime('%s','now') - strftime('%s', updated_at)) > ?
""", (10,))

workers = conn.execute("SELECT * FROM workers").fetchall()
jobs = conn.execute("SELECT * FROM jobs").fetchall()

print("Workers:", workers)
print("Jobs:", jobs)

time.sleep(12)

conn.execute("""
    UPDATE jobs
    SET status = 'IN_QUEUE'
    WHERE (strftime('%s','now') - strftime('%s', updated_at)) > ?
      AND assigned_worker IN (
          SELECT id
          FROM workers
          WHERE status = 'REQUESTED'
      );
""", (10,))
    
conn.execute("""
    UPDATE workers
    SET status = 'DEAD'
    WHERE status = 'REQUESTED'
      AND (strftime('%s','now') - strftime('%s', updated_at)) > ?
""", (10,))

workers = conn.execute("SELECT * FROM workers").fetchall()
jobs = conn.execute("SELECT * FROM jobs").fetchall()

print("Workers:", workers)
print("Jobs:", jobs)


