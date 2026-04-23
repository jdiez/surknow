"""Example module demonstrating project conventions."""

import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger(
    "{{cookiecutter.project_slug}}.foo"
)


def foo(bar: str) -> str:
    """Return the input string unchanged.

    Args:
        bar: The input string.

    Returns:
        The same string, unmodified.
    """
    logger.debug("foo.called", input=bar)
    return bar


if __name__ == "__main__":  # pragma: no cover
    pass
