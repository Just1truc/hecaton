import os
import time
import json

from typing import Callable
from pydantic import BaseModel, Json, Any

class ServerLessInput(BaseModel):
    input : Json[Any]

def report_job(
    new_status : str,
    output : str = ""
):
    jobs = [file for file in os.listdir("/shared") if file.startswith("job_")]
    job = jobs[0]
    jid = job[5:-6]
    open(f"/shared/result_{jid}.json", "w").write(json.dumps({
        "status" : new_status,
        "output" : output
    }))
    
# Inside docker
def start(handler : Callable[[ServerLessInput], dict]):
    
    # TODO
    # Last part: 
    
    # Read the shared folder until there is an input job_[job_id].json
    # => if input, read and send in handler
    # => wait for handler to finish then write output inside the result_[job_id].json
    while True:
        
        jobs = [file for file in os.listdir("/shared") if file.startswith("job_")]
        if len(jobs):
            job = jobs[0]
            job_data = json.loads(open(f"/shared/{job}").read())
            output = handler(ServerLessInput(job_data["input"]))
            report_job("COMPLETED", output)
            os.remove(f"/shared/{job}")

        time.sleep(1)