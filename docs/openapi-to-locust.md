# OpenAPI-to-Locust Code Generation (v1.5.0)

Generate production-ready Locust load test scripts from OpenAPI 3.x or Swagger 2.0 specifications. The `locust-gen` CLI parses your API spec, extracts endpoints, parameters, request bodies, and authentication schemes, then emits a complete `locustfile.py` with weighted task methods and auth setup.

## Supported Spec Formats

| Format | Version | File Types |
|--------|---------|------------|
| OpenAPI | 3.x (3.0.x, 3.1.x) | `.yaml`, `.yml`, `.json` |
| Swagger | 2.0 | `.yaml`, `.yml`, `.json` |

The parser validates the spec version from the root `openapi` or `swagger` key and extracts endpoints, parameters, request bodies, response schemas, and security schemes.

## Quick Start

```bash
# Generate from an OpenAPI spec
locust-gen from-openapi openapi.yaml --output locustfile.py

# Run it
locust -f locustfile.py --host https://api.example.com --users 50 --spawn-rate 5
```

## CLI Reference

```
locust-gen from-openapi [OPTIONS] SPEC_FILE
```

| Flag | Default | Description |
|------|---------|-------------|
| `-o`, `--output` | `locustfile.py` | Output file path |
| `-u`, `--users` | `10` | Number of simulated users |
| `-r`, `--spawn-rate` | `1` | Users spawned per second |
| `-t`, `--runtime` | `5m` | Test runtime duration (e.g. `5m`, `30s`, `1h30m`) |
| `-p`, `--pattern` | `constant` | Load pattern: `constant`, `ramp-up`, or `spike` |
| `--base-url` | *from spec* | Override base URL for all requests |
| `--auth-provider` | `None` | Authentication provider name (env, oauth2, etc.) |
| `--dry-run` | `false` | Print generated script to stdout instead of writing a file |
| `-v`, `--verbose` | `false` | Enable verbose output (shows endpoint count, warnings) |
| `--no-comments` | `false` | Generate script without inline docstrings |

## Examples

### Basic generation

```bash
locust-gen from-openapi spec.yaml
# Writes locustfile.py with all endpoints as @task methods
```

### Override host and users

```bash
locust-gen from-openapi spec.yaml \
    --base-url https://staging.api.example.com \
    --users 50 --spawn-rate 5
```

### Ramp-up load pattern

```bash
locust-gen from-openapi spec.yaml \
    --pattern ramp-up \
    --users 100 --spawn-rate 10 --runtime 10m
# Appends a RampUpLoadShape class to the generated script
```

### Dry-run (preview)

```bash
locust-gen from-openapi spec.yaml --dry-run
# Prints the generated script to stdout
# Useful for piping or reviewing before committing
```

### Verbose mode

```bash
locust-gen from-openapi spec.yaml -v --output locustfile.py
# Generated locustfile.py
#   Endpoints processed: 12
#   Auth schemes mapped: 2
```

## Generated Script Structure

The generated locustfile follows this structure:

```python
from locust import HttpUser, task, between
import os


class PetstoreUser(HttpUser):                    # Class name derived from spec title
    """Locust user class generated from Petstore 1.0.0."""
    wait_time = between(1.0, 3.0)                # Default: 1-3s between requests
    host = "https://petstore.example.com/v1"     # From spec servers[] or --base-url

    def on_start(self):                          # Auth setup (only if spec has security schemes)
        self.headers = {
            "Authorization": f"Bearer {os.environ.get('BEARERAUTH_TOKEN', ...)}"
        }
        return self.headers

    @task(3)                                     # Weight: GET=3, POST=2, PUT/PATCH/DELETE=1
    def list_pets(self):
        """List all pets"""                      # Docstring from operation summary
        resp = self.client.get("/pets", params={"limit": None, "status": None})

    @task(2)
    def create_pet(self):
        """Create a pet"""
        resp = self.client.post("/pets", json={'name': '<string>', 'tag': '<string>'})
```

### What gets generated per endpoint

| Spec Element | Generated Code |
|--------------|----------------|
| `operationId` | Method name (camelCase → snake_case) |
| `summary` | Docstring on the method |
| HTTP method + path | `self.client.get("/path")` call |
| `parameters` (path) | f-string interpolation in URL |
| `parameters` (query) | `params={...}` dict |
| `requestBody` (JSON) | `json={...}` with example or schema-derived placeholder |
| `security` | `on_start()` method with env-var-based token injection |

### Task weights

Default task weights follow real-world API usage patterns:

