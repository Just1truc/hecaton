from hecaton.gpu.utils import *
from hecaton.gpu.web_client import GPUWebClient
from hecaton.gpu.docker_manager import DockerManager
from hecaton.gpu.worker import start_worker

# Main code (Outside the docker)

def main():
    # Outside dockers (in the server)
    # main =>
    # - getpass secret if not registered yet (for a specific server)
    # - try loading existing cache to see if worker is already registered
    args = parser.parse_args()
    worker_config : WorkerConfig = load_worker_config(args.ip)
    # - connect to server (with cached id or no id)
    gpu_web_client = GPUWebClient(args.ip, worker_config=worker_config)
    # - DockerManager.sync =>
    # - Check if local images are the same as online's
    # - sync docker images
    gpu_web_client.update_status('INITIALIZING')
    docker_manager = DockerManager(gpu_web_client)
    gpu_web_client.update_status('IDLE')
    # - Download images that doesn't exist
    # - start worker
    # worker =>
    # - Call hecaton server to check if there is a job (cron every 3 sec)
    # - Keep track of local workers, if one has been running for more that 10min without update, kill it
    # - Pickup job (update job status to running)
    # - start associated imag e (if not already started) with shared as a folder with the name of the image on it
    # - put the job payload in a file in the shared folder
    # - check the folder every 3 seconds
    # - if folder contain output, upload output to server if status is completed (The output is a json file with the status) (allow workers to update with custom statuses)
    start_worker(gpu_web_client, docker_manager)

if __name__ == "__main__":
    
    main()