from typing import final
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.events import Click
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Tab, Tabs

from changedetection_tui.dashboard.jump_overlay import JumpOverlay
from changedetection_tui.dashboard.jumper import Jumper
from changedetection_tui.settings import default_keymap


# Screen -> Widget -> DOMNode
# So we use inherit_bindings=False to avoid inheriting from Screen.BINDINGS:
# - tab=focus_next
# - Shift+tab=focus_previous
# - ctrl+c=copy_text
@final
class MainScreen(Screen[None], inherit_bindings=False):
    BINDINGS = [
        Binding(
            key=default_keymap["main_screen"]["open_jump_mode"]["default"],
            action="toggle_jump_mode",
            description="Jump",
            tooltip="Activate jump mode to quickly move focus between widgets.",
            id="main_screen.open_jump_mode",
        ),
        Binding(
            key=default_keymap["main_screen"]["quit"]["default"],
            action="app.quit",
            description="quit",
            show=True,
            priority=False,
            tooltip="quit",
            id="main_screen.quit",
        ),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.jumper: Jumper | None = None

    def action_toggle_jump_mode(self) -> None:
        if self.jumper is None:
            return

        focused_before = self.focused
        if focused_before is not None:
            self.set_focus(None, scroll_visible=False)

        def handle_jump_target(target: str | Widget | None) -> None:
            if isinstance(target, str):
                try:
                    target_widget = self.screen.query_one(f"#{target}")
                except NoMatches:
                    self.log.warning(
                        f"Attempted to jump to target #{target}, but it couldn't be found on {self.screen!r}"
                    )
                else:
                    if target_widget.focusable:
                        self.set_focus(target_widget)
                    else:
                        if isinstance(target_widget, Tab):
                            try:
                                parent_tabs = target_widget.query_ancestor(Tabs)
                                if parent_tabs and target_widget.id:
                                    parent_tabs.active = target_widget.id
                                    self.set_focus(parent_tabs)
                            except NoMatches:
                                self.log.warning(
                                    "Programming error - no parent Tabs widget found"
                                    + "when trying to focus from Jump Mode."
                                )
                        else:
                            # We're trying to move to something that isn't focusable,
                            # and isn't a Tab within a Tabs, so just send a click event.
                            # It's probably the best we can do.
                            _ = target_widget.post_message(
                                Click(
                                    widget=target_widget,
                                    x=0,
                                    y=0,
                                    delta_x=0,
                                    delta_y=0,
                                    button=0,
                                    shift=False,
                                    meta=False,
                                    ctrl=False,
                                ),
                            )
            elif isinstance(target, Widget):
                self.set_focus(target)
            else:
                # If there's no target (i.e. the user pressed ESC to dismiss)
                # then re-focus the widget that was focused before we opened
                # the jumper.
                if focused_before is not None:
                    self.set_focus(focused_before, scroll_visible=False)

        self.app.clear_notifications()
        _ = self.app.push_screen(
            JumpOverlay(jumper=self.jumper), callback=handle_jump_target
        )

    def on_screen_resume(self) -> None:
        self.jumper = Jumper(
            {
                "only-unviewed": "1",
                "select-tags": "2",
                "search-input": "3",
                "ordering-by-select": "4",
                "ordering-direction-select": "5",
            },
            screen=self,
        )
