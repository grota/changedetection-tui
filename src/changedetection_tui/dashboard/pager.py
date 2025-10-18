from typing import cast
from textual import on
from textual.app import ComposeResult
from textual.containers import HorizontalGroup
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, Select
from textual.reactive import reactive


class WatchListPager(Widget):
    class PageChanged(Message):
        def __init__(self, page_number: int) -> None:
            super().__init__()
            self.page_number = page_number

    class ItemsPerPageChanged(Message):
        def __init__(self, value: int) -> None:
            super().__init__()
            self.value = value

    current_page: reactive[int] = reactive(0, recompose=True)
    last_page: reactive[int] = reactive(0, recompose=True)
    rows_per_page: reactive[int] = reactive(0, recompose=True)

    def compose(self) -> ComposeResult:
        with HorizontalGroup(id="pager"):
            is_first_page = self.current_page == 0
            is_last_page = (
                self.current_page >= self.last_page
            )  # >= for when last_page=0 (when not connected)
            yield Button(
                "↤", id="first", disabled=is_first_page, compact=True
            )  # U+21A4 Leftwards Arrow from Bar
            yield Button(
                "🠄", id="prev", disabled=is_first_page, compact=True
            )  # U+1F804 Leftwards Arrow with Medium Triangle Arrowhead
            yield Label(
                f"Page {self.current_page + 1} of {self.last_page + 1}",
                id="label-current-page",
            )
            yield Button(
                "🠆", id="next", disabled=is_last_page, compact=True
            )  # U+1F806 Rightwards Arrow with Medium Triangle Arrowhead
            yield Button(
                "↦", id="last", disabled=is_last_page, compact=True
            )  # U+21A6 Rightwards Arrow from Bar
            yield Label(
                "Items per page:", id="items-per-page-label", classes="items-per-page"
            )
            yield Select[int](
                [
                    ("Auto", 0),
                    ("5 items", 5),
                    ("10 items", 10),
                    ("15 items", 15),
                    ("20 items", 20),
                ],
                id="items-per-page-select",
                classes="items-per-page",
                compact=True,
                value=self.rows_per_page,
                allow_blank=False,
            )

    @on(Button.Pressed, "#first")
    def go_to_first_page(self) -> None:
        self.current_page = 0

    @on(Button.Pressed, "#prev")
    def go_to_prev_page(self) -> None:
        if self.current_page == 0:
            return
        self.current_page -= 1

    @on(Button.Pressed, "#next")
    def go_to_next_page(self) -> None:
        if self.current_page == self.last_page:
            return
        self.current_page += 1

    @on(Button.Pressed, "#last")
    def go_to_last_page(self) -> None:
        self.current_page = self.last_page

    @on(Select.Changed, "#items-per-page-select")
    def emit_items_per_page_changed(self, event: Select.Changed) -> None:
        value = cast(int, event.value)
        self.post_message(self.ItemsPerPageChanged(value))

    def watch_current_page(self, new_page_number: int) -> None:
        self.post_message(self.PageChanged(new_page_number))
