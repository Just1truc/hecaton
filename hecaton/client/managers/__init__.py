from __future__ import annotations

from hecaton.client.managers.image import ImageManager as ImageManager
from hecaton.client.managers.image import image_app as image_app
from hecaton.client.managers.job import JobManager as JobManager
from hecaton.client.managers.job import job_app as job_app
from hecaton.client.managers.server import ServerManager as ServerManager
from hecaton.client.managers.server import server_app as server_app
from hecaton.client.managers.user import user_app as user_app
from hecaton.client.managers.worker import worker_app as worker_app

__all__ = [
    "ImageManager",
    "image_app",
    "JobManager",
    "job_app",
    "ServerManager",
    "server_app",
    "user_app",
    "worker_app",
]


class Apps:
    image_app = image_app
    server_app = server_app
    job_app = job_app
    user_app = user_app
    worker_app = worker_app


apps = Apps()
