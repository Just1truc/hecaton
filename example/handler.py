from hecaton.serverless import ServerLessInput, start


def my_handler(data: ServerLessInput):
    """
    This is your custom payload handler that will run inside the Docker container.
    """
    # 'data.input' contains the payload submitted via the CLI or API (e.g., payload.json)
    job_payload = data.input

    import torch

    print(f"Processing job with data: {job_payload} ")

    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else None

    # The return value must be a dictionary.
    result = {
        "status": "success",
        "cuda_available": cuda_available,
        "device_name": device_name,
        "processed_data": job_payload,
    }

    # The dictionary returned will be sent back to the server as the output payload
    return result


if __name__ == "__main__":
    print("Starting serverless handler, waiting for jobs in /shared...")
    # This keeps the container running and polls for new jobs
    start(my_handler)
