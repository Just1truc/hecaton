from pydantic import BaseModel

class NewJobDTO(BaseModel):
    payload : str
    image : str

class JobUpdateDTO(BaseModel):
    job_id : int
    new_status : str
    new_payload : str | None

class NewImageDTO(BaseModel):
    image_name : str
    
class WorkerConnectionDTO(BaseModel):
    worker_id : int | None
    
class WorkerStatusUpdateDTO(BaseModel):
    worker_id : int
    status : str