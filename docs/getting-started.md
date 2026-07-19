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
locust -f examples/api_load_test.py --users 10 --spawn-rate 2 --run-time 1m
```

## Next Steps

1. Customize the example scripts for your API
2. Set up CI/CD with GitHub Actions
3. Integrate monitoring (AppDynamics, Prometheus)
4. Define performance thresholds for your application
