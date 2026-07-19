# Getting Started with Locust Performance Kit

## Prerequisites

- Python 3.9+
- pip
- Git

## Installation

```bash
git clone https://github.com/csaszarzoltan/locust-performance-kit.git
cd locust-performance-kit
pip install -r requirements.txt
```

## Your First Test

```bash
# Run the example API load test with web UI
locust -f examples/api_load_test.py

# Open http://localhost:8089 in your browser
# Configure: Host, Users, Spawn rate
```

## Headless Mode (CI/CD)

```bash
locust -f examples/api_load_test.py \
    --headless \
    --users 50 \
    --spawn-rate 5 \
    --run-time 2m \
    --host http://localhost:8080
```

## Configuration

Set environment variables or use a `.env` file:

```bash
# Environment variables
export LOCUST_HOST=https://api.example.com
export LOCUST_USERS=100
export LOCUST_SPAWN_RATE=10

# Or .env file
echo "LOCUST_HOST=https://api.example.com" > .env
echo "LOCUST_USERS=100" >> .env
```

## Using Templates Programmatically

```python
from locust_templates import APIUser, MetricsCollector, ThresholdChecker
from locust_templates.config import load_config

# Load configuration
config = load_config()

# Use in your Locust script
class MyUser(APIUser):
    host = config.host
    wait_time = between(1, 3)
```

## Next Steps

1. Customize the example scripts for your API
2. Set up CI/CD with GitHub Actions
3. Integrate monitoring (AppDynamics, Prometheus)
4. Define performance thresholds for your application
5. Use custom shapes for advanced load patterns