| HTTP Method | Weight | Rationale |
|-------------|--------|-----------|
| GET | 3 | Read-heavy workloads |
| POST | 2 | Create operations |
| PUT | 1 | Update operations |
| PATCH | 1 | Partial updates |
| DELETE | 1 | Removal operations |

## Load Patterns

Append a load pattern to the generated script with `--pattern`:

| Pattern | Flag | Behavior |
|---------|------|----------|
| `constant` | `--pattern constant` | Steady user count for the duration |
| `ramp-up` | `--pattern ramp-up` | Ramp to target users, hold, then ramp down |
| `spike` | `--pattern spike` | Baseline users with periodic spike bursts |

When a non-default pattern is selected, the generated script appends a `LoadTestShape` subclass at the end:

```python
# ── Load Pattern ──
from locust_templates.shapes import RampUpLoadShape

class TestShape(RampUpLoadShape):
    pass

environment.runner.shape_class = TestShape(
    target_users=50,
    ramp_up_duration=120.0,
    hold_duration=180.0,
    ramp_down_duration=60.0,
    spawn_rate=5,
)
```

## Authentication Handling

The parser extracts security schemes from the spec and generates `on_start()` code that reads tokens from environment variables.

| Security Type | Generated Env Vars | Example |
|---------------|--------------------|---------|
| `http` (bearer) | `<SCHEME_NAME>_TOKEN`, fallback `API_TOKEN` | `BEARERAUTH_TOKEN=eyJ...` |
| `apiKey` (header) | `<SCHEME_NAME>_KEY`, fallback `API_KEY` | `APIKEYAUTH_KEY=sk-...` |

### Setting tokens before a run

```bash
export BEARERAUTH_TOKEN=eyJhbGciOiJIUzI1NiIs...
export APIKEYAUTH_KEY=sk-live-abc123

locust -f locustfile.py --host https://api.example.com --users 20
```

## Python API

For programmatic use without the CLI:

```python
from locust_templates.openapi_parser import parse_spec
from locust_templates.locust_generator import GenerationConfig, generate_locust_script

# Parse the spec
spec = parse_spec("petstore.yaml")
print(f"Found {len(spec.endpoints)} endpoints")
print(f"Base URL: {spec.base_url}")

# Generate the script
config = GenerationConfig(
    base_url="https://staging.api.example.com",
    include_comments=True,
    auth_provider="env",
)
result = generate_locust_script(spec, config)

print(f"Processed: {result.endpoints_processed}")
print(f"Auth schemes: {result.auth_schemes_mapped}")
print(f"Warnings: {result.warnings}")

# Write to file
with open("locustfile.py", "w") as f:
    f.write(result.source_code)
```

## Parser Data Model

The parser returns structured data for each endpoint:

```python
spec = parse_spec("api.yaml")

for ep in spec.endpoints:
    print(f"{ep.method.upper()} {ep.path}")
    print(f"  operation_id: {ep.operation_id}")
    print(f"  summary: {ep.summary}")
    print(f"  path_params: {[(p.name, p.schema_type) for p in ep.path_params]}")
    print(f"  query_params: {[(p.name, p.schema_type) for p in ep.query_params]}")
    if ep.request_body:
        print(f"  body: {ep.request_body.content_type}")
    print(f"  security: {[s.scheme_name for s in ep.security]}")
```

Key data classes:

| Class | Description |
|-------|-------------|
| `OpenAPISpec` | Top-level: title, version, base_url, endpoints, security_schemes |
| `EndpointInfo` | Per-endpoint: path, method, params, body, security, tags |
| `ParamInfo` | Parameter metadata: name, location, type, required, enum |
| `RequestBodyInfo` | Body schema: content_type, schema dict, example |
| `SecurityRequirement` | Scheme reference: name, type, location |

## Limitations

- **External `$ref`** — Only internal JSON Pointer references (`#/...`) are resolved. External file references are not supported.
- **Content types** — Only `application/json` request bodies are generated. Other content types (form-data, XML) are skipped with a warning.
- **Path parameters** — Interpolated as f-strings but not given default values. You must set them in the generated code before running.
- **Load patterns** — `ConstantLoadShape`, `RampUpLoadShape`, and `SpikeLoadShape` are currently TDD stubs that will be completed in a future release.

## Example: Petstore

The repository ships with a [petstore.yaml](../petstore.yaml) sample spec. Generate and run it:

```bash
locust-gen from-openapi petstore.yaml --dry-run --users 10
locust-gen from-openapi petstore.yaml --output examples/petstore_locustfile.py
```

See also the generated output in [examples/openapi_generated_locustfile.py](../examples/openapi_generated_locustfile.py).
