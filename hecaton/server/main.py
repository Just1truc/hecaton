import os
import shutil
import uvicorn

from typing import Union, Callable, Tuple
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from hecaton.server.argparser import parser
from hecaton.server.worker import SQLiteQueue
from hecaton.server.dto import *
from hecaton.server.auth import *
from dotenv import load_dotenv

from pathlib import Path

app = FastAPI()

# Middleware for security
import os
import sys

from platformdirs import user_data_path
from fastapi_utilities import repeat_every


APP_NAME = "hecaton"
APP_AUTHOR = "Just1truc"

def data_dir() -> Path:
    d = user_data_path(appname=APP_NAME, appauthor=APP_AUTHOR, roaming=False)
    d.mkdir(parents=True, exist_ok=True)
    return d

if not os.path.exists(data_dir() / ".env"):
    file = input("No env found, please enter env file path: ")
    # save argument as secret in .env
    if os.path.exists(file) and os.path.isfile(file):
        shutil.copyfile(file, data_dir() / ".env")

    print(f"Properly copied .env in {data_dir() / '.env'}")

q = SQLiteQueue(data_dir() / "jobs.db")

load_dotenv(data_dir() / ".env")

API_SECRET = os.getenv("SECRET")
if not API_SECRET:
    # If no secret in env, generate one and save it
    import secrets
    API_SECRET = secrets.token_urlsafe(32)
    with open(data_dir() / ".env", "a") as f:
        f.write(f"\nSECRET={API_SECRET}\n")
    print(f"Generated new API SECRET: {API_SECRET}")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = decode_access_token(token, API_SECRET)
    if token_data is None:
        raise credentials_exception
    user = q.get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    # user row: id, username, hashed_password, role, created_at
    return User(username=user[1], role=user[3])

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    return current_user

async def get_current_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = q.get_user(form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # user row: id, username, hashed_password, role, created_at
    hashed_password = user[2]
    if not verify_password(form_data.password, hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user[1], "role": user[3]}, secret_key=API_SECRET, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Error Handler => transform error from Provider to HTTP error
def provider_call(provider, method : Callable, args : Tuple):
    try:
        return getattr(provider, method)(*args)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event('startup')
@repeat_every(seconds=3)
async def job_handler():
    # Assign jobs
    # Check alive workers + resassign jobs
    q.check_workers_alive()
    q.assign_jobs()

@app.on_event('startup')
async def startup_check():
    # Check if we have any admin user
    # If users table is empty or no admin, prompt creation or use Env vars
    # For simplicity, let's just check if 'admin' exists.
    admin_user = q.get_user("admin")
    if not admin_user:
        admin_pass = os.getenv("HECATON_ADMIN_PASS")
        if admin_pass:
            q.create_user("admin", get_password_hash(admin_pass), "admin")
            print(f"Created admin user from environment variable.")
        else:
            print("WARNING: No admin user found. You should create one or set HECATON_ADMIN_PASS env var.")

@app.post("/users/new", dependencies=[Depends(get_current_admin_user)])
def create_user(user_dto: NewUserDTO):
    uid = q.create_user(user_dto.username, get_password_hash(user_dto.password), user_dto.role)
    if not uid:
        raise HTTPException(status_code=400, detail="Username already exists")
    return {"message": f"User {user_dto.username} created successfully", "user_id": uid}

@app.get("/jobs", dependencies=[Depends(get_current_active_user)])
def all_jobs():
    return provider_call(q, 'get_jobs', ())

@app.post("/jobs/new", dependencies=[Depends(get_current_active_user)])
def new_job(job_dto : NewJobDTO):
    jid = provider_call(q, "enqueue", (job_dto.payload, job_dto.image))
    return { "job_id" : jid }

@app.get("/jobs/{jid}", dependencies=[Depends(get_current_active_user)])
def get_job(jid):
    res = provider_call(q, "get_job", (jid,))
    return res

@app.post("/jobs/update", dependencies=[Depends(get_current_active_user)])
def update_job(update_dto : JobUpdateDTO):
    # TODO: Verify that only the assigned worker can update the job? Or admin
    # For now, just authenticated users
    return provider_call(q, "update_job", (update_dto.job_id, update_dto.new_status, update_dto.new_payload))

@app.get("/images", dependencies=[Depends(get_current_active_user)])
def all_images():
    return provider_call(q, "get_images", ())

@app.post("/images/new", dependencies=[Depends(get_current_active_user)])
def new_image(image_dto : NewImageDTO):
    provider_call(q, "new_image", (image_dto.image_name,))
    return { "message" : "Successfully added image" }

@app.post("/images/update", dependencies=[Depends(get_current_active_user)])
def update_image(update_image_dto : UpdateImageDTO):
    provider_call(q, "update_image", (update_image_dto,))
    return { "message": f"Successfully updated image {update_image_dto.image_name}" }

@app.get("/images/{imid}")
def get_image(imid : int):
    # Public?
    return provider_call(q, 'get_image', (imid,))

@app.get("/workers", dependencies=[Depends(get_current_active_user)])
def all_workers():
    return provider_call(q, "get_workers", ())

@app.post("/workers/connect", dependencies=[Depends(get_current_active_user)])
def connect_worker(worker_dto : WorkerConnectionDTO):
    return { "worker_id" : provider_call(q, "connect_worker", (worker_dto.worker_id,)) }

@app.post("/worker/update", dependencies=[Depends(get_current_active_user)])
def update_worker(worker_update_dto : WorkerStatusUpdateDTO):
    provider_call(q, "update_worker_status", (worker_update_dto.worker_id, worker_update_dto.status))
    return { "message" : "Successfully updated worker status" }

# endpoint to get a worker's current job
@app.get("/worker/{wid}", dependencies=[Depends(get_current_active_user)])
def get_worker_job(worker_id : int):
    job : AssignedJobDTO | None = provider_call(q, "get_worker_job", (worker_id,))
    return { "jobs" : [job.model_dump()] if job else [] }

def main():
    args = parser.parse_args()
    uvicorn.run(
        "hecaton.server.main:app", 
        host=args.host, 
        port=int(args.port), 
        reload=False,
        ssl_keyfile=args.ssl_keyfile,
        ssl_certfile=args.ssl_certfile
    )
    
if __name__ == "__main__":
    main()