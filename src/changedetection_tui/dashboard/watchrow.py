from __future__ import annotations
from textual import on
from textual.app import ComposeResult
from textual.containers import HorizontalGroup, ItemGrid, VerticalGroup
from textual.events import Click
from textual.reactive import reactive
from textual.widgets import Static
from changedetection_tui.settings.settings import SETTINGS
from changedetection_tui.types import ApiListWatch
from typing import final

try:
    from typing import override, cast
except ImportError:
    from typing_extensions import override, cast
from changedetection_tui.dashboard.buttons import (
    RecheckButton,
    SwitchViewedStateButton,
    DiffButton,
    UpdatedWatchEvent,
)
from changedetection_tui.utils import format_timestamp


@final
class WatchRow(HorizontalGroup):
    """A row in the main watch list widget"""

    api_list_watch: reactive[ApiListWatch] = reactive(
        cast(ApiListWatch, cast(object, None)), recompose=True
    )

    def __init__(self, *args, uuid: str, watch: ApiListWatch, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # No need to invoke recompose here.
        self.set_reactive(WatchRow.api_list_watch, watch)
        self.uuid = uuid
        if self.api_list_watch.viewed:
            _ = self.add_class("viewed")

    @override
    def compose(self) -> ComposeResult:
        settings = SETTINGS.get()
        watch = self.api_list_watch
        viewed = watch.viewed
        title = watch.title_or_url()
        title = f'[link="{watch.url}"][u]{title}[/u][/link]'
        title = f"[dim]{title}[/dim]" if viewed else f"[bold]{title}[/bold]"
        # First column: title (or url) with optional error
        with VerticalGroup(classes="col-1"):
            yield Static(
                title, classes=f"watch-title {'viewed' if viewed else 'unviewed'}"
            )
            errors = f"[$error]{watch.last_error}[/]" if watch.last_error else ""
            yield Static(f"{errors}", classes="error-from-cd")
        # Second column
        yield Static(
            format_timestamp(
                watch.last_changed,
                format_type=(settings.compact_mode and "absolute" or "both"),
            ),
            classes="timestamp col-2",
        )
        # Third column
        yield Static(
            format_timestamp(
                watch.last_checked,
                format_type=(settings.compact_mode and "absolute" or "both"),
            ),
            classes="timestamp col-3",
        )
        # Fourth column: Action buttons
        # ItemGrid is undocumented, the min_column_width value has been found
        # via trial and error and I guess it will be an unstable api.
        with ItemGrid(classes="watch-actions col-4", min_column_width=5):
            flat = False
            compact = settings.compact_mode
            yield RecheckButton(
                "🔄 Recheck",
                id="recheck",
                classes="action-btn recheck-btn",
                flat=flat,
                compact=compact,
                action=f'focused.recheck("{self.uuid}")',
            )
            emoji_next_viewed_state = "☑️" if viewed else "✅"
            yield SwitchViewedStateButton(
                f"Set as {emoji_next_viewed_state}",
                id="switch_viewed_state",
                classes="action-btn switch-viewed-state-btn",
                flat=flat,
                compact=compact,
                uuid=self.uuid,
                last_changed=self.api_list_watch.last_changed,
                viewed=self.api_list_watch.viewed,
            )
            yield DiffButton(
                "📊 View Diff",
                id="diff-button",
                classes="action-btn diff-btn",
                flat=flat,
                compact=compact,
                action=f'focused.execute_diff("{self.uuid}")',
            )

    @on(UpdatedWatchEvent)
    def refresh_the_watchrow(self, event: UpdatedWatchEvent) -> None:
        self.api_list_watch = event.watch

    @on(Click)
    def focus_row(self, at_virtual_x: int | None = None) -> None:
        my_focusables = [w for w in list(self.query()) if w.focusable]
        idx_in_row = next(
            (
                i
                for i, w in enumerate(my_focusables)
                if w.virtual_region.x == at_virtual_x
            ),
            0,
        )
        if self.screen.focused not in my_focusables:
            self.screen.set_focus(my_focusables[idx_in_row])
