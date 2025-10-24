from datetime import datetime
import os
import httpx
from typing import TYPE_CHECKING, Any, cast, Literal
from collections.abc import Mapping
from textual.app import App
from textual.binding import Binding
from changedetection_tui.settings import SETTINGS, Settings, default_keymap
import functools
import operator


def format_timestamp(
    timestamp: int, format_type: Literal["relative", "absolute", "both"] = "both"
) -> str:
    """Format timestamp as human readable date and relative time"""
    if timestamp == 0:
        return "Never"

    dt = datetime.fromtimestamp(timestamp)
    now = datetime.now()

    # Absolute date/time
    absolute = dt.strftime("%b %d, %Y %I:%M:%S %p")

    # Relative time
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        relative = "just now"
    elif seconds < 3600:  # less than 1 hour.
        minutes = seconds // 60
        relative = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:  # less than 1 day.
        hours = seconds // 3600
        relative = f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:  # less than 1 week.
        days = seconds // 86400
        relative = f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 2592000:  # less than 30 day.
        weeks = seconds // 604800
        relative = f"{weeks} week{'s' if weeks != 1 else ''} ago"
    else:
        months = seconds // 2592000
        relative = f"{months} month{'s' if months != 1 else ''} ago"

    if format_type == "relative":
        return relative
    elif format_type == "absolute":
        return absolute
    else:  # both
        return f"{relative}\n({absolute})"


def get_best_snapshot_ts_based_on_last_viewed(
    snapshot_timestamps: list[int], last_viewed: int
) -> int:
    """For diffing purposes.

    When asking to diff a watch, without specifying neither the from nor
    the to we need to infer both.
    The to is easy, it's the latest snapshot timestamp.
    The from needs to be figured out from the list of snapshot timestamps
    and that's what this method does.

    See changedetection.io implementation in models/Watch.py get_from_version_based_on_last_viewed()
    """

    # If it has been viewed more recently than the latest change then we
    # will diff between the latest two snapshots, so return the next to
    # last one.
    if last_viewed >= snapshot_timestamps[0]:
        return snapshot_timestamps[1]

    # When the 'last viewed' timestamp is between snapshots, return the older snapshot
    for newer, older in list(zip(snapshot_timestamps[0:], snapshot_timestamps[1:])):
        if last_viewed < int(newer) and last_viewed >= int(older):
            return older

    # When the 'last viewed' timestamp is less than the oldest snapshot, return oldest
    return snapshot_timestamps[-1]


async def make_api_request(
    app: App[None],
    url: str,
    method: str = "GET",
    params: dict[str, str] | None = None,
    data: Mapping[str, Any] | None = None,
    json: Any | None = None,
) -> httpx.Response:
    if TYPE_CHECKING:
        from changedetection_tui.app import TuiApp

        app = cast(TuiApp, app)
    settings = SETTINGS.get()

    api_key = (
        (os.getenv(settings.api_key[1:]) or "")
        if settings.api_key[0] == "$"
        else settings.api_key
    )
    async with httpx.AsyncClient() as client:
        request = httpx.Request(
            url=settings.url + url,
            method=method,
            params=params,
            data=data,
            headers={"x-api-key": api_key},
            json=json,
        )
        res = await client.send(request)
        try:
            _ = res.raise_for_status()
        except httpx.HTTPStatusError as exc:
            app.log.error(exc)
            app.notify(
                title="HTTP Error",
                message=f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.",
                severity="error",
            )
            raise
        except Exception as exc:
            app.log.error(exc)
            app.notify(
                title="Generic Exception",
                message=f"Error {exc}.",
                severity="error",
            )
            raise
        return res


def set_nested_attr(
    obj: object, path: str, value: Any, create_intermediates: bool = False
):
    *parts, last = path.split(".")
    target = obj
    for part in parts:
        if create_intermediates:
            if not hasattr(target, part):
                setattr(target, part, object())
            target = getattr(target, part)
        else:
            target = getattr(target, part)
    setattr(target, last, value)


def set_nested_dict(
    d: dict[str, Any], path: str, value: Any, create_intermediates: bool = False
):
    *parts, last = path.split(".")
    target = d
    for part in parts:
        if create_intermediates:
            target = target.setdefault(part, {})
        else:
            target = target[part]
    target[last] = value


def get_nested_dict(d: dict[str, Any], path: str):
    *parts, last = path.split(".")
    target = functools.reduce(operator.getitem, parts, d)
    return target[last]


def get_nested_attr(obj: object, path: str):
    *parts, last = path.split(".")
    target = functools.reduce(getattr, parts, obj)
    return getattr(target, last)


def construct_keymap(
    settings: Settings, limit_to_bindings: list[Binding] | None = None
) -> dict[str, str]:
    toreturn: dict[str, str] = {}
    ids_in_bindings = [b.id for b in limit_to_bindings] if limit_to_bindings else []
    for section, section_dict in default_keymap.items():
        for action_name in section_dict.keys():
            namespaced_action_name = f"{section}.{action_name}"
            # Ids in BINDINGS must match with the "path" in default_keymap
            if len(ids_in_bindings) and namespaced_action_name not in ids_in_bindings:
                continue
            toreturn[namespaced_action_name] = get_nested_attr(
                settings.keybindings, namespaced_action_name
            )
    return toreturn
