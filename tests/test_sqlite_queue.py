import pytest
import shutil
from pathlib import Path
from hecaton.server.worker import SQLiteQueue
from hecaton.server.auth import get_password_hash

@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_jobs.db"
    queue = SQLiteQueue(str(db_path))
    return queue

def test_create_user(test_db):
    uid = test_db.create_user("testuser", get_password_hash("password"), "user")
    assert uid is not None
    
    user = test_db.get_user("testuser")
    assert user is not None
    assert user[1] == "testuser"
    assert user[3] == "user"

def test_create_duplicate_user(test_db):
    test_db.create_user("testuser", get_password_hash("password"), "user")
    uid2 = test_db.create_user("testuser", get_password_hash("password"), "user")
    assert uid2 is None

def test_image_management(test_db):
    # We need to mock requests.get in check_docker_image or mock check_docker_image
    # For now, let's mock check_docker_image in worker.py via monkeypatch
    import hecaton.server.worker
    
    def mock_check_docker_image(image):
        return {"description": "Mocked Description"}
    
    hecaton.server.worker.check_docker_image = mock_check_docker_image
    
    test_db.new_image("test/image:latest")
    images = test_db.get_images()
    assert len(images) == 1
    assert images[0][1] == "test/image:latest"
    assert images[0][2] == "Mocked Description"

def test_job_enqueue(test_db):
    # Mock image check again
    import hecaton.server.worker
    hecaton.server.worker.check_docker_image = lambda i: {"description": "d"}
    
    test_db.new_image("test/image:latest")
    jid = test_db.enqueue("payload", "test/image:latest")
    assert jid is not None
    
    job = test_db.get_job(jid)
    assert job is not None
    assert job[1] == "IN_QUEUE" # Status
    assert job[2] == "payload"

def test_worker_management(test_db):
    wid = test_db.connect_worker(None)
    assert wid is not None
    
    workers = test_db.get_workers()
    assert len(workers) == 1
    assert workers[0][0] == str(wid)
    assert workers[0][1] == "INITIALIZING"
    
    test_db.update_worker_status(wid, "IDLE")
    workers = test_db.get_workers()
    assert workers[0][1] == "IDLE"
