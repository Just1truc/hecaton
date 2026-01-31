import requests
from hecaton.gpu.utils import *

class GPUWebClient:
    
    def __init__(
        self,
        ip : str,
        worker_config : WorkerConfig
    ):
        self.ip = ip
        self.worker_id  = worker_config.worker_id
        
        # Authentication
        self.token = worker_config.token
        if not self.token and worker_config.username and worker_config.password:
            self.login(worker_config)
            
        self.headers    = {
            "Authorization" : f"Bearer {self.token}" if self.token else ""
        }

        self.__connect_server()
    
    def login(self, config: WorkerConfig):
        ip = self.ip if self.ip.startswith('http') else f'https://{self.ip}'
        try:
            res = requests.post(f"{ip}/token", data={"username": config.username, "password": config.password})
            if res.ok:
                data = res.json()
                self.token = data["access_token"]
                config.token = data["access_token"]
                save_worker_config(self.ip, config)
            else:
                print(f"Failed to login worker: {res.text}")
        except Exception as e:
            print(f"Login error: {e}")

    def __connect_server(self):
        ip = self.ip if self.ip.startswith('http') else f'https://{self.ip}'
        result = requests.post(f'{ip}/workers/connect',
            json={
                **({"worker_id" : int(self.worker_id)} if len(self.worker_id) else {})
            },
            headers=self.headers
        )
        if not(result.ok):
            raise RuntimeError(f"Failed to connect to server {self.ip}. Cause: {result.json()['detail']}")
        
        self.worker_id = str(result.json()["worker_id"])
        
        # Update config with worker_id
        config = load_worker_config(self.ip)
        config.worker_id = self.worker_id
        save_worker_config(self.ip, config)
        
    def get_online_images(self):
        ip = self.ip if self.ip.startswith('http') else f'https://{self.ip}'
        result = requests.get(f'{ip}/images', headers=self.headers)
        
        if not(result.ok):
            raise RuntimeError(F"Failed to fetch images {result.json()['message']}")
        
        return result.json()
    
    def update_status(
        self,
        status : str
    ):
        
        if not self.worker_id:
            raise RuntimeError("Not connected to a server")
        ip = self.ip if self.ip.startswith('http') else f'https://{self.ip}'
        
        result = requests.post(f'{ip}/worker/update', headers=self.headers,
            json={
                "worker_id" : self.worker_id,
                "status" : status
            }
        )
        if not(result.ok):
            raise RuntimeError(F"Failed to update worker status {result.json()['message']}")
        
    def update_job_status(
        self,
        jid : str,
        status : str
    ):  
        ip = self.ip if self.ip.startswith('http') else f'https://{self.ip}'
        result = requests.post(f'{ip}/jobs/update', headers=self.headers,
            json={
                "job_id" : jid,
                "new_status" : status
            }
        )
        if not(result.ok):
            raise RuntimeError(F"Failed to update worker status {result.json()['message']}")
    
    def update_job(
        self,
        jid : str,
        status : str,
        payload : dict
    ):  
        ip = self.ip if self.ip.startswith('http') else f'https://{self.ip}'
        result = requests.post(f'{ip}/jobs/update', headers=self.headers,
            json={
                "job_id" : jid,
                "new_status" : status,
                "new_payload" : payload
            }
        )
        if not(result.ok):
            raise RuntimeError(F"Failed to update worker {result.json()['message']}")
    
    def job_assigned(self):
        
        if not self.worker_id:
            raise RuntimeError("Not connected to a server")
        
            # TODO
        # call server to check if worker as a job assigned
        # needs a new endpoint in server/main.py that calls get_worker_job
        ip = self.ip if self.ip.startswith('http') else f'https://{self.ip}'
        result = requests.get(f'{ip}/worker/{self.worker_id}', headers=self.headers)
        
        if not(result.ok):
            raise RuntimeError(F"Failed to fetch worker job {result.json()['message']}")
        
        jobs = result.json()["jobs"]
        return jobs[0] if len(jobs) else None