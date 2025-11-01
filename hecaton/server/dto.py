from pydantic import BaseModel
from typing import Optional, List

class NewJobDTO(BaseModel):
    payload : str
    image : str

class JobUpdateDTO(BaseModel):
    job_id : int
    new_status : str
    new_payload : Optional[str] = None

class EnvVariable(BaseModel):
    key : str
    value : str

class UpdateImageDTO(BaseModel):
    image_name : str
    env : Optional[List[EnvVariable]] = None
    description : Optional[str] = None

class NewImageDTO(BaseModel):
    image_name : str
    
class WorkerConnectionDTO(BaseModel):
    worker_id : Optional[int] = None
    
class WorkerStatusUpdateDTO(BaseModel):
    worker_id : int
    status : str
    
class AssignedJobDTO(BaseModel):
    jid : str
    image_name : str
    image_env : Optional[dict]
    status : str
    payload : str
