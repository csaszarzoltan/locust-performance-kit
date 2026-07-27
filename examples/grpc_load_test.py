"""gRPC Load Test Example (TDD stub).

Placeholder for a production-ready Locust script demonstrating how to
use the GrpcUser template for gRPC service load testing.

Usage:
    locust -f examples/grpc_load_test.py --users 100 --spawn-rate 10 --run-time 5m

Requires: pip install locust-performance-kit[grpc]
"""

import sys
from pathlib import Path

# Ensure src is on the path for template imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import grpc  # noqa: F401
except ImportError:
    msg = (
        "gRPC support requires extra dependencies.\n"
        "  pip install locust-performance-kit[grpc]\n"
        "or:\n"
        "  pip install grpcio>=1.60.0"
    )
    print(msg)
    raise

from locust import between, task

from locust_templates.grpc import GrpcUser


class ExampleGrpcUser(GrpcUser):
    """Example gRPC user extending the base template.

    Implements a simple Greeter service load test.
    Override ``on_start`` to configure the target and stub.
    """

    wait_time = between(1, 3)

    @task
    def say_hello(self):
        """Sample RPC: call SayHello on the Greeter service."""
        raise NotImplementedError("Implement with real protobuf stubs")


if __name__ == "__main__":
    print("Run with: locust -f examples/grpc_load_test.py")
