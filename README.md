# Locust Performance Kit

Production-ready Locust load testing templates, CI/CD pipelines, and monitoring integrations for enterprise-grade performance testing.

Built by a performance engineer with 6+ years at a major Swiss bank. These templates have been battle-tested on real banking applications handling millions of transactions.

## What's Inside

### Core Templates
- **`examples/api_load_test.py`** - REST API load testing with custom metrics
- **`src/locust_templates/stress.py`** - Stress testing with ramp-up patterns
- **`src/locust_templates/spike.py`** - Spike testing for sudden load bursts
- **`src/locust_templates/soak.py`** - Endurance testing for stability
- **`src/locust_templates/web_ui.py`** - Browser-based user journey testing

### Utility Modules
- **`src/locust_templates/metrics.py`** - Thread-safe metrics collection with percentile calculations
- **`src/locust_templates/thresholds.py`** - Performance threshold validation (p95, p99, error rate)
- **`src/locust_templates/shapes.py`** - Custom Locust shapes (StepLoadShape, SpikeLoadShape)
- **`src/locust_templates/config.py`** - Environment-based configuration with .env support
- **`src/locust_templates/runner.py`** - CLI command builder for CI/CD pipelines

### CI/CD Integration
- **`.github/workflows/performance-ci.yml`** - GitHub Actions pipeline for automated performance gates
- Pre-configured thresholds and pass/fail criteria
- Automatic reporting to Slack/Teams

### Monitoring & Observability
- **`docs/appdynamics-integration.md`** - AppDynamics custom metrics
- **`docs/prometheus-grafana-setup.md`** - Real-time metrics dashboard
- **`docs/wily-integration.md`** - CA Wily Introscope integration

### Utilities
- **`docs/test-data-generation.md`** - Realistic test data patterns
- **`docs/result-analysis.md`** - Automated report generation

## Quick Start

```bash
# Clone the repo
git clone https://github.com/csaszarzoltan/locust-performance-kit.git
cd locust-performance-kit

# Install dependencies
pip install -r requirements.txt

# Run a basic load test
locust -f examples/api_load_test.py --users 100 --spawn-rate 10 --run-time 5m
```

## Configuration

Configuration is managed via environment variables with sensible defaults:

```bash
# Set your target host
export LOCUST_HOST=https://api.example.com

# Configure load profile
export LOCUST_USERS=100
export LOCUST_SPAWN_RATE=10
export LOCUST_RUN_TIME=5m

# Set performance thresholds
export LOCUST_P95_THRESHOLD=500
export LOCUST_P99_THRESHOLD=1000
export LOCUST_ERROR_RATE_THRESHOLD=0.01
```

Or use a `.env` file:

```bash
LOCUST_HOST=https://api.example.com
LOCUST_USERS=100
LOCUST_AUTH_TOKEN=your_token_here
```

## Using Custom Shapes

```python
from locust_templates.shapes import StepLoadShape, SpikeLoadShape

# Step-load: increase users by 10 every 30 seconds up to 100
shape = StepLoadShape(step_duration=30, step_users=10, max_users=100)

# Spike: alternate between 10 baseline and 100 spike users
shape = SpikeLoadShape(
    baseline_users=10,
    spike_users=100,
    baseline_duration=30,
    spike_duration=5,
    recovery_duration=30,
)
```

## Programmatic Command Building

```python
from locust_templates.runner import build_locust_command

cmd = build_locust_command(
    script="examples/api_load_test.py",
    headless=True,
    users=100,
    spawn_rate=10,
    host="https://api.example.com",
    run_time="5m",
)
# Returns: "locust -f examples/api_load_test.py --headless --users 100 --spawn-rate 10 ..."
```

## Example Output

```bash
# Run with web UI
locust -f examples/api_load_test.py

# Open http://localhost:8089
# Configure users, spawn rate, and host
```

## Tech Stack

- **Load Testing:** Locust, k6, JMeter (migrations)
- **CI/CD:** GitHub Actions, GitLab CI
- **APM:** AppDynamics, Dynatrace, CA Wily, Prometheus + Grafana
- **Languages:** Python, Bash, YAML
- **Cloud:** AWS, Azure, GCP load testing patterns

## Performance Thresholds (Typical)

```yaml
# Example thresholds for banking applications
p95_latency: 500ms
p99_latency: 1000ms
error_rate: 0.1%
throughput: 1000 RPS
```

## Use Cases

- **Regression testing** - Verify performance after deployments
- **Capacity planning** - Find breaking points before production
- **SLA validation** - Ensure contractual performance metrics
- **Bottleneck detection** - Identify slow endpoints early
- **Baseline establishment** - Create performance benchmarks

## Project Structure

```
src/locust_templates/     - Core template modules
tests/                    - Test suite (unit, integration, visual)
docs/                     - Documentation
examples/                 - Runnable example scripts
.github/workflows/        - CI/CD pipeline configuration
```

## Documentation

- [Getting Started Guide](docs/getting-started.md)
- [Writing Custom Locust Scripts](docs/custom-scripts.md)

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - feel free to use these templates in your projects.

## Author

**Zoltan Csaszar**
- Upwork: [Profile](https://www.upwork.com/freelancers/~010b8149572fd46b3d)
- GitHub: [@csaszarzoltan](https://github.com/csaszarzoltan)
- Location: Zurich, Switzerland

## Contact

For custom performance testing solutions or consulting:
- Open an issue on GitHub
- Reach out on Upwork for project-based work

---

Star this repo if you find it useful! It helps others discover it.
