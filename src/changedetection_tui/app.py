from pathlib import Path
from typing import final, override
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widgets import Footer, Header

from changedetection_tui.dashboard.dashboard import Dashboard
from changedetection_tui.settings import locations
from changedetection_tui.settings import SETTINGS, default_keymap
from changedetection_tui.settings.settings_screen import SettingsScreen
from changedetection_tui.theme import changedetection_tui
from changedetection_tui.main_screen import MainScreen
from changedetection_tui.utils import construct_keymap
import yaml
import os


class ComposeIsDone(Message):
    pass


@final
class TuiApp(App[None], inherit_bindings=False):
    """Main Textual App

    Using inherit_bindings=False to avoid inheriting the ctrl+q=quit in App.BINDINGS.
    """

    def __init__(self) -> None:
        super().__init__()
        settings = SETTINGS.get()
        self.title = "Changedetection TUI"
        self.register_theme(changedetection_tui)
        self.theme = "changedetection_tui"
        self.set_keymap(keymap=construct_keymap(settings))

    @override
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        wlw = Dashboard(id="dashboard")
        wlw.loading = True
        yield wlw
        _ = self.post_message(ComposeIsDone())

    @on(ComposeIsDone)
    def start_fetching_watches(self) -> None:
        self.notify("Connecting to changedetection...")
        self.query_exactly_one(Dashboard).search_watches()

    @on(SettingsScreen.SettingsChanged)
    def set_new_settings(self, event: SettingsScreen.SettingsChanged) -> None:
        conf_file_path = locations.config_file(create_dir=True)
        with open(conf_file_path, "w") as f:
            yaml.dump(event.new_settings.model_dump(), f, sort_keys=False)
        os.chmod(conf_file_path, 0o0600)
        _ = SETTINGS.set(event.new_settings)
        self.set_keymap(keymap=construct_keymap(event.new_settings))
        self.call_after_refresh(lambda: self.refresh(recompose=True))

    MODES = {
        "dashboard": MainScreen,
        "settings": SettingsScreen,
    }
    DEFAULT_MODE = "dashboard"

    CSS_PATH = Path(__file__).parent / "tui.scss"

    BINDINGS = [
        Binding(
            key=default_keymap["main_screen"]["focus_next"]["default"],
            action="app.focus_next",
            description="Focus Next",
            id="main_screen.focus_next",
        ),
        Binding(
            key=default_keymap["main_screen"]["focus_previous"]["default"],
            action="app.focus_previous",
            description="Focus Previous",
            id="main_screen.focus_previous",
        ),
        Binding(
            key=default_keymap["main_screen"]["open_settings"]["default"],
            action='switch_mode("settings")',
            description="Settings",
            id="main_screen.open_settings",
        ),
        Binding(
            key=default_keymap["main_screen"]["open_palette"]["default"],
            action="app.command_palette",
            description="palette",
            show=False,
            key_display=None,
            priority=True,
            tooltip="Open the command palette",
            id="main_screen.open_palette",
        ),
    ]
