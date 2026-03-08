# API Diff: 0.50.31 → 0.54.4

## Diff command

```
git diff 0.50.31 0.54.4 -- changedetectionio/api/ docs/api-spec.yaml docs/api_v1/
```

## API changes summary

This is a **significant upgrade** spanning several minor versions. The changes include a new
endpoint (`/watch/{uuid}/difference/{from}/{to}`), a new spec-serving endpoint (`/full-spec`),
and extensive internal refactoring of how validation is done (OpenAPI-spec-driven instead of
hard-coded JSON Schema). The HTTP surface changes that matter most are:

- **New endpoint**: `GET /api/v1/watch/{uuid}/difference/{from_timestamp}/{to_timestamp}` —
  returns a formatted diff between two history snapshots.
- **New endpoint**: `GET /api/v1/full-spec` — returns the merged live OpenAPI spec (no auth).
- **`GET /api/v1/watch` list response**: `muted` field renamed to `notification_muted` in
  example payloads; the actual response key from the model was already `notification_muted`,
  so this is a documentation fix, not a behavioral change.
- **`GET /api/v1/watch/{uuid}` recheck response**: was `"OK"` (plain string), now `"OK"` (still
  a string); format unchanged but callers should be aware the equality check in the project is
  fragile (see below).
- **`GET /api/v1/tag/{uuid}` recheck response**: changed from `"OK, N watches queued"` plain
  string to `{"status": "OK, queued N watches for rechecking"}` JSON object (for small batches)
  or `{"status": "...in background"}` with HTTP 202 (for ≥ 20 watches). This is a **breaking
  change** in response shape, but this project does not call the tag-recheck endpoint.
- **`POST /api/v1/import` response for large batches**: returns HTTP 202 with
  `{"status": "...", "count": N}` instead of a list of UUIDs when ≥ 20 URLs are submitted.
- **`last_error` field type**: expanded from `string` to `string | boolean | null`. The project's
  `ApiListWatch` Pydantic model already allows `str | Literal[False]` which handles the `false`
  boolean case, but does not handle `null`.
- **`Tag` schema**: now `allOf: [WatchBase, ...]` — the `Tag` response now includes all WatchBase
  fields in addition to tag-specific ones. The `date_created` field relied on by the project's
  `ApiTag` model was previously implicit; see impact note below.

No authentication/header changes. The `x-api-key` header scheme is unchanged.

---

## Changes affecting this project

### 1. `last_error` can now be `null` in `ApiListWatch`

**What changed:** The OpenAPI spec changed `last_error` from `type: string` to
`type: [string, boolean, 'null']`. This confirms three possible values: a string error message,
`false` (no error), or `null` (not yet checked).

**Impact:** The existing Pydantic model already handles `str | Literal[False]`. It does **not**
handle `None`. If the server returns `null` for `last_error` (e.g., on a newly-created watch),
Pydantic will raise a `ValidationError` crashing the watch list load.

**Proposed fix:**

Before (current code in this project):
```python
# file: src/changedetection_tui/types.py, line 8
    last_error: str | Literal[False]
```

After (proposed change):
```python
    last_error: str | Literal[False] | None
```

---

### 2. `RecheckButton` response check is fragile against HTTP 200 body changes

**What changed:** `GET /api/v1/watch/{uuid}?recheck=true` still returns `"OK"` (HTTP 200). No
functional change here. However, the check in `buttons.py` uses an exact string comparison with
`'"OK"'` (including JSON quotes stripped of newline). This is already fragile and worth noting.

**Impact:** Low risk — the recheck endpoint behavior is unchanged in this version bump. The
existing check `res.text.rstrip("\n") != '"OK"'` continues to work.

**Proposed fix:** No immediate action required. As a future hardening measure, consider checking
the HTTP status code instead of the body:

Before (current code in this project):
```python
# file: src/changedetection_tui/dashboard/buttons.py, lines 34-39
        if res.text.rstrip("\n") != '"OK"':
            raise httpx.HTTPStatusError(
                f"Unexpected API response while trying to recheck watch with uuid {uuid}",
                request=res.request,
                response=res,
            )
```

After (proposed change — more robust):
```python
        # HTTP 200 = queued; raise_for_status already happened in make_api_request
        # No additional check needed; success is guaranteed if no exception was raised.
```

---

### 3. `ApiTag` model may break on the expanded `Tag` schema response

**What changed:** The `Tag` schema is now `allOf: [WatchBase, {...tag-specific fields...}]`.
This means `GET /api/v1/tags` returns Tag objects that now include all WatchBase fields
(e.g., `last_checked`, `last_changed`, `paused`, etc.) alongside the tag-specific fields.

Additionally, the upstream code now explicitly **strips** watch-runtime fields from the tag GET
response (`Watch.py` in the Tag handler creates a `clean_tag` dict). So the actual response
will not include those runtime fields. However, `date_created` and `uuid` are still present.

The project's current `ApiTag` model:

```python
# file: src/changedetection_tui/types.py, lines 26-33
class ApiTag(BaseModel):
    date_created: int
    notification_muted: bool
    title: str
    uuid: str
```

