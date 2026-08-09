# Baseline Decisions

Run Detail exposes measured status, quality, findings, source-linked rules, confidence, next checks, and a SHA-256 decision identity. PASS runs may be promoted to one ACTIVE baseline per environment. Replacements retain the previous record as SUPERSEDED. ADVISORY requires an explicit override and longer reason; FAIL, ERROR, sample, or invalid evidence cannot be promoted.

The canonical JSON schema is `performance-decision/v1`. Its hash covers sorted compact UTF-8 JSON excluding the `hash` object and generated timestamp. Arrays use deterministic ordering, non-finite values are rejected, and host absolute paths are omitted. Markdown contains status, grade, hash, the top 20 severity-ordered findings, and omitted count.

```bash
locust-kit analyze --csv results --baseline baseline --slo p95=500 \
  --decision-json decision.json --decision-markdown summary.md
```

Exit codes remain 0 for successful/advisory analysis, 1 for input or output errors, and 2 for measured SLO violations. Requested decision files are written before returning 2.
