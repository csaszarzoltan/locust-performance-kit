import json
import subprocess
import sys


def test_pure_module_import_does_not_load_locust_or_gevent():
    code = "import sys; import locust_templates.decision_artifact; print(json.dumps({'locust': 'locust' in sys.modules, 'gevent': 'gevent' in sys.modules}))"
    result = subprocess.run([sys.executable, "-c", "import json;" + code], check=True, text=True, capture_output=True)
    assert json.loads(result.stdout) == {"locust": False, "gevent": False}


def test_public_api_remains_lazy_and_compatible():
    code = "import sys, locust_templates as p; before='locust' in sys.modules; cls=p.APIUser; after='locust' in sys.modules; print(before, after, cls.__name__)"
    result = subprocess.run([sys.executable, "-c", code], check=True, text=True, capture_output=True)
    assert result.stdout.strip() == "False True APIUser"
