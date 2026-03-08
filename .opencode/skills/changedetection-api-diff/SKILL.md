---
name: changedetection-api-diff
description: >
  Analyzes API changes between the currently checked-out version of the
  changedetection.io submodule and the latest upstream release tag. Produces a
  structured markdown report covering what changed in the API, and proposes
  concrete code changes (with before/after snippets) in the parent project to
  stay aligned. Advances the submodule to the latest tag when done.

  Use this skill whenever the user wants to update, sync, or upgrade the
  changedetection.io submodule, check what changed in the upstream API, review
  breaking changes before bumping the submodule, or understand what work is
  needed to stay compatible with a new release. Trigger on phrases like
  "update the submodule", "what changed in the API", "sync with upstream",
  "bump changedetection.io", "latest API changes", or "upgrade to new version".
---

# changedetection-api-diff

You are analyzing API changes between two versions of the `changedetection.io`
submodule and producing an actionable upgrade report for the parent project.

## Context

The parent project (`changedetection_tui`) wraps the `changedetection.io`
project as a git submodule located at `changedetection.io/`. The parent
project consumes changedetection.io's HTTP API, so when the upstream API
changes, the parent project may need updates too.

## Step 1: Establish the version range

All git commands below run from within the submodule directory. If you're
currently at the parent project root, use `workdir` or `cd changedetection.io`
as appropriate for your tool:

```bash
# What version are we on right now?
git describe --tags

# Fetch all upstream tags
git fetch --tags

# What's the newest upstream tag?
git tag --sort=-version:refname | head -1
```

Call the current version `<tag-from>` and the latest upstream tag `<tag-to>`.
If `<tag-from>` equals `<tag-to>`, there's nothing to do — tell the user and
stop.

## Step 2: Get the diff

Focus on the parts of the repo that define API behavior:

```bash
git diff <tag-from> <tag-to> -- changedetectionio/api/ docs/api-spec.yaml docs/api_v1/
```

Note: `docs/api_v1/` may not exist in older tags — if git reports it as an
unknown path, just drop it from the command. The `changedetectionio/api/`
directory and `docs/api-spec.yaml` are the primary targets.

Save the exact command you ran — it belongs in the report.

The diff will likely be long. Read it carefully. You're looking for:
- New endpoints or removed endpoints
- Changed request parameters (added, removed, renamed, type-changed)
- Changed response shapes
- Authentication or header changes
- Anything in `api-spec.yaml` that signals a contract change

Ignore noise: test fixtures, image files, comments-only changes, internal
refactors that don't affect the HTTP surface.

## Step 3: Understand the parent project's API usage

Before writing the report, ground yourself in how the parent project actually
calls the API. Look at the parent project's source (the `src/` directory at
the repo root, one level up from the submodule). Find the HTTP client code,
any API wrapper classes, endpoint constants, and response parsers.

This matters because a change in the upstream API only needs a proposed fix
if the parent project actually uses that endpoint or field.

## Step 4: Write the report

Write a markdown file to `assets/api-diff-<tag-from>-<tag-to>.md` in the
parent project root (i.e., `../assets/` relative to the submodule, or the
`assets/` directory at the repo root).

### Report structure

```markdown
# API Diff: <tag-from> → <tag-to>

## Diff command

\`\`\`
<the exact git diff command you ran>
\`\`\`

## API changes summary

Brief prose: how significant is this upgrade? Any breaking changes?

## Changes affecting this project

For each relevant change, one section:

### <Change title>

**What changed:** Description of the upstream change.

**Impact:** Does this break existing behavior? Is it additive only?

**Proposed fix:**

Before (current code in this project):
\`\`\`python
# file: src/path/to/file.py, around line N
<existing code>
\`\`\`

After (proposed change):
\`\`\`python
<updated code>
\`\`\`

## Changes with no impact on this project

List any upstream changes that don't require action here (e.g., endpoints this
project doesn't use), so the reader knows you considered them.

## Summary of proposed changes

Checklist of all files and functions that need updating, for easy tracking.
```

If there are no relevant changes at all, still write the report — note it
explicitly so there's a record that you checked.

## Step 5: Advance the submodule

After the report is written, update the submodule to the latest tag:

```bash
git checkout <tag-to>
```

Run this from within `changedetection.io/`. Then remind the user that the
parent project's `.gitmodules` / submodule pointer will need to be committed
to reflect the new version (they can do `git add changedetection.io && git
commit` from the parent repo when they're ready).

## Tips

- The `docs/api-spec.yaml` OpenAPI spec is the most reliable signal for
  contract changes. Prioritize changes there.
- When proposing code snippets, prefer minimal diffs — show only what needs
  to change, not entire functions.
- If the diff is very large (many releases skipped), consider whether it's
  worth breaking the report into sections by release. Use your judgment.
- If you can't determine which parent project code uses a given endpoint
  (maybe the codebase is large), say so explicitly rather than guessing.
