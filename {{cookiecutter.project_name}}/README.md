# {{cookiecutter.project_name}}

[![Release](https://img.shields.io/github/v/release/{{cookiecutter.author_github_handle}}/{{cookiecutter.project_name}})](https://img.shields.io/github/v/release/{{cookiecutter.author_github_handle}}/{{cookiecutter.project_name}})
[![Build status](https://img.shields.io/github/actions/workflow/status/{{cookiecutter.author_github_handle}}/{{cookiecutter.project_name}}/main.yml?branch=main)](https://github.com/{{cookiecutter.author_github_handle}}/{{cookiecutter.project_name}}/actions/workflows/main.yml?query=branch%3Amain)
{%- if cookiecutter.codecov == "y" %}
[![codecov](https://codecov.io/gh/{{cookiecutter.author_github_handle}}/{{cookiecutter.project_name}}/branch/main/graph/badge.svg)](https://codecov.io/gh/{{cookiecutter.author_github_handle}}/{{cookiecutter.project_name}})
{%- endif %}
[![Commit activity](https://img.shields.io/github/commit-activity/m/{{cookiecutter.author_github_handle}}/{{cookiecutter.project_name}})](https://img.shields.io/github/commit-activity/m/{{cookiecutter.author_github_handle}}/{{cookiecutter.project_name}})
[![License](https://img.shields.io/github/license/{{cookiecutter.author_github_handle}}/{{cookiecutter.project_name}})](https://img.shields.io/github/license/{{cookiecutter.author_github_handle}}/{{cookiecutter.project_name}})

{{cookiecutter.project_description}}

- **Github repository**: <https://github.com/{{cookiecutter.author_github_handle}}/{{cookiecutter.project_name}}/>
{%- if cookiecutter.docs_tool == "mkdocs" %}
- **Documentation**: <https://{{cookiecutter.author_github_handle}}.github.io/{{cookiecutter.project_name}}/>
{%- endif %}

## Getting started

### 1. Create a New Repository

First, create a repository on GitHub with the same name as this project, and then run the following commands:

{% raw %}```bash
git init -b main
git add .
git commit -m "init commit"
git remote add origin git@github.com:YOUR_HANDLE/YOUR_PROJECT.git
git push -u origin main
```{% endraw %}

### 2. Set Up Your Development Environment

Install the environment and the pre-commit hooks with:

{% raw %}```bash
make install
```{% endraw %}

This will also generate your `uv.lock` file.

### 3. Run the pre-commit hooks

{% raw %}```bash
uv run pre-commit run -a
```{% endraw %}

### 4. Commit the changes

{% raw %}```bash
git add .
git commit -m 'Fix formatting issues'
git push origin main
```{% endraw %}

You are now ready to start development on your project!
The CI/CD pipeline will be triggered when you open a pull request, merge to main, or when you create a new release.

### 5. Set up branch protection (recommended)

Go to **Settings > Branches > Add rule** for `main`:

- Require pull request reviews before merging
- Require status checks to pass (select `quality` and `tests-and-type-check`)
- Require branches to be up to date before merging

{%- if cookiecutter.publish_to_pypi == "y" %}

## Releasing a new version

- Create an API Token on [PyPI](https://pypi.org/).
- Add the API Token to your projects secrets with the name `PYPI_TOKEN` by visiting [this page](https://github.com/{{cookiecutter.author_github_handle}}/{{cookiecutter.project_name}}/settings/secrets/actions/new).
- Create a [new release](https://github.com/{{cookiecutter.author_github_handle}}/{{cookiecutter.project_name}}/releases/new) on Github.
- Create a new tag in the form `*.*.*`.
{%- endif %}

---

Repository initiated with [cookie-claude](https://github.com/{{cookiecutter.author_github_handle}}/cookie-claude).
