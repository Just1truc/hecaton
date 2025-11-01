from hecaton.client.managers.image  import ImageManager, image_app
from hecaton.client.managers.server import ServerManager, server_app
from hecaton.client.managers.job    import JobManager, job_app

class Apps:
    
    image_app = image_app
    server_app = server_app
    job_app = job_app
    
apps = Apps()