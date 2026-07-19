# 🚀 Locust Performance Kit

Production-ready Locust load testing templates, CI/CD pipelines, and monitoring integrations for enterprise-grade performance testing.

Built by a performance engineer with 6+ years at a major Swiss bank. These templates have been battle-tested on real banking applications handling millions of transactions.

## 📦 What's Inside

### Core Templates
- **`examples/api_load_test.py`** - REST API load testing with custom metrics
- **examples/web_ui_test.py** - Browser-based user journey testing
- **examples/stress_test.py`** - Stress testing with ramp-up patterns
- **examples/spike_test.py`** - Spike testing for sudden load bursts
- **examples/soak_test.py`** - Endurance testing for stability

### CI/CD Integration
- **`.github/workflows/performance-ci.yml`** - GitHub Actions pipeline for automated performance gates
- Pre-configured thresholds and pass/fail criteria
- Automatic reporting to Slack/Teams

### Monitoring & Observability
- **`docs/appdynamics-integration.md`** - AppDynamics custom metrics
- **docs/prometheus-grafana-setup.md`** - Real-time metrics dashboard
- **docs/wily-integration.md`** - CA Wily Introscope integration

### Utilities
- **`docs/test-data-generation.md`** - Realistic test data patterns
- **`docs/result-analysis.md`** - Automated report generation

## 🚀 Quick Start

```bash
# Clone the repo
git clone https://github.com/csaszarzoltan/locust-performance-kit.git
cd locust-performance-kit

# Install dependencies
pip install -r requirements.txt

# Run a basic load test
locust -f examples/api_load_test.py --users 100 --spawn-rate 10 --run-time 5m
```

## 📊 Example Output

```bash
# Run with web UI
locust -f examples/api_load_test.py

# Open http://localhost:8089
# Configure users, spawn rate, and host
```

## 🛠️ Tech Stack

- **Load Testing:** Locust, k6, JMeter (migrations)
- **CI/CD:** GitHub Actions, GitLab CI
- **APM:** AppDynamics, Dynatrace, CA Wily, Prometheus + Grafana
- **Languages:** Python, Bash, YAML
- **Cloud:** AWS, Azure, GCP load testing patterns

## 📈 Performance Thresholds (Typical)

```yaml
# Example thresholds for banking applications
p95_latency: 500ms
p99_latency: 1000ms
error_rate: 0.1%
throughput: 1000 RPS
```

## 🎯 Use Cases

- **Regression testing** - Verify performance after deployments
- **Capacity planning** - Find breaking points before production
- **SLA validation** - Ensure contractual performance metrics
- **Bottleneck detection** - Identify slow endpoints early
- **Baseline establishment** - Create performance benchmarks

## 📚 Documentation

- [Getting Started Guide](docs/getting-started.md)
- [Writing Custom Locust Scripts](docs/custom-scripts.md)
- [CI/CD Setup](docs/ci-cd-setup.md)
- [Monitoring Integration](docs/monitoring.md)

## 🤝 Contributing

 Contributions are welcome! Please feel free to submit issues or pull requests.

## 📄 License

 MIT License - feel free to use these templates in your projects.

## 👤 Author

**Zoltan Csaszar**
- Upwork: [Profile](https://www.upwork.com/freelancers/~010b8149572fd46b3d)
- GitHub: [@csaszarzoltan](https://github.com/csaszarzoltan)
- Location: Zurich, Switzerland

## 📞 Contact

For custom performance testing solutions or consulting:
- Open an issue on GitHub
- Reach out on Upwork for project-based work

---

⭐ **Star this repo if you find it useful!** It helps others discover it.
