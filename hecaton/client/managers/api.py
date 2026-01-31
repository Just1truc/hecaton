# File that contain the class that communicates with the hecaton's server
import requests
from typing import Optional, List, Tuple

class HecatonServer:
    
    str_to_method = {
        "GET" : requests.get,
        "POST": requests.post,
        "PUT" : requests.put,
        "DELETE" : requests.delete
    }
    
    def call_endpoint(
        ip : str,
        secret : str,
        method : str,
        endpoint : str,
        payload : dict | None = None
    ):
        ip = ip if ip.startswith('https') else f'https://{ip}'
        # result = HecatonServer.str_to_method[method](f"{ip}{endpoint}",
        result = HecatonServer.str_to_method[method](f"{ip}{endpoint}",
            headers = { "Authorization" : f"Bearer {secret}" },
            **({"json" : payload} if method != "GET" else {})
        )
        # )
        return result
    
    def login(ip: str, username: str, password: str):
        ip = ip if ip.startswith('https') else f'https://{ip}'
        result = requests.post(f"{ip}/token", data={"username": username, "password": password})
        if result.ok:
            return result.json()
        return None

    
    def list_jobs(
        ip : str,
        secret : str
    ):
        results = HecatonServer.call_endpoint(
            ip=ip,
            secret=secret,
            method="GET",
            endpoint="/jobs"
        )
        if results.ok:
            return results.json()
        return results.json()["detail"]
    
    def list_images(
        ip : str,
        secret : str
    ):
        results = HecatonServer.call_endpoint(
            ip=ip,
            secret=secret,
            method="GET",
            endpoint="/images"
        )
        # print(results)
        if results.ok:
            return results.json()
        return results.json()["detail"]

    def new_job(
        ip : str,
        secret : str,
        file_path : str,
        image : str
    ):
        file_content = open(file_path, "r").read()
        
        results = HecatonServer.call_endpoint(
            ip=ip,
            secret=secret,
            method="POST",
            endpoint="/jobs/new",
            payload={
                "payload" : file_content,
                "image" : image
            }
        )
        if results.ok:
            return results.json()["job_id"]
        return results.json()["detail"]
    
    def update_image(
        ip,
        secret,
        image : str,
        env : List[Tuple[str, str]] | None = None,
        description : Optional[str] = None
    ):
        results = HecatonServer.call_endpoint(
            ip=ip,
            secret=secret,
            method="POST",
            endpoint="/images/update",
            payload={
                "image_name" : image,
                **({"env" : [{"key" : var[0], "value" : var[1]} for var in env]} if env else {}),
                **({"description" : description} if description else {}) 
            }
        )
        if results.ok:
            return results.json()["message"]
        return results.json()["detail"]
            
    def new_image(
        ip : str,
        secret : str,
        image : str
    ):
        results = HecatonServer.call_endpoint(
            ip=ip,
            secret=secret,
            method="POST",
            endpoint="/images/new",
            payload={
                "image_name" : image,
            }
        )
        if results.ok:
            return results.json()["message"]
        return results.json()["detail"]

    def get_job(
        ip : str,
        secret : str,
        jid : str
    ):
        results = HecatonServer.call_endpoint(
            ip=ip,
            secret=secret,
            method="GET",
            endpoint=f"/jobs/{jid}"
        )
        if results.ok:
            return results.json()
        return results.json()["detail"]

    def create_user(
        ip: str,
        secret: str,
        username: str,
        password: str,
        role: str
    ):
        results = HecatonServer.call_endpoint(
            ip=ip,
            secret=secret,
            method="POST",
            endpoint="/users/new",
            payload={
                "username": username,
                "password": password,
                "role": role
            }
        )
        if results.ok:
            return results.json()["message"]
        return results.json()["detail"]

    def list_workers(
        ip : str,
        secret : str
    ):
        results = HecatonServer.call_endpoint(
            ip=ip,
            secret=secret,
            method="GET",
            endpoint="/workers"
        )
        if results.ok:
            return results.json()
        return results.json()["detail"]