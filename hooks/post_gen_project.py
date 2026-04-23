"""Post-generation hook: removes unused files and initializes the project."""
from __future__ import annotations

import os
import shutil
import subprocess

PROJECT_DIRECTORY = os.path.realpath(os.path.curdir)


def remove_file(filepath: str) -> None:
    target = os.path.join(PROJECT_DIRECTORY, filepath)
    if os.path.exists(target):
        os.remove(target)


def remove_dir(filepath: str) -> None:
    target = os.path.join(PROJECT_DIRECTORY, filepath)
    if os.path.isdir(target):
        shutil.rmtree(target)


def move_file(filepath: str, target: str) -> None:
    os.rename(
        os.path.join(PROJECT_DIRECTORY, filepath),
        os.path.join(PROJECT_DIRECTORY, target),
    )


def move_dir(src: str, target: str) -> None:
    shutil.move(
        os.path.join(PROJECT_DIRECTORY, src),
        os.path.join(PROJECT_DIRECTORY, target),
    )


if __name__ == "__main__":
    # --- GitHub Actions ---
    if "{{cookiecutter.include_github_actions}}" != "y":
        remove_dir(".github")
    else:
        if "{{cookiecutter.docs_tool}}" != "mkdocs" and "{{cookiecutter.publish_to_pypi}}" == "n":
            remove_file(".github/workflows/on-release-main.yml")

    # --- Documentation ---
    if "{{cookiecutter.docs_tool}}" == "mkdocs":
        pass  # keep mkdocs.yml and docs/
    else:
        remove_dir("docs")
        remove_file("mkdocs.yml")

    # --- Dockerfile ---
    if "{{cookiecutter.dockerfile}}" != "y":
        remove_file("Dockerfile")

    # --- Codecov ---
    if "{{cookiecutter.codecov}}" != "y":
        remove_file("codecov.yaml")
        if "{{cookiecutter.include_github_actions}}" == "y":
            remove_file(".github/workflows/validate-codecov-config.yml")

    # --- Devcontainer ---
    if "{{cookiecutter.devcontainer}}" != "y":
        remove_dir(".devcontainer")

    # --- License ---
    license_map = {
        "MIT license": "LICENSE_MIT",
        "BSD license": "LICENSE_BSD",
        "ISC license": "LICENSE_ISC",
        "Apache Software License 2.0": "LICENSE_APACHE",
        "GNU General Public License v3": "LICENSE_GPL",
    }
    chosen = "{{cookiecutter.open_source_license}}"
    all_licenses = ["LICENSE_MIT", "LICENSE_BSD", "LICENSE_ISC", "LICENSE_APACHE", "LICENSE_GPL"]

    if chosen in license_map:
        move_file(license_map[chosen], "LICENSE")
        for lic in all_licenses:
            if lic != license_map[chosen]:
                remove_file(lic)
    else:
        # Not open source
        for lic in all_licenses:
            remove_file(lic)

    # --- Layout (src vs flat) ---
    if "{{cookiecutter.layout}}" == "src":
        if os.path.isdir("src"):
            remove_dir("src")
        move_dir(
            "{{cookiecutter.project_slug}}",
            os.path.join("src", "{{cookiecutter.project_slug}}"),
        )

    # --- Initialize git repo ---
    try:
        subprocess.run(["git", "init", "-b", "main"], check=True, capture_output=True)
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Note: git init skipped (git not available or failed)")

    # --- Run uv sync if available ---
    try:
        subprocess.run(["uv", "sync"], check=True, capture_output=True)
        print("Dependencies installed via uv sync.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Note: uv sync skipped (uv not available or failed). Run 'uv sync' manually.")

    # --- Install pre-commit hooks if available ---
    try:
        subprocess.run(["uv", "run", "pre-commit", "install"], check=True, capture_output=True)
        print("Pre-commit hooks installed.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Note: pre-commit install skipped. Run 'uv run pre-commit install' manually.")

    project_name = "{{cookiecutter.project_name}}"
    print(f"\nProject '{project_name}' created successfully!")
    print("Next steps:")
    print(f"  cd {project_name}")
    print("  make install      # if uv sync didn't run above")
    print("  make check        # run code quality tools")
    print("  make test         # run tests")
