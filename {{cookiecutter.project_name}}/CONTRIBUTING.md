# Contributing to `{{cookiecutter.project_name}}`

Contributions are welcome, and they are greatly appreciated!

## Types of Contributions

### Report Bugs

Report bugs at https://github.com/{{cookiecutter.author_github_handle}}/{{cookiecutter.project_name}}/issues

If you are reporting a bug, please include:

- Your operating system name and version.
- Any details about your local setup that might be helpful in troubleshooting.
- Detailed steps to reproduce the bug.

### Fix Bugs

Look through the GitHub issues for bugs.
Anything tagged with "bug" and "help wanted" is open to whoever wants to implement a fix for it.

### Implement Features

Look through the GitHub issues for features.
Anything tagged with "enhancement" and "help wanted" is open to whoever wants to implement it.

### Write Documentation

{{cookiecutter.project_name}} could always use more documentation, whether as part of the official docs, in docstrings, or even on the web in blog posts, articles, and such.

## Get Started!

Ready to contribute? Here's how to set up `{{cookiecutter.project_name}}` for local development.

**Prerequisites:** `uv` and `git` installed.

1. Fork the `{{cookiecutter.project_name}}` repo on GitHub.

2. Clone your fork locally:

```bash
git clone git@github.com:YOUR_NAME/{{cookiecutter.project_name}}.git
cd {{cookiecutter.project_name}}
```

3. Install the environment and pre-commit hooks:

```bash
make install
```

4. Create a branch for local development:

```bash
git checkout -b name-of-your-bugfix-or-feature
```

5. Make your changes locally. Don't forget to add tests.

6. Run quality checks and tests:

```bash
make check
make test
```

7. Run tox for multi-version testing (optional):

```bash
tox
```

8. Commit your changes and push:

```bash
git add .
git commit -m "Your detailed description of your changes."
git push origin name-of-your-bugfix-or-feature
```

9. Submit a pull request through the GitHub website.

## Pull Request Guidelines

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated.
3. All quality checks must pass (`make check && make test`).