Pydantic's default behavior ignores extra fields, so the additional WatchBase fields in the
response will be silently ignored. `date_created`, `notification_muted`, `title`, and `uuid`
should still be present. **No breaking change**, but worth confirming `date_created` is still
in the response. Looking at `WatchBase`, `date_created` is an inherited field so it will be
present.

**Impact:** Additive only. No action strictly required. The model uses Pydantic which ignores
extra fields by default.

**Proposed fix:** No change required. However, if stricter validation is ever enabled
(`model_config = ConfigDict(extra="forbid")`), this would break. Keep as-is.

---

### 4. New `GET /watch/{uuid}/difference/{from_timestamp}/{to_timestamp}` endpoint available

**What changed:** A brand-new endpoint exists that generates a formatted diff between two
history snapshots directly in the API. Supported formats: `text`, `html`, `htmlcolor`,
`markdown`. Supports `word_diff`, `no_markup`, `changesOnly`, `ignoreWhitespace`, `removed`,
`added`, `replaced` query parameters. Accepts `'previous'` and `'latest'` as keyword
timestamps.

**Impact:** Additive only. The project currently fetches the two raw snapshots separately and
runs `icdiff` locally in a subprocess (`diff_widgets.py` lines 70–101). The new endpoint could
replace this approach for use-cases that want server-side diffs, but no existing functionality
is broken.

**Proposed fix:** No change required to maintain current behavior. Opportunistically, the
`DiffPanelScreen` could be enhanced to use `GET /api/v1/watch/{uuid}/difference/previous/latest`
directly, but that is a new feature, not a required fix.

---

## Changes with no impact on this project

- **`POST /api/v1/import`**: Large import (≥ 20 URLs) now returns HTTP 202 instead of a list.
  The project does not use the import endpoint.
- **`PUT /api/v1/watch/{uuid}` strict validation**: The server now rejects unknown fields and
  read-only fields in PUT requests. The project only sends `{"last_viewed": <int>}` in PUT
  requests (via `SwitchViewedStateButton`), which is an explicitly allowed field in `UpdateWatch`.
  No impact.
- **`POST /api/v1/watch` no longer auto-queues**: New watches are no longer immediately queued
  for a recheck on creation (the scheduler handles it). The project does not create watches.
- **`GET /api/v1/full-spec`**: New unauthenticated YAML spec endpoint. Not used by the project.
- **Tag `recheck` response shape change**: `GET /api/v1/tag/{uuid}?recheck=true` changed
  response from plain string to JSON object. The project does not call this endpoint.
- **`Notifications` API internal changes** (`datastore.needs_write` → `datastore.commit()`):
  Internal implementation change; the HTTP surface is unchanged.
- **`Tags.py` `updateTag` validation tightening**: Server now rejects unknown fields in PUT tag
  requests. The project does not update tags via the API.
- **`WatchSingleHistory` 404 for missing timestamp**: Server now returns 404 if the requested
  timestamp doesn't exist in history. The project requests specific integer timestamps from the
  history list, so a valid timestamp is always used. The `'latest'` keyword is not used by this
  project (it fetches the raw list and picks the last key). No impact.
- **`WatchFavicon` path change** (`watch.watch_data_dir` → `watch.data_dir`): Internal server
  change; the API endpoint and response are identical.
- **`worker_handler` renamed to `worker_pool`**: Internal server refactoring; no API surface
  change.
- **OpenAPI spec `uuid` field removed from `WatchBase.properties`**: The `uuid` field was moved
  out of the listed schema properties (it's still returned in responses). The project reads
  `uuid` from `ApiWatch` (which is populated from the full watch GET, not from schema
  introspection). No impact.
- **`docs/api_v1/index.html` updated**: Pre-rendered ReDoc documentation file update. No
  functional impact on API behavior.
- **Various `| null` / `anyOf` type expansions in spec**: Fields like `body`, `proxy`,
  `notification_title`, `notification_body`, `webdriver_delay`, etc. are now typed as nullable.
  The project does not read these fields from API responses.
- **`notification_format` enum values changed** from `["Text", "HTML", "Markdown"]` to
  `["text", "html", "htmlcolor", "markdown", "System default"]`: The project does not use or
  parse this field.
- **New `WatchBase` fields in spec**: Many new fields documented
  (`include_filters`, `subtractive_selectors`, `trigger_text`, `conditions`, etc.). All
  additive; the project ignores extra fields via Pydantic defaults.

---

## Summary of proposed changes

| File | Change | Priority |
|------|--------|----------|
| `src/changedetection_tui/types.py:8` | Add `None` to `last_error` type annotation: `str \| Literal[False] \| None` | **High** — prevents `ValidationError` crash on newly-created watches |
| `src/changedetection_tui/dashboard/buttons.py:34-39` | Remove fragile `'"OK"'` string check (optional hardening) | Low |

Only **one change is required** to maintain correctness across the version bump: updating the
`last_error` type in `ApiListWatch` to allow `None`. All other changes are either
non-impacting, additive opportunities, or internal server refactors.
