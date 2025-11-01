import time

from hecaton.gpu.web_client     import GPUWebClient
from hecaton.gpu.docker_manager import DockerManager

# worker =>
    # - Call hecaton server to check if there is a job (cron every 3 sec)
    # - Keep track of local workers, if one has been running for more that 10min without update, kill it
    # - Pickup job (update job status to running)
    # - start associated imag e (if not already started) with shared as a folder with the name of the image on it
    # - put the job payload in a file in the shared folder
    # - check the folder every 3 seconds
    # - if folder contain output, upload output to server if status is completed (The output is a json file with the status) (allow workers to update with custom statuses)

def start_worker(
    web_client : GPUWebClient,
    docker_manager : DockerManager
):
    # resync image before starting a job
    
    REFRESH_FREQ = 10
    refresh_interval = 1
    while True:
        # TODO
        # if GPUWebClient.job_assigned
        # DockerManager.start_job
        job = web_client.job_assigned()
        if job:
            # pickup job
            web_client.update_status('RUNNING')
            web_client.update_job_status(job["jid"], "IN_PROGRESS")
            
            # This will be awaited until the job is finished
            report = docker_manager.run_job(
                image       = job["image_name"],
                job_id      = job["jid"],
                job_payload = job["payload"],
                image_env   = job["image_env"]
            )
            web_client.update_job(job["jid"], report["status"], { "output" : report["output"], "process_time" : report["process_time"] } )
        
        # every 10 times, resync images
        if refresh_interval % REFRESH_FREQ == 0:
            web_client.update_status('SYNCHRONIZING')
            docker_manager.resync()
            web_client.update_status('IDLE')
            refresh_interval = 0
        else:
            if job:
                # only say idle if SYNCHRONIZED
                web_client.update_status('IDLE')
                    
        # Wait 3s between each action to unsure not spaming the bandwidth
        time.sleep(3)
        refresh_interval += 1