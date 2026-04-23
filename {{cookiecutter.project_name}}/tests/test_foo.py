from {{cookiecutter.project_slug}}.foo import foo


def test_foo():
    assert foo("hello") == "hello"


def test_foo_empty():
    assert foo("") == ""
