import sys
import traceback
sys.path.append('.')

from hecaton.gpu.docker_manager import DockerManager

class FakeWebClient:
    def get_online_images(self):
        # We simulate that the server asks us to pull this image
        return [("id1", "alpine")]

class FakeDockerAPI:
    def pull(self, image, stream, decode):
        print(f"Fake pull called for {image}")
        yield {'status': 'Pulling fs layer', 'id': 'layer1', 'progressDetail': {}}
        yield {'status': 'Downloading', 'id': 'layer1', 'progressDetail': {'current': 100, 'total': 1500}}
        yield {'status': 'Download complete', 'id': 'layer1', 'progressDetail': {'current': 1500, 'total': 1500}}

class FakeDockerImages:
    class FakeImageContext:
        tags = []
    def list(self):
        return [self.FakeImageContext()]
    def pull(self, image):
        pass

class FakeDockerClient:
    api = FakeDockerAPI()
    images = FakeDockerImages()

# Patch docker from_env to return FakeDockerClient
import docker
import hecaton.gpu.docker_manager

original_from_env = docker.from_env
docker.from_env = lambda: FakeDockerClient()

try:
    dm = hecaton.gpu.docker_manager.DockerManager(FakeWebClient())
    print("DockerManager initialization and small pull worked successfully.")
except Exception as e:
    print("DockerManager initialization failed:", e)
    traceback.print_exc()
finally:
    docker.from_env = original_from_env

print("\nTesting large layer pull (Fake):")
class FakeLargePullAPI:
    def pull(self, image, stream, decode):
        yield {'status': 'Downloading', 'id': 'layer1', 'progressDetail': {'current': 100, 'total': 3 * 1024 * 1024 * 1024}}

FakeDockerClient.api = FakeLargePullAPI()
docker.from_env = lambda: FakeDockerClient()

try:
    dm = hecaton.gpu.docker_manager.DockerManager(FakeWebClient())
    print("Large layer did not raise exception! ERROR!")
except Exception as e:
    print("Large layer success (raised exception):", e)
finally:
    docker.from_env = original_from_env
