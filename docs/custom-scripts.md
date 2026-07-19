# Writing Custom Locust Scripts

## Basic Structure

```python
from locust import HttpUser, task, between

class MyUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def my_task(self):
        self.client.get("/api/endpoint")
```

## Weighted Tasks

Use `@task(weight)` to control task frequency:

```python
@task(3)  # Executed 3x more often
def frequent_task(self):
    pass

@task(1)  # Executed less often
def rare_task(self):
    pass
```

## Using the Template Base Classes

Extend the provided templates for common patterns:

```python
from locust_templates import APIUser, MetricsCollector
from locust_templates.config import load_config

config = load_config()

class MyAPIUser(APIUser):
    host = config.host

    @task(5)
    def list_items(self):
        with self.client.get("/api/items", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Failed: {resp.status_code}")
```

## Custom Load Shapes

Use shapes for advanced load patterns:

```python
from locust import HttpUser, between, task
from locust_templates.shapes import StepLoadShape

# Step-load shape: increase users gradually
shape = StepLoadShape(step_duration=30, step_users=10, max_users=100)

class MyUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def my_task(self):
        self.client.get("/api/health")
```

## Metrics Collection

Collect custom metrics for analysis:

```python
from locust_templates.metrics import MetricsCollector

metrics = MetricsCollector()

class MyUser(HttpUser):
    @task
    def my_task(self):
        with self.client.get("/api/data") as resp:
            metrics.record_request(
                "GET /api/data",
                resp.elapsed.total_seconds() * 1000,
                resp.status_code,
                resp.status_code == 200,
            )
```

## Threshold Checking

Validate performance after test:

```python
from locust_templates.thresholds import ThresholdChecker

checker = ThresholdChecker(p95_threshold=500, p99_threshold=1000)
result = checker.check(p95=350, p99=800, error_rate=0.005)

if not result.passed:
    for failure in result.failures:
        print(f"FAIL: {failure}")
```

## Best Practices

- Keep tasks realistic (realistic wait times)
- Use `catch_response=True` for custom success/failure
- Add meaningful logging
- Test locally before CI/CD
- Use environment variables for configuration
- Collect metrics for post-test analysis
