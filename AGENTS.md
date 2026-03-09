# Agent Guidelines for changedetection-tui

This project is a python  terminal user interface (TUI) client for the opensource [changedetection.io](https://github.com/dgtlmoon/changedetection.io) project.
It uses python's "textual".

## Run/Build/Lint/Test Commands

- **Start the development service**:
First make sure that the changedetection.io development service via docker compose is up and running: `docker compose -f compose-dev.yaml up -d`
Rationale: have a local testbed service that can we can safely invoke api calls on instead of the actual changedetection.io service the user might be using.

- **Run application**:
ALWAYS RUN THE PROGRAM SPECIFYING THE URL AND API-KEY EXPLICITLY LIKE THIS: `uv run cdtui --url=http://localhost:5000 --api-key=a9fa87b8421663bd958d3a34a705e049`
Rationale: the user might have their actual configuration file, you must not use that, so always specify the url and api key explicitly to the changedetection.io development service.

- **Install dependencies**: `uv sync`
- **Development run**: `textual run --dev .venv/bin/cdtui --url=http://localhost:5000 --api-key=a9fa87b8421663bd958d3a34a705e049`
- **Lint**: `uv run ruff check .`
- **Format code**: `uv run ruff format .`
- **Run tests**: `uv run pytest`

## Fetch of external references and guides

- If the user mentions "use context7" with a question related to the "textual" library you can skip the first call to resolve-library-id and make use of both the following library IDs:
  - "/websites/textual_textualize_io" (which references information from the user guide)
  - "/textualize/textual" (which references information from the github repo)

  These IDs are provided for both performance reasons and for completeness: choose one id based on the user query and use it with get-library-docs as many times as you need. Once you reach a conclusion cross check it by fetching documentation using the other id.
