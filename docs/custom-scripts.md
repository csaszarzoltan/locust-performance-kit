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

## Best Practices

- Keep tasks realistic (realistic wait times)
- Use `catch_response=True` for custom success/failure
- Add meaningful logging
- Test locally before CI/CD
