from typing import final
import httpx
from textual import on
from changedetection_tui.dashboard.diff_widgets import DiffPanelScreen, execute_diff
from changedetection_tui.types import ApiListWatch, ApiWatch
from textual.widgets import Button
from textual.message import Message
from changedetection_tui.utils import (
    make_api_request,
    get_best_snapshot_ts_based_on_last_viewed,
)

assigned_jump_keys: set[str] = set()


def _get_next_jump_key() -> str | None:
    for char in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if char not in assigned_jump_keys:
            assigned_jump_keys.add(char)
            return char
    return None


@final
class RecheckButton(Button):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if key := _get_next_jump_key():
            self.jump_key = key

    async def action_recheck(self, uuid: str) -> None:
        res = await make_api_request(
            app=self.app,
            route=f"/api/v1/watch/{uuid}",
            params={"recheck": "true"},
        )
        if res.text.rstrip("\n") != '"OK"':
            raise httpx.HTTPStatusError(
                f"Unexpected API response while trying to recheck watch with uuid {uuid}",
                request=res.request,
                response=res,
            )
        res = await make_api_request(self.app, route=f"/api/v1/watch/{uuid}")
        # ATM this actually returns a larger watch obj compared to the smaller
        # one returned by the list watches api, but that is a subset so it
        # still works.
        watch = ApiListWatch.model_validate(res.json())
        _ = self.post_message(UpdatedWatchEvent(watch, uuid))


class DiffButton(Button):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if key := _get_next_jump_key():
            self.jump_key = key

    async def action_execute_diff(self, uuid: str) -> None:
        from changedetection_tui.settings import SETTINGS

        if not SETTINGS.get().skip_diff_dialog:
            self.app.push_screen(DiffPanelScreen(uuid=uuid))
            return

        # Skip the dialog: fetch history and watch data, then run diff directly.
        res = await make_api_request(self.app, route=f"/api/v1/watch/{uuid}/history")
        snapshot_timestamps = [
            int(x)
            for x in sorted(res.json().keys(), key=lambda x: int(x), reverse=True)
        ]
        res = await make_api_request(self.app, route=f"/api/v1/watch/{uuid}")
        watch = ApiWatch.model_validate(res.json())
        from_ts = get_best_snapshot_ts_based_on_last_viewed(
            snapshot_timestamps=snapshot_timestamps,
            last_viewed=int(watch.last_viewed),
        )
        to_ts = snapshot_timestamps[0]
        if from_ts == to_ts:
            return
        await execute_diff(
            app=self.app,
            watch=watch,
            uuid=uuid,
            from_ts=from_ts,
            to_ts=to_ts,
        )


@final
class SwitchViewedStateButton(Button):
    def __init__(
        self, *args, uuid: str, last_changed: int, viewed: bool, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.uuid = uuid
        self.last_changed = last_changed
        self.viewed = viewed
        if key := _get_next_jump_key():
            self.jump_key = key

    @on(Button.Pressed)
    async def switch_watch_viewed_state(self, event: Button.Pressed) -> None:
        _ = event.stop()
        # add + or - 1 to the last_checked ts based on its viewed state.
        last_viewed_ts = self.last_changed + (-1 if self.viewed else +1)
        res = await make_api_request(
            self.app,
            route=f"/api/v1/watch/{self.uuid}",
            json={"last_viewed": last_viewed_ts},
            method="PUT",
        )
        res = await make_api_request(self.app, route=f"/api/v1/watch/{self.uuid}")
        # ATM this actually returns a larger watch obj compared to the smaller
        # one returned by the list watches api, but that is a subset so it
        # still works.
        watch = ApiListWatch.model_validate(res.json())
        _ = self.post_message(UpdatedWatchEvent(watch, self.uuid))


@final
class UpdatedWatchEvent(Message):
    def __init__(self, watch: ApiListWatch, uuid: str) -> None:
        super().__init__()
        self.watch = watch
        self.uuid = uuid
