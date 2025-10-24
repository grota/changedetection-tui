from itertools import islice

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
            key=default_keymap["main_screen"]["main_list_go_down"]["default"],
            action="go_down",
            description="↓",  # U+2193 Downwards Arrow
            tooltip="Focus element in next row",
            id="main_screen.main_list_go_down",
        ),
        Binding(
            key=default_keymap["main_screen"]["main_list_go_up"]["default"],
            action="go_up",
            description="↑",  # U+2191 Upwards Arrow
            tooltip="Focus element in previous row",
            id="main_screen.main_list_go_up",
        ),
        Binding(
            key=default_keymap["main_screen"]["main_list_go_right"]["default"],
            action="app.focus_next",
            description="→",  # U+2192 Rightwards Arrow
            tooltip="Focus next element",
            id="main_screen.main_list_go_right",
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
        filtered_tuples = [
            x
            for x in sorted(
                self.all_rows.root.items(),
                key=self._get_list_sorting_key,
                reverse=(self.ordering.order_direction == Ordering.OrderDirection.DESC),
            )
            if not self.only_unviewed or not x[1].viewed
        ]  # [(uuid, ApiListWatch), (uuid, ApiListWatch), ...]
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
