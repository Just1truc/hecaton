
import os
import time
import shutil
import threading
import requests
import uvicorn
import contextlib
from pathlib import Path
from hecaton.server.worker import SQLiteQueue
from hecaton.server.auth import get_password_hash
from hecaton.server.main import app, data_dir

# Setup test environment
TEST_DIR = data_dir().parent / "hecaton_test"
if TEST_DIR.exists():
    shutil.rmtree(TEST_DIR)
TEST_DIR.mkdir()

# Mock data_dir
import hecaton.server.main
hecaton.server.main.data_dir = lambda: TEST_DIR
import hecaton.server.worker
# Re-init queue with new path
hecaton.server.main.q = SQLiteQueue(TEST_DIR / "jobs.db")
q = hecaton.server.main.q

# Create admin user
print("Creating admin user...")
admin_pass = "admin123"
q.create_user("admin", get_password_hash(admin_pass), "admin")

# Start server
PORT = 8001
def run_server():
    uvicorn.run(app, port=PORT, host="127.0.0.1", log_level="error")

t = threading.Thread(target=run_server, daemon=True)
t.start()
print("Waiting for server to start...")
time.sleep(3)

BASE_URL = f"http://127.0.0.1:{PORT}"

def test_login():
    print("Testing Login...")
    res = requests.post(f"{BASE_URL}/token", data={"username": "admin", "password": admin_pass})
    assert res.ok, f"Login failed: {res.text}"
    token = res.json()["access_token"]
    print(f"Login successful! Token: {token[:10]}...")
    return token

def test_protected_route(token):
    print("Testing Protected Route (GET /jobs)...")
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/jobs", headers=headers)
    assert res.ok, f"Protected route failed: {res.text}"
    print("Protected route successful!")

def test_unauthorized():
    print("Testing Unauthorized Access...")
    res = requests.get(f"{BASE_URL}/jobs")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"
    print("Unauthorized access blocked correctly!")

try:
    token = test_login()
    test_protected_route(token)
    test_unauthorized()
    print("\nALL TESTS PASSED!")
except Exception as e:
    print(f"\nTEST FAILED: {e}")
    exit(1)
