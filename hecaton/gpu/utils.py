import os
import json
import getpass

from hecaton.gpu.argparser import parser
from pydantic import BaseModel
from pathlib import Path
from platformdirs import user_data_path

APP_NAME = "hecaton"
APP_AUTHOR = "Just1truc"

def data_dir() -> Path:
    d = user_data_path(appname=APP_NAME, appauthor=APP_AUTHOR, roaming=False)
    print(d)
    d.mkdir(parents=True, exist_ok=True)
    return d

class WorkerConfig(BaseModel):
    
    secret : str | None = None # Legacy or Token
    token : str | None = None
    username : str | None = None
    password : str | None = None
    worker_id : str

def load_worker_config(server_ip : str) -> WorkerConfig:
    gpu_data_path = data_dir() / "gpu_config.json"
    
    register = {}
    if os.path.exists(gpu_data_path):
        register = json.loads(open(gpu_data_path).read())

    if server_ip in register:
        return WorkerConfig.model_validate(register[server_ip])
    
    # New entry
    print(f"To configure worker for {server_ip}, please provide credentials:")
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    
    new_entry = WorkerConfig(username=username, password=password, worker_id="")
    register[server_ip] = new_entry.model_dump()
    open(gpu_data_path, "w").write(json.dumps(register))
    
    return new_entry

def save_worker_config(ip : str, worker_config : WorkerConfig):
    
    gpu_data_path = data_dir() / "gpu_config.json"
    
    register = {}
    if os.path.exists(gpu_data_path):
        register = json.loads(open(gpu_data_path).read())
        
    register[ip] = worker_config.model_dump()
    open(gpu_data_path, "w").write(json.dumps(register))

