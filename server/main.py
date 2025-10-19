import os
import shutil

from typing import Union, Callable, Tuple
from fastapi import FastAPI
from server.argparser import parser
from server.worker import SQLiteQueue
from server.dto import *
from dotenv import load_dotenv

from pathlib import Path

app = FastAPI()

# Middleware for security
import os
import sys

from fastapi import Security, HTTPException
from fastapi import HTTPException, Depends
from fastapi.security import APIKeyHeader
from platformdirs import user_data_path
from fastapi_utilities import repeat_every


APP_NAME = "hecaton"
APP_AUTHOR = "Just1truc"

def data_dir() -> Path:
    d = user_data_path(appname=APP_NAME, appauthor=APP_AUTHOR, roaming=False)
    d.mkdir(parents=True, exist_ok=True)
    return d

if __name__ != "__main__":
    q = SQLiteQueue(data_dir() / "jobs.db")

    load_dotenv(data_dir() / ".env")

    API_SECRET = os.getenv("SECRET")

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

def get_api_key(auth: str = Security(api_key_header)):
    print(auth, API_SECRET)
    if auth != API_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return auth

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

@app.get("/jobs", dependencies=[Depends(get_api_key)])
def all_jobs():
    return provider_call(q, 'get_jobs', ())

@app.post("/jobs/new", dependencies=[Depends(get_api_key)])
def new_job(job_dto : NewJobDTO):
    jid = provider_call(q, "enqueue", (job_dto.payload, job_dto.image))
    return { "job_id" : jid }

@app.get("/jobs/{jid}", dependencies=[Depends(get_api_key)])
def get_job(jid):
    res = provider_call(q, "get_job", (jid,))
    return res

@app.post("/jobs/update/{jid}", dependencies=[Depends(get_api_key)])
def get_job(update_dto : JobUpdateDTO):
    return provider_call(q, "update_job", (update_dto.job_id, update_dto.new_status, update_dto.new_payload))

@app.get("/images", dependencies=[Depends(get_api_key)])
def all_images():
    return provider_call(q, "get_images", ())

@app.post("/images/new", dependencies=[Depends(get_api_key)])
def new_image(image_dto : NewImageDTO):
    provider_call(q, "new_image", (image_dto.image_name,))
    return { "message" : "Successfully added image" }

@app.get("/images/{imid}")
def get_image(imid : int):
    return provider_call(q, 'get_image', (imid,))

@app.get("/workers", dependencies=[Depends(get_api_key)])
def all_workers():
    return provider_call(q, "get_workers", ())

@app.post("/workers/connect", dependencies=[Depends(get_api_key)])
def connect_worker(worker_dto : WorkerConnectionDTO):
    return { "worker_id" : provider_call(q, "connect_worker", (worker_dto.worker_id,)) }

@app.post("/worker/update", dependencies=[Depends(get_api_key)])
def update_worker(worker_update_dto : WorkerStatusUpdateDTO):
    provider_call(q, "update_worker_status", (worker_update_dto.worker_id, worker_update_dto.status))
    return { "message" : "Successfully updated worker status" }

if __name__ == "__main__":
    
    # save argument as secret in .env
    file = sys.argv[1]
    if os.path.exists(file) and os.path.isfile(file):
        shutil.copyfile(file, data_dir() / ".env")
        
    print(f"Properly copied .env in {data_dir() / '.env'}")

    
# print("test")
# if __name__ == "__main__":
#     print("test2")

#     args = parser.parse_args()
#     load_dotenv(args.env)
    
#     if not(os.getenv("SECRET")):
#         print("API secret not set properly in dotenv file. format should be AI_SECRET={secret}")
        
#     q = SQLiteQueue("jobs.db")
