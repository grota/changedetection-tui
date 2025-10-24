import copy
from pathlib import Path

import pydantic
from changedetection_tui.settings import KeyBindingSettings, locations
from changedetection_tui.settings.kb_report import (
    ActionBinding,
    KeyBindingsReport,
    ConflictGroup,
)
from changedetection_tui.settings import Settings
import pytest
import yaml
from click.testing import CliRunner
from changedetection_tui.__main__ import cli

FAKE_URL = "http://example.com"
FAKE_APIKEY = "1234567890"
DEFAULT_KEYBINDINGS = {
    "main_screen": {
        "open_jump_mode": {
            "description": "KeyBinding to invoke jump-mode.",
            "value": "ctrl+j",
        },
        "quit": {
            "description": "KeyBinding to quit the application.",
            "value": "ctrl+c",
        },
        "open_settings": {
            "description": "KeyBinding to open the application settings.",
            "value": "ctrl+o",
        },
        "focus_next": {
            "description": "KeyBinding to move focus to the next item.",
            "value": "tab",
        },
        "focus_previous": {
            "description": "KeyBinding to move focus to the previous item.",
            "value": "shift+tab",
        },
        "open_palette": {
            "description": "KeyBinding to invoke the palette.",
            "value": "ctrl+p",
        },
        "main_list_go_left": {
            "description": "KeyBinding to go left in main list.",
            "value": "h",
        },
        "main_list_go_down": {
            "description": "KeyBinding to go down in main list.",
            "value": "j",
        },
        "main_list_go_up": {
            "description": "KeyBinding to go up in main list.",
            "value": "k",
        },
        "main_list_go_right": {
            "description": "KeyBinding to go right in main list.",
            "value": "l",
        },
    },
    "jump_mode": {
        "dismiss_jump_mode_1": {
            "description": "KeyBinding to dismiss the jump overlay.",
            "value": "escape",
        },
        "dismiss_jump_mode_2": {
            "description": "KeyBinding to dismiss the jump overlay.",
            "value": "ctrl+c",
        },
    },
}


@pytest.fixture
def setup_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    def _setup(filename: str = "config.yaml", content: dict | None = None):
        path = tmp_path / filename
        monkeypatch.setattr(locations, "config_file", lambda create_dir=False: path)
        if content:
            with open(path, "w") as f:
                yaml.safe_dump(content, f)
        return path

    return _setup


def test_keybindings_default_behavior():
    """behavior for default keybindings in code"""
    kbs = KeyBindingSettings()
    assert not kbs.non_default_actions
    assert not kbs.unbound_actions

    # report = kbs._report
    # assert report, 'model_post_init must have run'
    # assert kbs.model_dump() == copy.deepcopy(DEFAULT_KEYBINDINGS)
    # assert len(report.blocking_conflicts) == 0, (
    #     "Default keybindings in code should have no blocking conflicts"
    # )
    # assert len(report.non_blocking_conflicts) == 0, (
    #     "Default keybindings in code should have no non-blocking conflicts"
    # )


def test_settings_with_no_required_params(setup_config):
    setup_config("nonexistent_config.yaml")
    with pytest.raises(pydantic.ValidationError) as ex:
        _ = Settings()

    errors = ex.value.errors()
    assert len(errors) == 2
    assert errors[0]["loc"][0] == "url"
    assert errors[0]["msg"] == "Field required"
    assert errors[1]["loc"][0] == "api_key"
    assert errors[0]["msg"] == "Field required"


def test_settings_with_no_yaml(setup_config):
    setup_config("nonexistent_config.yaml")
    settings = Settings(url=FAKE_URL, api_key=FAKE_APIKEY)
    assert settings.model_dump() == {
        "url": FAKE_URL,
        "api_key": FAKE_APIKEY,
        "compact_mode": True,
        "keybindings": copy.deepcopy(DEFAULT_KEYBINDINGS),
    }, "With no file it still needs to be able to access defaults"
    assert not settings.keybindings.non_default_actions
    assert not settings.keybindings.unbound_actions

    # report = settings.keybindings._report
    # assert len(report.blocking_conflicts) == 0, ("And since it is using defaults there should be no conflicts")
    # assert len(report.non_blocking_conflicts) == 0, ("And since it is using defaults there should be no conflicts")


def test_settings_with_same_keys_but_in_different_sections(setup_config):
    setup_config(
        content={
            "keybindings": {
                "main_screen": {
                    "quit": {"description": "", "value": "ctrl+a"},
                },
                "jump_mode": {
                    "dismiss_jump_mode_2": {"description": "", "value": "ctrl+a"}
                },
            }
        }
    )
    settings = Settings(url=FAKE_URL, api_key=FAKE_APIKEY)
    assert settings.keybindings.main_screen.quit == "ctrl+a"
    assert settings.keybindings.jump_mode.dismiss_jump_mode_2 == "ctrl+a"

    assert settings.keybindings.non_default_actions == {
        "main_screen.quit",
        "jump_mode.dismiss_jump_mode_2",
    }
    assert not settings.keybindings.unbound_actions

    # report = settings.keybindings._report
    # assert len(report.blocking_conflicts) == 0, 'in different sections, no collisions'
    # assert len(report.non_blocking_conflicts) == 0, 'in different sections, no collisions'


