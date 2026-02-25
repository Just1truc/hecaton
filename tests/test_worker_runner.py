import sys
import traceback
sys.path.append('.')

from hecaton.server.worker import check_docker_image

print("Testing normal image:")
try:
    desc = check_docker_image("library/alpine:latest")
    print("Normal image success:", desc)
except Exception as e:
    print("Normal image failed:", e)
    traceback.print_exc()

print("\nTesting large image limit (Fake):")
try:
    import requests
    original_get = requests.get
    
    def fake_get(url, *args, **kwargs):
        class FakeResponse:
            def json(self):
                if "tags" in url:
                    return {"full_size": 6 * 1024 * 1024 * 1024} # 6GB
                return {"description": "fake"}
        return FakeResponse()
        
    requests.get = fake_get
    check_docker_image("library/hugeimage:latest")
    print("Large image did not raise exception! ERROR!")
except Exception as e:
    print("Large image success (raised exception):", e)
finally:
    requests.get = original_get
