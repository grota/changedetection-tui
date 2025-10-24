from typing import TYPE_CHECKING, cast, final

try:
    from typing import override
except ImportError:
    from typing_extensions import override
from textual.app import ComposeResult
from textual.reactive import var
from textual.widget import Widget
from textual import on, work
from textual.widgets import Input, Select
from textual.worker import Worker, WorkerState

from changedetection_tui.dashboard.header import Ordering, WatchListHeader
from changedetection_tui.dashboard.pager import WatchListPager
from changedetection_tui.dashboard.watchlist import WatchListWidget
from changedetection_tui.types import ApiListWatches
from changedetection_tui.utils import make_api_request
from changedetection_tui.settings import SETTINGS
import httpx


@final
class Dashboard(Widget):
    all_rows: var[ApiListWatches] = var(ApiListWatches({}))
    current_page: var[int] = var(0)
    last_page: var[int] = var(0)
    rows_per_page: var[int] = var(0)
    only_unviewed: var[bool] = var(True)
    ordering: var[Ordering] = var(
        Ordering(
            order_by=Ordering.OrderBy.LAST_CHANGED,
            order_direction=Ordering.OrderDirection.DESC,
        )
    )

    @override
    def compose(self) -> ComposeResult:
        self.can_focus = False
        yield WatchListHeader(ordering=self.ordering)
        yield WatchListWidget(ordering=self.ordering).data_bind(
            Dashboard.all_rows,
            Dashboard.only_unviewed,
            Dashboard.ordering,
            Dashboard.current_page,
            Dashboard.rows_per_page,
        )
        yield WatchListPager().data_bind(
            Dashboard.current_page, Dashboard.last_page, Dashboard.rows_per_page
        )

    @on(WatchListHeader.FiltersChanged)
    def update_filtering(self, event: WatchListHeader.FiltersChanged) -> None:
        self.only_unviewed = event.only_unviewed

    @on(WatchListHeader.OrderingChanged)
    def update_ordering(self, event: WatchListHeader.OrderingChanged) -> None:
        self.ordering = event.ordering
        self.mutate_reactive(Dashboard.ordering)

    @on(WatchListHeader.TagFilterChanged)
    def selected_tag_has_changed(self, event: WatchListHeader.TagFilterChanged) -> None:
        input = self.query_exactly_one("#search-input")
        if TYPE_CHECKING:
            input = cast(Input, input)
        _ = self.search_watches(
            search_term=input.value,
            tag_title=event.tag_title if event.tag_title != Select.BLANK else None,
        )

    @on(WatchListHeader.InputSearchChanged)
    def input_search_term_has_changed(
        self, event: WatchListHeader.InputSearchChanged
    ) -> None:
        selected_tag = self.query_exactly_one("#select-tags")
        if TYPE_CHECKING:
            selected_tag = cast(Select[str], selected_tag)
        _ = self.search_watches(
            search_term=event.search_term,
            tag_title=selected_tag.value
            if selected_tag.value != Select.BLANK
            else None,
        )

    @on(WatchListWidget.LastPageChanged)
    def update_pager_last_page(self, event: WatchListWidget.LastPageChanged) -> None:
        self.last_page = event.last_page

    @on(WatchListPager.PageChanged)
    def pager_page_changed(self, event: WatchListPager.PageChanged) -> None:
        self.current_page = event.page_number

    @on(WatchListPager.ItemsPerPageChanged)
    def items_per_page_changed(self, event: WatchListPager.ItemsPerPageChanged) -> None:
        self.rows_per_page = event.value

    # textual's exclusiveness works using granularity of "group" (a param of this decorator) and "dom node".
    # We use exit_on_error to have an exception here set WorkerState.ERROR.
    @work(exclusive=True, exit_on_error=False)
    async def search_watches(
        self, search_term: str | None = None, tag_title: str | None = None
    ) -> ApiListWatches:
        params = {}
        if search_term:
            url = "/api/v1/search"
            params = {"q": search_term, "partial": "true"}
            if tag_title:
                params["tag"] = tag_title
        else:
            params = {"tag": tag_title} if tag_title else None
            url = "/api/v1/watch"

        try:
            response = (await make_api_request(self.app, url=url, params=params)).json()
        except httpx.HTTPError as exc:
            r = exc.request
            message = f"Error connecting to {r.url}"
            self.log.error(message, exc)
            self.notify(
                severity="error",
                title=message,
                message=str(exc),
            )
            raise
        except httpx.InvalidURL as exc:
            self.log.error(exc)
            self.notify(
                title="Invalid URL",
                severity="error",
                message=str(exc),
            )
            raise

        return ApiListWatches.model_validate(response)

    @on(Worker.StateChanged)
    def get_watch_list_result_from_worker(self, event: Worker.StateChanged) -> None:
        worker = cast(Worker[ApiListWatches], event.worker)
        if worker.name not in ["search_watches"]:
            return
        if event.state == WorkerState.ERROR:
            self.loading = False
            return
        if worker.state != WorkerState.SUCCESS:
            return
        api_list_of_watches = worker.result
        if not isinstance(api_list_of_watches, ApiListWatches):
            raise ValueError(
                f"Expected ApiListWatches, got {type(api_list_of_watches)}"
            )
        if TYPE_CHECKING:
            from changedetection_tui.app import TuiApp

            self.app = cast(TuiApp, cast(object, self.app))

        self.notify(
            title="connected",
            message=f"Loaded {len(api_list_of_watches.root.keys())} results from {SETTINGS.get().url}",
        )
        self.all_rows = api_list_of_watches
        self.loading = False
