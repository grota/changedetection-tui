from dataclasses import dataclass
from enum import IntEnum, Enum, auto
from typing import cast, final

from textual.app import ComposeResult
from textual.color import Color

try:
    from typing import override
except ImportError:
    from typing_extensions import override
from textual import on, work
from textual.containers import Grid, HorizontalGroup, VerticalGroup
from textual.message import Message
from textual.reactive import reactive
from textual.types import NoSelection, SelectType
from textual.widget import Widget
from textual.widgets import Checkbox, Input, Label, Select, Static
from textual.worker import WorkerFailed

from changedetection_tui.types import ApiListTags
from changedetection_tui.utils import make_api_request
from changedetection_tui.settings import SETTINGS


@dataclass()
class Ordering:
    class OrderBy(IntEnum):
        LAST_CHANGED = auto()
        LAST_CHECKED = auto()

    order_by: OrderBy

    class OrderDirection(Enum):
        ASC = auto()
        DESC = auto()

    order_direction: OrderDirection


@final
class WatchListHeader(Widget):
    only_unviewed: reactive[bool] = reactive(True)
    ordering: reactive[Ordering] = reactive(cast(Ordering, cast(object, None)))

    def __init__(self, *args, ordering: Ordering, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.set_reactive(WatchListHeader.ordering, ordering)

    @final
    class FiltersChanged(Message):
        def __init__(self, only_unviewed: bool) -> None:
            super().__init__()
            self.only_unviewed = only_unviewed

    @final
    class OrderingChanged(Message):
        def __init__(self, ordering: Ordering) -> None:
            super().__init__()
            self.ordering = ordering

    @final
    class TagFilterChanged(Message):
        def __init__(self, tag_title: SelectType | NoSelection) -> None:
            super().__init__()
            self.tag_title = tag_title

    @final
    class InputSearchChanged(Message):
        def __init__(self, search_term: str) -> None:
            super().__init__()
            self.search_term = search_term

    @override
    def compose(self) -> ComposeResult:
        settings = SETTINGS.get()
        table_filters_and_ordering = HorizontalGroup(
            classes="table-filters-and-ordering"
        )
        table_filters_and_ordering.styles.margin = (
            settings.compact_mode and (0, 0, 0, 0) or (0, 0, 1, 0)
        )
        with table_filters_and_ordering:
            filters_group = HorizontalGroup(
                name="filters_group", classes="filters_group"
            )
            filters_group.styles.border = (
                settings.compact_mode
                and ("none", "transparent")
                or ("solid", Color.parse(self.app.theme_variables["accent-darken-3"]))
            )
            with filters_group:
                with VerticalGroup(
                    name="filter_group_only_to_be_viewed",
                    classes="filter_group_only_to_be_viewed with-horizontal-margin",
                ):
                    yield Label("Show Only items:")
                    yield Checkbox(
                        "To be viewed",
                        value=self.only_unviewed,
                        id="only-unviewed",
                        compact=settings.compact_mode,
                    )
                with VerticalGroup(
                    name="tags_group", classes="tags_group with-horizontal-margin"
                ):
                    yield Label("Tags:")
                    yield Select(
                        [],
                        id="select-tags",
                        prompt="No tag selected",
                        compact=settings.compact_mode,
                    )
                with VerticalGroup(
                    name="search_group", classes="search_group with-horizontal-margin"
                ):
                    yield Label("Search for:")
                    yield Input(
                        id="search-input",
                        tooltip="Enter to submit",
                        compact=settings.compact_mode,
                    )
            ordering_group = Grid(name="ordering_group", classes="ordering_group")
            ordering_group.styles.border = (
                settings.compact_mode
                and ("none", "transparent")
                or ("solid", Color.parse(self.app.theme_variables["accent-darken-3"]))
            )
            with ordering_group:
                with VerticalGroup(id="order-by", classes="ordering"):
                    yield Label("Order by:")
                    yield Select(
                        [
                            ("Last Changed", Ordering.OrderBy.LAST_CHANGED),
                            ("Last Checked", Ordering.OrderBy.LAST_CHECKED),
                        ],
                        allow_blank=False,
                        value=self.ordering.order_by,
                        id="ordering-by-select",
                        compact=settings.compact_mode,
                    )
                with VerticalGroup(id="order-direction", classes="ordering"):
                    yield Label("Direction:")
                    yield Select(
                        [
                            ("Desc", Ordering.OrderDirection.DESC),
                            ("Asc", Ordering.OrderDirection.ASC),
                        ],
                        allow_blank=False,
                        value=self.ordering.order_direction,
                        id="ordering-direction-select",
                        compact=settings.compact_mode,
                    )
        with HorizontalGroup(classes="table-header"):
            yield Static("[bold]Title[/]", classes="col-1")
            yield Static("[bold]Last Changed[/]", classes="col-2")
            yield Static("[bold]Last Checked[/]", classes="col-3")
            yield Static("[bold]Actions[/]", classes="col-4")

    async def on_mount(self) -> None:
        try:
            api_list_of_tags = await self.load_tags().wait()
        except WorkerFailed as exc:
            # we don't do much here because there is already the main fail from
            # the "list watches" api call that notifies the user (for things
            # like invalid hostname/port).
            self.log.error(exc)
            return
        select_tags = self.query_exactly_one("#select-tags")
        select_tags = cast(Select[str], select_tags)
        select_tags.set_options(
            [(tag.title, tag.title) for tag in api_list_of_tags.root.values()]
        )
        _ = self.query_exactly_one("#only-unviewed").focus()

    # exit_on_error=False to be able to catch exception in caller.
    @work(exclusive=True, exit_on_error=False)
    async def load_tags(self) -> ApiListTags:
        res = await make_api_request(self.app, url="/api/v1/tags")
        tags = ApiListTags.model_validate(res.json())
        return tags

    @on(Checkbox.Changed, "#only-unviewed")
    def propagate_unviewed_filter_changed(self, event: Checkbox.Changed) -> None:
        _ = event.stop()
        _ = self.post_message(self.FiltersChanged(only_unviewed=event.value))

    @on(Select.Changed, "#ordering-by-select")
    def propagate_order_by(self, event: Select.Changed) -> None:
        _ = event.stop()
        value = cast(Ordering.OrderBy, event.value)
        self.ordering.order_by = value
        _ = self.post_message(self.OrderingChanged(ordering=self.ordering))

    @on(Select.Changed, "#ordering-direction-select")
    def propagate_order_direction(self, event: Select.Changed) -> None:
        _ = event.stop()
        value = cast(Ordering.OrderDirection, event.value)
        self.ordering.order_direction = value
        _ = self.post_message(self.OrderingChanged(ordering=self.ordering))

    @on(Select.Changed, "#select-tags")
    def propagate_tag_selection(self, event: Select.Changed) -> None:
        _ = self.post_message(self.TagFilterChanged(event.value))

    @on(Input.Submitted, "#search-input")
    def propagate_search_term(self, event: Input.Submitted):
        _ = self.post_message(self.InputSearchChanged(event.value))
