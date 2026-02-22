from hecaton.serverless import start, ServerLessInput
from time import time

def my_handler(data: ServerLessInput):
    """
    This is your custom payload handler that will run inside the Docker container.
    """
    # 'data.input' contains the payload submitted via the CLI or API (e.g., payload.json)
    job_payload = data.input
    
    print(f"Processing job with data: {job_payload}")
    time.sleep(10)
    
    # Perform your compute task here (e.g. process data, train a model, generate image)
    # The return value must be a dictionary.
    result = {"status": "success", "processed_data": job_payload}
    
    # The dictionary returned will be sent back to the server as the output payload
    return result

if __name__ == "__main__":
    print("Starting serverless handler, waiting for jobs in /shared...")
    # This keeps the container running and polls for new jobs
    start(my_handler)
