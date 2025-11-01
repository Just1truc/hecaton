import requests
from hecaton.gpu.utils import *

class GPUWebClient:
    
    def __init__(
        self,
        ip : str,
        worker_config : WorkerConfig
    ):
        self.ip = ip
        self.secret     = worker_config.secret
        self.worker_id  = worker_config.worker_id
        self.headers    = {
            "Authorization" : self.secret
        }

        self.__connect_server()
    
    def __connect_server(self):
        
        result = requests.post(f'{self.ip}/workers/connect',
            json={
                **({"worker_id" : int(self.worker_id)} if len(self.worker_id) else {})
            },
            headers=self.headers
        )
        if not(result.ok):
            raise RuntimeError(f"Failed to connect to server {self.ip}. Cause: {result.json()['message']}")
        
        self.worker_id = str(result.json()["worker_id"])
        
        save_worker_config(self.ip, WorkerConfig(secret=self.secret, worker_id=self.worker_id))
        
    def get_online_images(self):
        
        result = requests.get(f'{self.ip}/images', headers=self.headers)
        
        if not(result.ok):
            raise RuntimeError(F"Failed to fetch images {result.json()['message']}")
        
        return result.json()
    
    def update_status(
        self,
        status : str
    ):
        
        if not self.worker_id:
            raise RuntimeError("Not connected to a server")
        
        result = requests.post(f'{self.ip}/worker/update', headers=self.headers,
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
        result = requests.post(f'{self.ip}/jobs/update', headers=self.headers,
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
        result = requests.post(f'{self.ip}/jobs/update', headers=self.headers,
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
        result = requests.get(f'{self.ip}/worker/{self.worker_id}', headers=self.headers)
        
        if not(result.ok):
            raise RuntimeError(F"Failed to fetch worker job {result.json()['message']}")
        
        jobs = result.json()["jobs"]
        return jobs[0] if len(jobs) else None