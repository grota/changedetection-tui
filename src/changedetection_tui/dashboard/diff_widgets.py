from typing import cast
import sys
import shutil
import subprocess
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Grid, VerticalGroup
from textual.screen import ModalScreen
from textual.types import NoSelection
from textual.widgets import Button, Label, Select
from tempfile import TemporaryDirectory
from os import path
import shlex

from textual.worker import Worker, WorkerState
from changedetection_tui.settings import SETTINGS
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
        self.api_watch: ApiWatch

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
        diff_settings = SETTINGS.get().diff
        if diff_settings.mode == "command-based":
            from_data = (
                await make_api_request(
                    self.app, route=f"/api/v1/watch/{self.uuid}/history/{from_ts}"
                )
            ).text
            to_data = (
                await make_api_request(
                    self.app, route=f"/api/v1/watch/{self.uuid}/history/{to_ts}"
                )
            ).text
            self._run_command_based_diff(
                from_data=from_data,
                to_data=to_data,
                from_ts=from_ts,
                to_ts=to_ts,
            )
        else:
            await self._run_internal_diff(from_ts=from_ts, to_ts=to_ts)
        _ = self.app.pop_screen()

    def _run_command_based_diff(
        self,
        from_data: str,
        to_data: str,
        from_ts: int,
        to_ts: int,
    ) -> None:
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
                cmd = self._expand_command_based_diff_template(
                    from_filepath=from_filepath,
                    to_filepath=to_filepath,
                )
                _ = subprocess.run(cmd, shell=True, check=True)

    def _expand_command_based_diff_template(
        self, from_filepath: str, to_filepath: str
    ) -> str:
        settings = SETTINGS.get()
        template = settings.diff.command_template
        tokens = {
            "{ICDIFF}": shlex.quote(self._get_path_for("icdiff")),
            "{FILE_FROM}": shlex.quote(from_filepath),
            "{FILE_TO}": shlex.quote(to_filepath),
        }
        expanded_command = template
        for token, value in tokens.items():
            expanded_command = expanded_command.replace(token, value)
        return expanded_command

    async def _run_internal_diff(self, from_ts: int, to_ts: int) -> None:
        settings = SETTINGS.get().diff
        params: dict[str, str] = {
            "format": settings.internal_format,
            "word_diff": self._bool_to_api_string(settings.internal_word_diff),
            "no_markup": self._bool_to_api_string(settings.internal_no_markup),
            "type": settings.internal_type,
            "changesOnly": self._bool_to_api_string(settings.internal_changes_only),
            "ignoreWhitespace": self._bool_to_api_string(
                settings.internal_ignore_whitespace
            ),
            "removed": self._bool_to_api_string(settings.internal_removed),
            "added": self._bool_to_api_string(settings.internal_added),
            "replaced": self._bool_to_api_string(settings.internal_replaced),
        }
        internal_diff = (
            await make_api_request(
                self.app,
                route=f"/api/v1/watch/{self.uuid}/difference/{from_ts}/{to_ts}",
                params=params,
            )
        ).text
        with TemporaryDirectory() as tmpdir:
            internal_diff_filepath = path.join(
                tmpdir,
                self._filename_for_internal_diff(self.api_watch, from_ts, to_ts),
            )
            with open(internal_diff_filepath, "w", encoding="utf-8") as output_file:
                output_file.write(internal_diff)
            with self.app.suspend():
                _ = subprocess.run(
                    [
                        "less",
                        "--RAW-CONTROL-CHARS",
                        "-+S",
                        "--wordwrap",
                        internal_diff_filepath,
                    ],
                    check=True,
                )

    def _filename_for_internal_diff(
        self, watch: ApiListWatch, from_timestamp: int, to_timestamp: int
    ) -> str:
        return sanitize_filename(
            f"{watch.title_or_url()}_internal_diff_{format_timestamp(from_timestamp)}_to_{format_timestamp(to_timestamp)}.txt",
            replacement_text="_",
        )

    def _bool_to_api_string(self, value: bool) -> str:
        return value and "true" or "false"

    @work(exclusive=True)
    async def load_data(self, uuid: str) -> tuple[list[int], int, ApiWatch]:
        res = await make_api_request(self.app, route=f"/api/v1/watch/{uuid}/history")
        json = cast(dict[str, str], res.json())
        snapshot_timestamps = [
            int(x)
            for x in sorted(
                list(json.keys()),
                key=lambda x: int(x),
                reverse=True,
            )
        ]
        res = await make_api_request(self.app, route=f"/api/v1/watch/{uuid}")
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

    def _get_path_for(self, cmd: str) -> str:
        """Get the path to the cmd in the current Python environment."""
        cmd_path = shutil.which(cmd)
        if cmd_path:
            return cmd_path

        # Fallback: try to find it in the same directory as the Python executable
        python_dir = path.dirname(sys.executable)
        fallback_path = path.join(python_dir, cmd)
        if path.exists(fallback_path):
            return fallback_path

        # Another fallback: try common bin directories
        for bin_dir in ["bin", "Scripts"]:
            fallback_path = path.join(path.dirname(python_dir), bin_dir, cmd)
            if path.exists(fallback_path):
                return fallback_path

        raise RuntimeError(f"{cmd} binary not found.")

    def _filename_for_diff(self, watch: ApiListWatch, timestamp: int) -> str:
        return sanitize_filename(
            f"{watch.title_or_url()}_{format_timestamp(timestamp)}",
            replacement_text="_",
        )