def _get_report_from_exception(
    ex: pytest.ExceptionInfo[pydantic.ValidationError],
) -> KeyBindingsReport:
    validation_err = ex.value
    assert len(validation_err.errors()) == 1
    first_err = validation_err.errors()[0]
    report = first_err["ctx"]["report"]  # pyright: ignore[reportTypedDictNotRequiredAccess, reportAny]
    assert isinstance(report, KeyBindingsReport)
    return report


def test_settings_with_single_no_conflict_override(setup_config):
    """A single user override that does not conflict with any default binding"""
    setup_config(
        content={
            "keybindings": {
                "main_screen": {
                    "open_jump_mode": {
                        "description": "KeyBinding to invoke jump-mode.",
                        "value": "ctrl+a",
                    },
                }
            }
        }
    )
    settings = Settings(url=FAKE_URL, api_key=FAKE_APIKEY)
    assert settings.keybindings.main_screen.open_jump_mode == "ctrl+a"
    assert settings.keybindings.non_default_actions == {"main_screen.open_jump_mode"}
    assert not settings.keybindings.unbound_actions

    # report = settings.keybindings._report
    # assert report
    # assert len(report.blocking_conflicts) == 0, "ctrl+a is not used by defaults, there should be no conflicts"
    # assert len(report.non_blocking_conflicts) == 0


def test_settings_with_same_keys_in_same_section(setup_config):
    """Two user overrides (same section) that also conflict with a default binding

    Should be blocking, for the fact that it's a user error.
    """
    setup_config(
        content={
            "keybindings": {
                "main_screen": {
                    "open_jump_mode": {
                        "description": "KeyBinding to invoke jump-mode.",
                        "value": "ctrl+c",
                    },
                    "focus_next": {
                        "description": "KeyBinding to move focus to the next item.",
                        "value": "ctrl+c",
                    },
                },
            },
        }
    )

    with pytest.raises(pydantic.ValidationError) as ex:
        _ = Settings(url=FAKE_URL, api_key=FAKE_APIKEY)

    report = _get_report_from_exception(ex)
    assert report.blocking_conflicts == [
        ConflictGroup(
            key="ctrl+c",
            actions=[
                ActionBinding(
                    action="main_screen.open_jump_mode",
                    default_value=False,
                    key="ctrl+c",
                ),
                ActionBinding(
                    action="main_screen.quit", default_value=True, key="ctrl+c"
                ),
                ActionBinding(
                    action="main_screen.focus_next", default_value=False, key="ctrl+c"
                ),
            ],
        )
    ], "1 conflict, with 3 ActionBinding: 2 are user set, one comes from the defaults"
    assert len(report.non_blocking_conflicts) == 0


def test_settings_simple_override_that_unbinds_an_action(setup_config):
    """A single user override that conflicts with a default binding

    main_screen.focus_next=ctrl+c which collides with quit
    Should not be blocking, the default binding should be set unbound.
    """
    setup_config(
        content={
            "keybindings": {
                "main_screen": {
                    "focus_next": {
                        "description": "Original is tab, collides with quit",
                        "value": "ctrl+c",
                    },
                },
            },
        }
    )
    settings = Settings(url=FAKE_URL, api_key=FAKE_APIKEY)
    assert settings.keybindings.main_screen.focus_next == "ctrl+c"
    assert settings.keybindings.main_screen.quit is None

    assert settings.keybindings.non_default_actions == {"main_screen.focus_next"}, (
        "focus_next is set by the user and quit is unbound automatically"
        "(non_default_actions never contains None/unbound actions)"
    )
    assert settings.keybindings.unbound_actions == {"main_screen.quit"}


def test_make_settings(setup_config):
    path = setup_config()
    runner = CliRunner()
    result = runner.invoke(cli, input="http://example.com")
    print(f"{result.output=}|", result.exception)
    assert (
        result.output[0:-12]
        == f"""URL and API key are both required to operate.
This list is searched in order until a value is found:

- Command line switches. (--url, -u) / (--api-key, -a)
- Environment variables. (CDTUI_URL / CDTUI_APIKEY)
- Configuration file. ({path})
- Interactive prompt.

See 'cli --help' for more help.

Missing: url, api_key
You will now be prompted for missing values.
Values specified here can be persisted to the config file after launch via settings.

Please specify the URL: http://example.com
Please specify the API key (input will be hidden):"""
    )
