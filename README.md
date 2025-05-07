# VectorBench: OpenTelemetry Tracing Bug Bash

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new?hide_repo_select=true&ref=main&repo=979694699)

## Assessment Overview

This coding assessment tests your ability to debug and fix OpenTelemetry instrumentation issues in a Python web application.

**Time Limit**: We recommend spending no more than 60 minutes on this assessment.

**Objective**: Fix the broken OpenTelemetry tracing pipeline in the FastAPI application to make all the tests pass.

## Getting Started

1. Click the "Open in GitHub Codespaces" button above to start the assessment.
2. Once the Codespace loads, explore the code in the `tracing_bug_bash` directory.
3. Run the tests with `pytest -q` to see what's failing.
4. Fix the issues in the `tracing_bug_bash/app.py` file.
5. Once all tests pass, submit your solution with `python submit.py`.

## The Challenge

The tracing application has three key bugs:

1. **Spans Collection**: Spans are not being properly collected and exported.
2. **Error Endpoint**: The `/error` endpoint always returns a 500 error, but should return a 200 OK response.
3. **Context Propagation**: The trace context is not properly propagated to downstream services.

Each bug is documented in the code with comments indicating what's wrong and hints for how to fix it.

## Testing Your Solution

The tests in `tests/test_app.py` verify that each of the three bugs has been fixed:

- `test_spans_collection`: Verifies that spans are being properly collected.
- `test_error_endpoint`: Verifies that the error endpoint returns a 200 response.
- `test_context_propagation`: Verifies that trace context is properly propagated.

Run the tests with:

```bash
pytest -q
```

## Submission

When you're ready to submit your solution:

1. Make sure all tests are passing.
2. Run the submission script:

```bash
python submit.py
```

The script will:
- Verify that all tests pass
- Create a zip of your workspace
- Submit your solution to VectorBench
- Record your completion time

## What We're Looking For

- **Understanding of OpenTelemetry concepts**: Can you identify and fix issues with span collection, context propagation, and instrumentation?
- **Debugging skills**: Can you systematically identify and resolve the issues?
- **Attention to detail**: Did you fix all the bugs completely?

Good luck!

---

## Data Collection Notice

This assessment collects:
- Your code changes
- Test results
- Time spent on the assessment

For more details, see [CONSENT.md](./CONSENT.md). 