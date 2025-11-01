import time
import docker
import tempfile

from typing import Optional
from hecaton.gpu.web_client import *

# - DockerManager.sync =>
# - Check if local images are the same as online's
# - sync docker images
# - Download images that doesn't exist
# - start worker

class DockerManager:
    
    def __init__(
        self,
        web_client : GPUWebClient
    ):
        self.network_client = web_client
        self.docker_client = docker.from_env()
        
        self.__sync_images()
        
    def __sync_images(self):
        
        images = self.network_client.get_online_images()
        
        # get local images, compare
        online_images   = [image[1] for image in images]
        local_images    = [image.tags[0].split(":")[0] for image in self.docker_client.images.list()]
        
        # Syncing images
        for online_image in online_images:
            if not online_image in local_images:
                self.docker_client.images.pull(online_image)
           
    def __start_container(
        self,
        image : str,
        env : Optional[dict]
    ):
        # TODO
        # when the server send back that a job needs to be picked up, a container need to be started
        # use docker sdk (self.docker_client) to check if a worker is already running an image,
        # start image with shared folder as container name in tmp
        
        running = [
            c for c in self.docker_client.containers.list()
            if image == c.image.tags[0].split(":")[0]
        ]
        if running:
            print(f"Container already running for image '{image}': {running[0].name}")
            return running[0]
        
        shared_dir = tempfile.mkdtemp(prefix="shared_")
        print(f"Created shared directory at: {shared_dir}")
        
        clean_env = (env and {var["key"]: var["value"] for var in env }) or {}
        container = self.docker_client.containers.run(
            image=image,
            detach=True,
            environment=clean_env,
            volumes={
                shared_dir: {'bind': '/shared', 'mode': 'rw'}
            },
            name=f"{image.replace('/', '_')}_instance"
        )
        
        return container, shared_dir
    
    def resync(self):
        self.__sync_images()
    
    def run_job(
        self, 
        image   : str,
        job_id  : str,
        job_payload : str,
        image_env : Optional[dict]
    ):
        # TODO
        # start container
        # write job_payload in shared folder with container job_[job_id].json
        # wait for result_[job_id].json to be given in shared folder
        # if "status" in result_[job_id].json is COMPLETED or time > TIMEOUT
        # => return
        start = time.time()
        container, shared = self.__start_container(image, image_env)
        
        # save read payload:
        try:
            payload = json.loads(job_payload)
        except:
            payload = job_payload
        
        # start job
        # write job inside of container
        open(f"{shared}/job_[{job_id}].json", "w").write(json.dumps({
            "input" : payload
        }))
        results = {
            "output" : "",
            "status" : "IN_PROGRESS",
            "process_time" : ""
        }
        last_status = "IN_PROGRESS"
        while True:
            if os.path.exists(f"{shared}/result_[{job_id}].json"):
                file_content = open(f"{shared}/result_[{job_id}].json")
                try:
                    loaded = json.loads(file_content)
                    if loaded["status"] != last_status:
                        self.network_client.update_job_status(job_id, loaded["status"])
                    if loaded["status"] == "COMPLETED" or loaded["status"] == "FAILED":
                        results = loaded
                except:
                    results = {
                        "output": "Failed to process program output",
                        "status": "FAILED"
                    }
                    break
            time.sleep(1)
        
        end = time.time()
        results["process_time"] = end - start
        os.remove(f"{shared}/result_{job_id}.json")
        
        return results