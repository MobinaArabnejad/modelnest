# Initial threat model

## Assets

- User credentials and API keys
- Private model files and datasets
- Model metadata and inference results
- Host resources used by inference workers

## Trust boundaries

1. Anonymous client to API
2. One authenticated user to another user
3. API process to uploaded files and models
4. API process to remote URLs
5. API process to inference workers

## Security requirements

- Enforce authorization server-side for every model and dataset operation.
- Store secrets outside the repository and redact them from logs.
- Canonicalize and constrain all filesystem paths.
- Use safe model formats by default and isolate inference workers.
- Apply size, time, and concurrency limits to uploads and inference.
- Validate remote-import URLs and block loopback, link-local, and private destinations.

This document will be updated as features are implemented.
