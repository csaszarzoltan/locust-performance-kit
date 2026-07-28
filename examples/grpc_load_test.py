"""gRPC Load Test Example — Greeter Service.

Demonstrates how to load-test a gRPC Greeter service using the
``GrpcUser`` template with realistic task weighting, auth integration,
timeout handling, and proper lifecycle management.

Usage:
    locust -f examples/grpc_load_test.py --users 100 --spawn-rate 10 --run-time 5m

Requires: pip install locust-performance-kit[grpc]
"""

from __future__ import annotations

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

# ---------------------------------------------------------------------------
# Protobuf stub classes (inline placeholders for self-contained example)
# In a real project these come from protoc-generated files, e.g.:
#
#   from helloworld_pb2 import HelloRequest
#   from helloworld_pb2_grpc import GreeterStub
#
# The try/except below lets the example compile without the generated stubs
# so it can serve as a reference; replace with real imports in production.
# ---------------------------------------------------------------------------
try:
    from helloworld_pb2 import HelloRequest  # type: ignore[import-untyped]
    from helloworld_pb2_grpc import GreeterStub  # type: ignore[import-untyped]
except ImportError:

    class HelloRequest:  # type: ignore[no-redef]
        """Placeholder — replace with protoc-generated class."""

        def __init__(self, name: str = "") -> None:
            self.name = name

        def __repr__(self) -> str:
            return f"HelloRequest(name={self.name!r})"

    class GreeterStub:  # type: ignore[no-redef]
        """Placeholder — replace with protoc-generated stub."""

        def __init__(self, channel: object) -> None:
            self._channel = channel

        def SayHello(self, request: HelloRequest, timeout: int = 10) -> object:  # noqa: N802
            """Stub method — real implementation calls the gRPC service."""
            return None


class ExampleGrpcUser(GrpcUser):
    """Example gRPC user for load-testing a Greeter service.

    Configures a channel and stub in ``on_start``, runs two weighted
    tasks (``say_hello`` and ``say_hello_timeout``), and cleans up
    the channel in ``on_stop``.

    Run::

        locust -f examples/grpc_load_test.py --users 100 --spawn-rate 10 --run-time 5m
    """

    wait_time = between(1, 3)

    # Auth provider for gRPC metadata (optional — remove or override as needed)
    auth_provider = "env"
    auth_kwargs: dict = {}

    def on_start(self) -> None:
        """Connect to the gRPC server, set up auth, and cache the stub."""
        super().on_start()
        self._get_channel("localhost:50051")
        self.stub = self._get_stub(GreeterStub)

    @task(3)
    def say_hello(self) -> None:
        """Call SayHello with a standard request message.

        Weight: 3 — this is the most frequent operation.
        """
        request = HelloRequest(name="Load Tester")
        self._call_rpc(self.stub.SayHello, request, timeout=10)

    @task(1)
    def say_hello_timeout(self) -> None:
        """Call SayHello with a shorter deadline.

        Weight: 1 — demonstrates timeout configuration for latency-sensitive
        operations. Useful for testing SLA compliance.
        """
        request = HelloRequest(name="Quick Test")
        self._call_rpc(self.stub.SayHello, request, timeout=2)

    def on_stop(self) -> None:
        """Close the gRPC channel when the simulated user stops."""
        import contextlib

        if hasattr(self, "_channel") and self._channel is not None:
            with contextlib.suppress(Exception):
                self._channel.close()
            self._channel = None


if __name__ == "__main__":
    print("Run with: locust -f examples/grpc_load_test.py")
