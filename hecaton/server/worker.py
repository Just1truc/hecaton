import json, sqlite3, uuid, threading
import requests

from hecaton.server.dto import AssignedJobDTO, UpdateImageDTO

# In seconds
TIMEOUT_TIME = 30

def check_docker_image(image : str):
    
    assert len(image.split('/')) == 2, "Invalid docker image format"
    user, image_name = image.split("/")
    
    result = requests.get(f'http://hub.docker.com/v2/namespaces/{user}/repositories/{image_name}').json()
    if "message" in result and result["message"] == "object no found":
        raise Exception(f"Image is not available or doesn't exists ({image})")
    
    return { "description" : result["description"] }

class SQLiteQueue:
    def __init__(self, path="jobs.db"):
        
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(
            path,
            timeout=30,
            isolation_level=None,   # autocommit
            check_same_thread=False # <-- key
        )
        self.execute("PRAGMA journal_mode=WAL;")
        self.execute("PRAGMA synchronous=NORMAL;")
        self._init_schema()
        
    def execute(self, sql, params=()):
        with self._lock:
            return self.conn.execute(sql, params)

    def executescript(self, script):
        with self._lock:
            return self.conn.executescript(script)

    def _init_schema(self):
        self.executescript("""
        CREATE TABLE IF NOT EXISTS workers(
          id TEXT PRIMARY KEY,
          status TEXT NOT NULL CHECK(status IN ('IDLE', 'REQUESTED', 'DEAD', 'RUNNING', 'INITIALIZING', 'SYNCHRONIZING')),
          updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );
        CREATE TABLE IF NOT EXISTS users(
          id TEXT PRIMARY KEY,
          username TEXT NOT NULL UNIQUE,
          hashed_password TEXT NOT NULL,
          role TEXT NOT NULL DEFAULT 'user',
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );
        CREATE TABLE IF NOT EXISTS images(
          id INTEGER PRIMARY KEY,
          image_name TEXT NOT NULL UNIQUE,
          description TEXT,
          env TEXT
        );
        CREATE TABLE IF NOT EXISTS jobs(
          id TEXT PRIMARY KEY,
          image_id INTEGER,
          assigned_worker INTEGER,
          status TEXT NOT NULL CHECK(status IN ('IN_QUEUE','IN_PROGRESS','FINISHED','FAILED','CANCELLED', 'ASSIGNED')),
          payload TEXT NOT NULL,
          attempts INTEGER NOT NULL DEFAULT 0,
          last_error TEXT,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
          updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
          FOREIGN KEY(image_id) REFERENCES images(id),
          FOREIGN KEY(assigned_worker) REFERENCES workers(id)
        );
        CREATE INDEX IF NOT EXISTS jobs_status_created_idx ON jobs(status, created_at);
        """)

    # New job
    def enqueue(self, payload: str, image : str):
        row = self.execute("SELECT * FROM images WHERE image_name=?", (image,)).fetchone()
        
        if not row:
            raise Exception(f"No image found with the name: {image}")
        
        # row is (id, image_name, description, env)
        id_ = row[0]
        
        jid = str(uuid.uuid4())
        self.execute(
            "INSERT INTO jobs(id,status,payload,image_id) VALUES(?, 'IN_QUEUE', ?, ?)",
            (jid, payload, id_),
        )
        return jid

    def _now(self): return ("".join,)
    
    # Get all workers
    def get_workers(self):
        row = self.execute("SELECT * FROM workers").fetchall()
        return row
    
    # Get all jobs
    def get_jobs(self):
        row = self.execute("SELECT jobs.id, images.image_name, jobs.status, jobs.updated_at FROM jobs INNER JOIN images on jobs.image_id = images.id").fetchall()
        return row

    # Get all images
    def get_images(self):
        row = self.execute("SELECT * FROM images").fetchall()
        return row
    
    def get_image(self, imid : int):
        return self.execute("SELECT * FROM images WHERE id=?", (imid,)).fetchone()
    
    # Post new image
    def new_image(self, image : str):
        # Check if image is a valid docker image + get information on docker image
        repo_info = check_docker_image(image)
        
        max_id = self.execute("SELECT MAX(id) FROM images").fetchone()[0]
        # max_id can be None if table empty
        new_id = (max_id or 0) + 1
        
        self.execute(
            "INSERT INTO images(id,image_name, description) VALUES(?, ?, ?)",
            (new_id, image, repo_info['description']),
        )
        
    def update_image(
        self,
        image_update : UpdateImageDTO
    ):
        query = []
        args = []
        if image_update.description:
            query.append("description=?")
            args.append(image_update.description)
        if image_update.env:
            query.append("env=?")
            args.append(json.dumps([var.model_dump() for var in image_update.env]))
        if not len(query):
            return
        query = ",".join(query)
        self.execute(f"UPDATE images SET {query} WHERE image_name=?", args)

    # Assign idle workers to jobs that don't have an assigned worker
    def assign_jobs(self) -> str:
        
        available_workers = self.execute("SELECT * FROM workers WHERE status='IDLE'").fetchall()
        awaiting_jobs = self.execute("SELECT * FROM jobs WHERE status='IN_QUEUE'").fetchall()
        
        for worker in available_workers:
            job_to_assign = awaiting_jobs.pop(0)
            # Update the job
            self.execute("UPDATE jobs SET assigned_worker=?, status='ASSIGNED', updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?", (worker.id, job_to_assign.id))
            # Update the worker to REQUESTED
            self.update_worker_status(worker.id, 'REQUESTED')
            
    def get_worker_job(self, worker_id : int) -> AssignedJobDTO | None:
        row = self.execute("SELECT (jobs.id, images.image_name, image.env, jobs.status, jobs.payload) FROM jobs INNER JOIN images on jobs.image_id = images.id WHERE assigned_worker=?", (worker_id,)).fetchone()
        if not row or not len(row):
            return None
        jid, image_name, image_env, status, payload = row
        return AssignedJobDTO(jid, image_name, (image_env and json.loads(image_env)), status, payload)
    
    # Update workers status
    def update_worker_status(self, worker_id : int, worker_status : str):
        self.execute("UPDATE workers SET status=?, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?", (worker_status, worker_id))
    
    # Connect new worker
    def connect_worker(self, worker_id : int | None):
        # connecting existing worker
        if (worker_id):
            self.update_worker_status(worker_id=worker_id, worker_status='INITIALIZING')
            return worker_id
        else:
            # Connecting new worker
            max_id = self.execute("SELECT MAX(id) FROM workers").fetchone()[0]
            new_id = (int(max_id) if max_id is not None else 0) + 1
            self.execute(
                "INSERT INTO workers(id,status) VALUES(?, 'INITIALIZING')",
                (new_id,),
            )
            return new_id
    
    # Set Job Status
    def update_job(self, job_id : str, new_status : str, new_payload : str | None):
        if (new_payload):
            self.execute("UPDATE jobs SET status=?, payload=? WHERE id=?", (new_status, new_payload, job_id))
        else:
            self.execute("UPDATE jobs SET status=? WHERE id=?", (new_status, job_id))
    
    # Get Job
    def get_job(self, jid):
        row = self.execute("SELECT id,status,payload,attempts,last_error FROM jobs WHERE id=?", (jid,)).fetchone()
        if not row: return None
        return row

    # Kill worker that didn't pickup jobs
    def check_workers_alive(self):
        self.execute("""
            UPDATE jobs
            SET status = 'IN_QUEUE'
            WHERE (strftime('%s','now') - strftime('%s', updated_at)) > ?
              AND assigned_worker IN (
                  SELECT id
                  FROM workers
                  WHERE status = 'REQUESTED'
              );
        """, (10,))

        self.execute("""
            UPDATE workers
            SET status = 'DEAD'
            WHERE status = 'REQUESTED'
              AND (strftime('%s','now') - strftime('%s', updated_at)) > ?
        """, (10,))
        
        #TODO: Finish this
        # Make the server endpoints
        
        # Make the gpu client (Simple 10s wait before updating job to done)
        # In gpu client, initlization by getting the images
        # Installing unknown images
        # Make the API for the workers
        # Auto Check if cuda is installed on the device before start
        
        # Make client CLI
        # Test everything

    # User Management
    def create_user(self, username, hashed_password, role='user'):
        uid = str(uuid.uuid4())
        try:
            self.execute(
                "INSERT INTO users(id, username, hashed_password, role) VALUES(?, ?, ?, ?)",
                (uid, username, hashed_password, role)
            )
            return uid
        except sqlite3.IntegrityError:
            return None # Username already exists

    def get_user(self, username):
        return self.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()