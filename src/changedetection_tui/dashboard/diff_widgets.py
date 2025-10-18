from typing import cast
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Grid, VerticalGroup
from textual.screen import ModalScreen
from textual.types import NoSelection
from textual.widgets import Button, Label, Select
from tempfile import TemporaryDirectory
from os import system, path

from textual.worker import Worker, WorkerState
from changedetection_tui.types import ApiListWatch, ApiWatch
from changedetection_tui.utils import (
    make_api_request,
    format_timestamp,
    get_best_snapshot_ts_based_on_last_viewed,
)
from pathvalidate import sanitize_filename


class DiffPanelScreen(ModalScreen):
    """Screen for diff selection"""

    BINDINGS = [("escape", "app.pop_screen", "Cancel")]

    def __init__(self, *args, uuid: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.uuid = uuid

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            with VerticalGroup(id="group-from", classes="group-from-to"):
                yield Label("Select from:")
                yield Select([], id="select-from")
            with VerticalGroup(id="group-to", classes="group-from-to"):
                yield Label("Select to:")
                yield Select([], id="select-to")
            yield Label("Proceed to diff?", id="question")
            yield Button("Ok", variant="primary", id="diff")
            yield Button("Cancel", variant="default", id="cancel")

    async def on_mount(self) -> None:
        self.query_exactly_one("#diff").focus()
        self.load_data(self.uuid)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "diff":
            self.app.pop_screen()
            return
        select_from = self.query_exactly_one("#select-from")
        select_from = cast(Select[int], select_from)
        from_ts = select_from.value

        select_to = self.query_exactly_one("#select-to")
        select_to = cast(Select[int], select_to)
        to_ts = select_to.value

        # do nothing if user selected same ts, or either is not selected
        if (
            from_ts == to_ts
            or isinstance(to_ts, NoSelection)
            or isinstance(from_ts, NoSelection)
        ):
            return
        from_data = (
            await make_api_request(
                self.app, url=f"/api/v1/watch/{self.uuid}/history/{from_ts}"
            )
        ).text
        to_data = (
            await make_api_request(
                self.app, url=f"/api/v1/watch/{self.uuid}/history/{to_ts}"
            )
        ).text
        with TemporaryDirectory() as tmpdir:
            from_filename = self._filename_for_diff(self.api_watch, from_ts)
            to_filename = self._filename_for_diff(self.api_watch, to_ts)
            from_filepath = path.join(tmpdir, from_filename)
            to_filepath = path.join(tmpdir, to_filename)

            with open(from_filepath, "w", encoding="utf-8") as from_file:
                from_file.write(from_data)
            with open(to_filepath, "w", encoding="utf-8") as to_file:
                to_file.write(to_data)

            with self.app.suspend():
                system(
                    f"icdiff --report-identical-files '{from_filepath}' '{to_filepath}' -U 10 --show-no-spaces| less --RAW-CONTROL-CHARS -+S --wordwrap"
                )
        self.app.pop_screen()

    @work(exclusive=True)
    async def load_data(self, uuid: str) -> tuple[list[int], int, ApiWatch]:
        res = await make_api_request(self.app, url=f"/api/v1/watch/{uuid}/history")
        json = cast(dict[str, str], res.json())
        snapshot_timestamps = [
            int(x)
            for x in sorted(
                list(json.keys()),
                key=lambda x: int(x),
                reverse=True,
            )
        ]
        res = await make_api_request(self.app, url=f"/api/v1/watch/{uuid}")
        watch = ApiWatch.model_validate(res.json())
        best_from_ts = get_best_snapshot_ts_based_on_last_viewed(
            snapshot_timestamps=snapshot_timestamps,
            last_viewed=int(watch.last_viewed),
        )
        return (snapshot_timestamps, best_from_ts, watch)

    @on(Worker.StateChanged)
    def get_watch_list_result_from_worker(self, event: Worker.StateChanged) -> None:
        worker = cast(Worker[tuple[list[int], int, ApiWatch]], event.worker)
        if worker.name != "load_data":
            return
        if worker.state != WorkerState.SUCCESS:
            return
        if not worker.result:
            return

        snapshot_timestamps = worker.result[0]
        best_from_ts = worker.result[1]
        select_from = self.query_exactly_one("#select-from")
        select_from = cast(Select, select_from)
        select_from.set_options(
            [(format_timestamp(ts), ts) for ts in snapshot_timestamps]
        )
        select_from.value = best_from_ts

        select_to = self.query_exactly_one("#select-to")
        select_to = cast(Select, select_to)
        select_to.set_options(
            [(format_timestamp(ts), ts) for ts in snapshot_timestamps]
        )
        select_to.value = snapshot_timestamps[0]

        self.api_watch = worker.result[2]

    def _filename_for_diff(self, watch: ApiListWatch, timestamp: int) -> str:
        return sanitize_filename(
            f"{watch.title_or_url()}_{format_timestamp(timestamp)}",
            replacement_text="_",
        )
