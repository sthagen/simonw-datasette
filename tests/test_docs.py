"""
Tests to ensure certain things are documented.
"""

from datasette import app, utils
from datasette.app import Datasette
from datasette.filters import Filters
from pathlib import Path
import pytest
import re

docs_path = Path(__file__).parent.parent / "docs"
label_re = re.compile(r"\.\. _([^\s:]+):")


def get_headings(content, underline="-"):
    heading_re = re.compile(r"(\w+)(\([^)]*\))?\n\{}+\n".format(underline))
    return {h[0] for h in heading_re.findall(content)}


def get_labels(filename):
    content = (docs_path / filename).read_text()
    return set(label_re.findall(content))


@pytest.fixture(scope="session")
def settings_headings():
    return get_headings((docs_path / "settings.rst").read_text(), "~")


@pytest.mark.parametrize("setting", app.SETTINGS)
def test_settings_are_documented(settings_headings, setting):
    assert setting.name in settings_headings


@pytest.fixture(scope="session")
def plugin_hooks_content():
    return (docs_path / "plugin_hooks.rst").read_text()


@pytest.mark.parametrize(
    "plugin", [name for name in dir(app.pm.hook) if not name.startswith("_")]
)
def test_plugin_hooks_are_documented(plugin, plugin_hooks_content):
    headings = set()
    headings.update(get_headings(plugin_hooks_content, "-"))
    headings.update(get_headings(plugin_hooks_content, "~"))
    assert plugin in headings
    hook_caller = getattr(app.pm.hook, plugin)
    arg_names = [a for a in hook_caller.spec.argnames if a != "__multicall__"]
    # Check for plugin_name(arg1, arg2, arg3)
    expected = f"{plugin}({', '.join(arg_names)})"
    assert (
        expected in plugin_hooks_content
    ), f"Missing from plugin hook documentation: {expected}"


@pytest.fixture(scope="session")
def documented_views():
    view_labels = set()
    for filename in docs_path.glob("*.rst"):
        for label in get_labels(filename):
            first_word = label.split("_")[0]
            if first_word.endswith("View"):
                view_labels.add(first_word)
    # We deliberately don't document these:
    view_labels.update(("PatternPortfolioView", "AuthTokenView", "ApiExplorerView"))
    return view_labels


@pytest.mark.parametrize("view_class", [v for v in dir(app) if v.endswith("View")])
def test_view_classes_are_documented(documented_views, view_class):
    assert view_class in documented_views


@pytest.fixture(scope="session")
def documented_table_filters():
    json_api_rst = (docs_path / "json_api.rst").read_text()
    section = json_api_rst.split(".. _table_arguments:")[-1]
    # Lines starting with ``?column__exact= are docs for filters
    return {
        line.split("__")[1].split("=")[0]
        for line in section.split("\n")
        if line.startswith("``?column__")
    }


@pytest.mark.parametrize("filter", [f.key for f in Filters._filters])
def test_table_filters_are_documented(documented_table_filters, filter):
    assert filter in documented_table_filters


@pytest.fixture(scope="session")
def documented_fns():
    internals_rst = (docs_path / "internals.rst").read_text()
    # Any line that starts .. _internals_utils_X
    lines = internals_rst.split("\n")
    prefix = ".. _internals_utils_"
    return {
        line.split(prefix)[1].split(":")[0] for line in lines if line.startswith(prefix)
    }


@pytest.mark.parametrize("fn", utils.functions_marked_as_documented)
def test_functions_marked_with_documented_are_documented(documented_fns, fn):
    assert fn.__name__ in documented_fns


def test_rst_heading_underlines_match_title_length():
    """Test that RST heading underlines are the same length as their titles."""
    # Common RST underline characters
    underline_chars = ["-", "=", "~", "^", "+", "*", "#"]

    errors = []

    for rst_file in docs_path.glob("*.rst"):
        content = rst_file.read_text()
        lines = content.split("\n")

        for i in range(len(lines) - 1):
            current_line = lines[i]
            next_line = lines[i + 1]

            # Check if next line is entirely made of a single underline character
            # and is at least 5 characters long (to avoid false positives)
            if (
                next_line
                and len(next_line) >= 5
                and len(set(next_line)) == 1
                and next_line[0] in underline_chars
            ):
                # Skip if the previous line is empty (blank line before underline)
                if not current_line:
                    continue

                # Check if this is an overline+underline style heading
                # Look at the line before current_line to see if it's also an underline
                if i > 0:
                    prev_line = lines[i - 1]
                    if (
                        prev_line
                        and len(prev_line) >= 5
                        and len(set(prev_line)) == 1
                        and prev_line[0] in underline_chars
                        and len(prev_line) == len(next_line)
                    ):
                        # This is overline+underline style, skip it
                        continue

                # This is a heading underline
                title_length = len(current_line)
                underline_length = len(next_line)

                if title_length != underline_length:
                    errors.append(
                        f"{rst_file.name}:{i+1}: Title length {title_length} != underline length {underline_length}\n"
                        f"  Title: {current_line!r}\n"
                        f"  Underline: {next_line!r}"
                    )

    if errors:
        raise AssertionError(
            f"Found {len(errors)} RST heading(s) with mismatched underline length:\n\n"
            + "\n\n".join(errors)
        )


# Tests for testing_plugins.rst documentation

# fmt: off
# -- start test_homepage --
@pytest.mark.asyncio
async def test_homepage():
    ds = Datasette(memory=True)
    response = await ds.client.get("/")
    html = response.text
    assert "<h1>" in html
# -- end test_homepage --


# -- start test_actor_is_null --
@pytest.mark.asyncio
async def test_actor_is_null():
    ds = Datasette(memory=True)
    response = await ds.client.get("/-/actor.json")
    assert response.json() == {"actor": None}
# -- end test_actor_is_null --


# -- start test_signed_cookie_actor --
@pytest.mark.asyncio
async def test_signed_cookie_actor():
    ds = Datasette(memory=True)
    cookies = {"ds_actor": ds.client.actor_cookie({"id": "root"})}
    response = await ds.client.get("/-/actor.json", cookies=cookies)
    assert response.json() == {"actor": {"id": "root"}}
# -- end test_signed_cookie_actor --
