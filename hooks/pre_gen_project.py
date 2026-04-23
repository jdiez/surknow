"""Pre-generation hook: validates project name and slug."""
from __future__ import annotations

import re
import sys

PROJECT_NAME_REGEX = r"^[-a-zA-Z][-a-zA-Z0-9]+$"
project_name = "{{cookiecutter.project_name}}"
if not re.match(PROJECT_NAME_REGEX, project_name):
    print(
        f"ERROR: The project name '{project_name}' is not valid. "
        "Use letters, numbers, and hyphens only. Must start with a letter."
    )
    sys.exit(1)

PROJECT_SLUG_REGEX = r"^[_a-zA-Z][_a-zA-Z0-9]+$"
project_slug = "{{cookiecutter.project_slug}}"
if not re.match(PROJECT_SLUG_REGEX, project_slug):
    print(
        f"ERROR: The project slug '{project_slug}' is not a valid Python module name. "
        "Use letters, numbers, and underscores only. Must start with a letter or underscore."
    )
    sys.exit(1)
