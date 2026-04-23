# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest  | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability in **{{cookiecutter.project_name}}**, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email [{{cookiecutter.email}}](mailto:{{cookiecutter.email}}) with:

1. A description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

You should receive an acknowledgment within 48 hours. We will work with you to understand and address the issue before any public disclosure.

## Security Best Practices

This project follows these security practices:

- Dependencies are regularly audited via `deptry` and Dependabot
- Pre-commit hooks detect private keys and debug statements
- All code is linted with `ruff` including `flake8-bandit` security rules
- Type checking via `mypy` in strict mode reduces runtime errors
