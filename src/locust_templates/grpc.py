"""gRPC Load Test Template.

Provides ``GrpcUser`` — a Locust user class for load-testing gRPC services
with channel management, stub caching, auth integration, and event firing.

Usage::

    from locust_templates.grpc import GrpcUser

    class MyGrpcUser(GrpcUser):
        @task
        def say_hello(self):
            stub = self._get_stub(GreeterStub)
            request = HelloRequest(name="World")
            self._call_rpc(stub.SayHello, request)

Requires: ``pip install locust-performance-kit[grpc]`` or ``pip install grpcio>=1.60.0``
"""

from __future__ import annotations

import contextlib
import time

from locust import User, between, task

from locust_templates.auth import create_authenticator

# ── Optional dependency guard ────────────────────────────────
try:
    import grpc
except ImportError:
    grpc = None  # type: ignore[assignment]


class GrpcUser(User):
    """Base user class for gRPC load testing.

    Manages a single gRPC channel per user instance. Subclasses
    override ``on_start`` to configure the target and stub, and
    add ``@task``-decorated methods that call ``_call_rpc``.
    """

    wait_time = between(1, 5)

    # Class-level defaults so __new__-created instances (used in tests) work
    _channel = None
    _stub_cache: dict[str, object] = {}

    # Auth configuration (same pattern as APIUser)
    auth_provider: str = "env"
    auth_kwargs: dict = {}

    def __init__(self, environment):
        super().__init__(environment)
        self._channel = None
        self._stub_cache: dict[str, object] = {}
        self._authenticator = None

    def on_start(self):
        """Called when a simulated user starts.

        Sets up authentication so that gRPC calls carry auth metadata.
        """
        self._setup_auth()

    def _setup_auth(self):
        """Initialize the authenticator (graceful fallback on failure)."""
        try:
            self._authenticator = create_authenticator(
                self.auth_provider, **self.auth_kwargs
            )
            self._authenticator.authenticate()
        except Exception:
            self._authenticator = None

    def _get_channel(self, target, secure=False, credentials=None):
        """Create (or return the cached) gRPC channel to *target*.

        Args:
            target: ``host:port`` string.
            secure: If True, use ``grpc.secure_channel``.
            credentials: Optional ``grpc.ChannelCredentials`` (ignored when
                *secure* is False).

        Returns:
            ``grpc.Channel`` (or a mock-compatible object).
        """
        if self._channel is not None:
            return self._channel

        if grpc is None:
            raise ImportError(
                "gRPC support requires extra dependencies.\n"
                "  pip install locust-performance-kit[grpc]\n"
                "or:\n  pip install grpcio>=1.60.0"
            )

        if secure:
            creds = credentials or grpc.composite_channel_credentials(
                grpc.local_channel_credentials()
            )
            self._channel = grpc.secure_channel(target, creds)
        else:
            self._channel = grpc.insecure_channel(target)

        return self._channel

    def _get_stub(self, stub_class):
        """Return a stub instance for the current channel.

        The stub is cached so that repeated calls return the same instance.

        Args:
            stub_class: The gRPC stub class (e.g. ``GreeterStub``).

        Returns:
            An instance of *stub_class* bound to the cached channel.
        """
        stub_name = getattr(stub_class, "__name__", repr(stub_class))
        if stub_name not in self._stub_cache:
            if self._channel is None:
                raise RuntimeError(
                    "Channel not created. Call _get_channel(target) first."
                )
            self._stub_cache[stub_name] = stub_class(self._channel)
        return self._stub_cache[stub_name]

    def _call_rpc(self, stub_method, request, timeout=10):
        """Execute a unary-unary RPC and fire ``events.request``.

        Fires a Locust event with ``request_type="grpc"`` so metrics
        appear grouped in the Locust web UI / reports.

        Args:
            stub_method: Bound method of a gRPC stub (e.g. ``stub.SayHello``).
            request: The protobuf request message.
            timeout: Deadline in seconds (default 10).

        Returns:
            The protobuf response message, or ``None`` on failure.
        """
        from locust import events

        start_time = time.perf_counter()
        response = None
        exception = None
        try:
            metadata = self._get_auth_metadata()
            response = stub_method(request, timeout=timeout, metadata=metadata)
        except Exception as exc:
            exception = exc

        total_time = (time.perf_counter() - start_time) * 1000  # ms
        events.request.fire(
            request_type="grpc",
            name=stub_method.__name__,
            response_time=total_time,
            response_length=0,
            exception=exception,
        )

        if exception:
            raise exception
        return response

    def _get_auth_metadata(self):
        """Return auth metadata list for gRPC call context.

        Returns:
            List of ``(key, value)`` tuples, or an empty list.
        """
        if self._authenticator is None:
            return []
        headers = self._authenticator.get_headers()
        # Convert HTTP-style headers to gRPC metadata tuples
        return [(k.lower(), v) for k, v in headers.items()]

    def on_stop(self):
        """Called when a simulated user stops.

        Closes the gRPC channel gracefully.
        """
        if self._channel is not None:
            with contextlib.suppress(Exception):
                self._channel.close()
            self._channel = None

    @task
    def grpc_ping(self):
        """Default no-op task so Locust sees at least one task.

        Subclasses should override this or add their own ``@task`` methods.
        """
        pass


__all__ = ["GrpcUser"]
