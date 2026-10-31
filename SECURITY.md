# Security policy

## Supported version

Security fixes target the current `main` branch.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for this repository if available. Otherwise, open a minimal issue asking the maintainer for a private contact channel; do not include exploit details, credentials, or personal data in a public issue.

Include the affected commit/version, reproduction prerequisites, impact, and a safe proof of concept. Expect acknowledgement within seven days.

## Local safety model

CHRONOS binds to `127.0.0.1` and is not designed for public internet exposure. It has no authentication or authorization layer. Do not change the bind address to `0.0.0.0` or place it behind a public proxy without adding and reviewing appropriate security controls.

The raw-data downloader accepts only the versioned HTTPS URLs in the local manifest by default and verifies exact byte sizes and MD5 values. MD5 here is an upstream integrity identifier, not a modern authenticity signature; review manifest changes in pull requests.

Never commit tokens, `.env` files, raw datasets, user recordings, or machine-specific paths.
