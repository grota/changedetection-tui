from dataclasses import dataclass
import enum
from typing import cast, final, override
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


@dataclass()
class Ordering:
    class OrderBy(enum.IntEnum):
        LAST_CHANGED = enum.auto()
        LAST_CHECKED = enum.auto()

    order_by: OrderBy

    class OrderDirection(enum.StrEnum):
        ASC = enum.auto()
        DESC = enum.auto()

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
    def compose(self):
        with HorizontalGroup(classes="table-filters-and-ordering"):
            with HorizontalGroup(name="filters_group", classes="filters_group"):
                with VerticalGroup(
                    name="filter_group_only_to_be_viewed",
                    classes="filter_group_only_to_be_viewed",
                ):
                    yield Label("Show Only items:", variant="secondary")
                    yield Checkbox(
                        "To be viewed", value=self.only_unviewed, id="only-unviewed"
                    )
                with VerticalGroup(name="tags_group", classes="tags_group"):
                    yield Label("Tags:", variant="secondary")
                    yield Select([], id="select-tags", prompt="No tag selected")
                with VerticalGroup(name="search_group", classes="search_group"):
                    yield Label("Search for:", variant="secondary")
                    yield Input(id="search-input", tooltip="Enter to submit")
            with Grid(name="ordering_group", classes="ordering_group"):
                with VerticalGroup(id="order-by", classes="ordering"):
                    yield Label("Order by:", variant="secondary")
                    yield Select(
                        [
                            ("Last Changed", Ordering.OrderBy.LAST_CHANGED),
                            ("Last Checked", Ordering.OrderBy.LAST_CHECKED),
                        ],
                        allow_blank=False,
                        value=self.ordering.order_by,
                        id="ordering-by-select",
                    )
                with VerticalGroup(id="order-direction", classes="ordering"):
                    yield Label("Direction:", variant="secondary")
                    yield Select(
                        [
                            ("Desc", Ordering.OrderDirection.DESC),
                            ("Asc", Ordering.OrderDirection.ASC),
                        ],
                        allow_blank=False,
                        value=self.ordering.order_direction,
                        id="ordering-direction-select",
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
