from itertools import islice
from textual import on
from changedetection_tui.utils import invalidate_watchlist_cache

try:
    from itertools import batched
except ImportError:

    def batched(iterable, n: int, strict=False):
        if n < 1:
            raise ValueError("n must be at least one")
        iterator = iter(iterable)
        while batch := tuple(islice(iterator, n)):
            if strict and len(batch) != n:
                raise ValueError("batched(): incomplete batch")
            yield batch


from typing import Callable, cast, final

try:
    from typing import override
except ImportError:
    from typing_extensions import override
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.events import Resize
from textual.message import Message
from changedetection_tui.dashboard.header import Ordering
from changedetection_tui.settings import SETTINGS, default_keymap
from changedetection_tui.types import ApiListWatch, ApiListWatches
from changedetection_tui.dashboard.watchrow import WatchRow
from textual.reactive import reactive
from changedetection_tui.dashboard import buttons
import operator


@final
class WatchListWidget(VerticalScroll):
    all_rows: reactive[ApiListWatches] = reactive(ApiListWatches({}), recompose=True)
    only_unviewed: reactive[bool] = reactive(True, recompose=True)
    ordering: reactive[Ordering] = reactive(
        cast(Ordering, cast(object, None)), recompose=True
    )
    current_page: reactive[int] = reactive(0, recompose=True)
    rows_per_page: reactive[int] = reactive(0, recompose=True)

    BINDINGS = [
        Binding(
            key=default_keymap["main_screen"]["main_list_go_left"]["default"],
            action="app.focus_previous",
            description="←",  # U+2190 Leftwards Arrow
            tooltip="Focus previous element",
            id="main_screen.main_list_go_left",
        ),
        Binding(
            key=default_keymap["main_screen"]["main_list_go_left_2"]["default"],
            action="app.focus_previous",
            description="←",
            tooltip="Focus previous element",
            id="main_screen.main_list_go_left_2",
        ),
        Binding(
            key=default_keymap["main_screen"]["main_list_go_down"]["default"],
            action="go_down",
            description="↓",  # U+2193 Downwards Arrow
            tooltip="Focus element in next row",
            id="main_screen.main_list_go_down",
        ),
        Binding(
            key=default_keymap["main_screen"]["main_list_go_down_2"]["default"],
            action="go_down",
            description="↓",
            tooltip="Focus element in next row",
            id="main_screen.main_list_go_down_2",
        ),
        Binding(
            key=default_keymap["main_screen"]["main_list_go_up"]["default"],
            action="go_up",
            description="↑",  # U+2191 Upwards Arrow
            tooltip="Focus element in previous row",
            id="main_screen.main_list_go_up",
        ),
        Binding(
            key=default_keymap["main_screen"]["main_list_go_up_2"]["default"],
            action="go_up",
            description="↑",
            tooltip="Focus element in previous row",
            id="main_screen.main_list_go_up_2",
        ),
        Binding(
            key=default_keymap["main_screen"]["main_list_go_right"]["default"],
            action="app.focus_next",
            description="→",  # U+2192 Rightwards Arrow
            tooltip="Focus next element",
            id="main_screen.main_list_go_right",
        ),
        Binding(
            key=default_keymap["main_screen"]["main_list_go_right_2"]["default"],
            action="app.focus_next",
            description="→",
            tooltip="Focus next element",
            id="main_screen.main_list_go_right_2",
        ),
    ]

    def __init__(self, *args, ordering: Ordering, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.set_reactive(WatchListWidget.ordering, ordering)
        self.rows_per_page_from_resize: int = 0

    class LastPageChanged(Message):
        def __init__(self, last_page: int) -> None:
            super().__init__()
            self.last_page = last_page

    # order in which reactive methods are called: compute, validate, watch
    #
    # compute: like a getter.
    # the prop does not have its own value instead compute() is used
    # to get its value from OTHER reactive props, when those props change.
    #
    # validate: like a setter.
    # Used to intercept incoming value and optionally change the value.
    #
    # def compute_rows(self) -> list:
    # def validate_rows(self, rows: list) -> list:
    # def watch_rows(self, old_rows: list, new_rows: list) -> None:
    #
    # recompose re-calls compose. without it only render() would be re-called.

    @override
    def compose(self) -> ComposeResult:
        buttons.assigned_jump_keys = set()
        rows_per_page = self.rows_per_page
        if self.rows_per_page == 0:
            if self.rows_per_page_from_resize == 0:
                return
            rows_per_page = self.rows_per_page_from_resize
        self.can_focus: bool = False
        # order, filter, chunk. Here I have to materialize the list because I need to get the length of it.
        filtered_tuples = self._visible_rows()  # [(uuid, ApiListWatch), ...]
        tuples_for_page = batched(filtered_tuples, rows_per_page)
        batch = next(
            islice(tuples_for_page, self.current_page, self.current_page + 1), ()
        )  # ( up to 10 of (uuid,ApiListWatch) )
        for uuid, watch in batch:
            yield WatchRow(uuid=uuid, watch=watch, name=uuid)
        _ = self.post_message(
            self.LastPageChanged(
                (len(filtered_tuples) // rows_per_page)
                - (1 if len(filtered_tuples) % rows_per_page == 0 else 0)
            )
        )

    def _get_list_sorting_key(self, item: tuple[str, ApiListWatch]) -> int:
        return (
            item[1].last_changed
            if self.ordering.order_by == Ordering.OrderBy.LAST_CHANGED
            else item[1].last_checked
        )

    def on_resize(self, event: Resize) -> None:
        # This magic number is the height of a single WatchRow.
        single_watchrow_height = SETTINGS.get().compact_mode and 3 or 5
        self.rows_per_page_from_resize = event.size.height // single_watchrow_height
        if self.rows_per_page == 0:
            _ = self.refresh(recompose=True)

    def action_go_down(self) -> None:
        self.action_go_up_or_down(operator.gt, False)

    def action_go_up(self) -> None:
        self.action_go_up_or_down(operator.lt, True)

    def action_go_up_or_down(
        self, predicate: Callable[[int, int], bool], from_the_bottom: bool
    ):
        # self.screen.focused is one of my children that is focusable (a Button ATM)
        if not self.screen.focused:
            return
        parent_watchrow = self.screen.focused
        while parent_watchrow and not isinstance(parent_watchrow, WatchRow):
            parent_watchrow = parent_watchrow.parent
        if not parent_watchrow:
            return
        for sibling in (
            reversed(parent_watchrow.siblings)
            if from_the_bottom
            else parent_watchrow.siblings
        ):
            if not isinstance(sibling, WatchRow):
                continue
            if predicate(sibling.virtual_region.y, parent_watchrow.virtual_region.y):
                sibling.focus_row(at_virtual_x=self.screen.focused.virtual_region.x)
                break

    @on(buttons.UpdatedWatchEvent)
    def update_all_rows(self, event: buttons.UpdatedWatchEvent) -> None:
        """Takes care of updating the single watch in the list of rows"""
        # Invalidate watchlist cache after recheck
        invalidate_watchlist_cache()
        # Capture focus context before data mutation/recompose. Recompose can
        # destroy the currently focused button widget.
        visible_rows_before = self._visible_rows()
        focused_row_uuid, focused_col_index = self._focused_row_uuid_and_col_index()
        # Keep row position as fallback when the focused row disappears after
        # filtering (e.g. toggling "viewed" while "only_unviewed" is active).
        focused_row_index = (
            next(
                (
                    idx
                    for idx, (uuid, _) in enumerate(visible_rows_before)
                    if uuid == focused_row_uuid
                ),
                None,
            )
            if focused_row_uuid
            else None
        )
        self.app.log(focused_row_uuid, focused_col_index, focused_row_index)

        self.all_rows.root[event.uuid] = event.watch
        self.mutate_reactive(WatchListWidget.all_rows)

        if focused_col_index is None:
            return
        visible_rows_after = self._visible_rows()
        # Choose a stable target row after refresh: prefer same row, otherwise
        # preserve user's relative position in the list.
        target_uuid = self._target_uuid_after_update(
            visible_rows_after=visible_rows_after,
            focused_row_uuid=focused_row_uuid,
            focused_row_index=focused_row_index,
        )
        if not target_uuid:
            return
        # Restore focus after the DOM has been refreshed.
        _ = self.call_after_refresh(
            self._restore_focus_on_row,
            target_uuid,
            focused_col_index,
        )

    def _visible_rows(
        self,
    ) -> list[tuple[str, ApiListWatch]]:
        return [
            x
            for x in sorted(
                self.all_rows.root.items(),
                key=self._get_list_sorting_key,
                reverse=(self.ordering.order_direction == Ordering.OrderDirection.DESC),
            )
            if not self.only_unviewed or not x[1].viewed
        ]

    def _focused_row_uuid_and_col_index(self) -> tuple[str | None, int | None]:
        focused = self.screen.focused
        if not focused:
            return (None, None)
        parent = focused
        while parent and not isinstance(parent, WatchRow):
            parent = parent.parent
        if not isinstance(parent, WatchRow):
            return (None, None)
        # Save the column index (0=Recheck, 1=Set viewed, 2=View Diff) so we
        # can restore focus to the same action column on the target row.
        focusables = [w for w in parent.query() if w.focusable]
        col_index = next(
            (i for i, w in enumerate(focusables) if w is focused),
            0,
        )
        return (parent.uuid, col_index)

    def _target_uuid_after_update(
        self,
        visible_rows_after: list[tuple[str, ApiListWatch]],
        focused_row_uuid: str | None,
        focused_row_index: int | None,
    ) -> str | None:
        if not visible_rows_after:
            return None
        if focused_row_uuid and any(
            focused_row_uuid == row_uuid for row_uuid, _ in visible_rows_after
        ):
            return focused_row_uuid
        if focused_row_index is None:
            return None
        if focused_row_index < len(visible_rows_after):
            return visible_rows_after[focused_row_index][0]
        return visible_rows_after[-1][0]

    def _restore_focus_on_row(self, target_uuid: str, focused_col_index: int) -> None:
        target_row = next(
            (row for row in self.query(WatchRow) if row.uuid == target_uuid),
            None,
        )
        if not target_row:
            return
        target_row.focus_row(at_col_index=focused_col_index)
