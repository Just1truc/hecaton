import shutil
import threading
import time

import requests
import uvicorn

from hecaton.server.auth import get_password_hash
from hecaton.server.main import app, data_dir
from hecaton.server.worker import SQLiteQueue

# Setup test environment
TEST_DIR = data_dir().parent / "hecaton_test_users"
if TEST_DIR.exists():
    shutil.rmtree(TEST_DIR)
TEST_DIR.mkdir()

# Mock data_dir
import hecaton.server.main

hecaton.server.main.data_dir = lambda: TEST_DIR
hecaton.server.main.q = SQLiteQueue(TEST_DIR / "jobs.db")
q = hecaton.server.main.q

# Create admin user
print("Creating admin user...")
admin_pass = "admin123"
q.create_user("admin", get_password_hash(admin_pass), "admin")

# Start server
PORT = 8002


def run_server():
    uvicorn.run(app, port=PORT, host="127.0.0.1", log_level="error")


t = threading.Thread(target=run_server, daemon=True)
t.start()
print("Waiting for server to start...")
time.sleep(3)

BASE_URL = f"http://127.0.0.1:{PORT}"


def get_admin_token():
    res = requests.post(
        f"{BASE_URL}/token", data={"username": "admin", "password": admin_pass}
    )
    assert res.ok, f"Login failed: {res.text}"
    return res.json()["access_token"]


def test_create_user(admin_token):
    print("Testing User Creation...")
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {"username": "newuser", "password": "userpass", "role": "user"}
    res = requests.post(f"{BASE_URL}/users/new", json=payload, headers=headers)
    assert res.ok, f"User creation failed: {res.text}"
    print("User creation successful!")

    # Try login as new user
    print("Testing New User Login...")
    res = requests.post(
        f"{BASE_URL}/token", data={"username": "newuser", "password": "userpass"}
    )
    assert res.ok, f"New user login failed: {res.text}"
    print("New user login successful!")


try:
    token = get_admin_token()
    test_create_user(token)
    print("\nALL TESTS PASSED!")
except Exception as e:
    print(f"\nTEST FAILED: {e}")
    exit(1)
