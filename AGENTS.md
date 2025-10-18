# Agent Guidelines for changedetection-tui

## Build/Lint/Test Commands

- **Install dependencies**: `uv sync`
- **Run application**: `uv run cdtui http://localhost:5000 a9fa87b8421663bd958d3a34a705e049`
- **Development run**: `textual run --dev .venv/bin/cdtui http://localhost:5000 a9fa87b8421663bd958d3a34a705e049`
- **Lint**: `uv run ruff check .` (if ruff configured)
- **Type check**: `uv run mypy .` (if mypy configured)

## Fetch of external references and guides

- If the user mentions "use context7" with a question related to the "textual" library you can skip the first call to resolve-library-id and make use of both the following library IDs:
  - "/websites/textual_textualize_io" (which references information from the user guide)
  - "/textualize/textual" (which references information from the github repo)

  These IDs are provided for both performance reasons and for completeness: choose one id based on the user query and use it with get-library-docs as many times as you need. Once you reach a conclusion cross check it by fetching documentation using the other id.

## Code Style Guidelines

ABOVE ALL: do not change existing code based only on style, e.g.:
- never change strings using single quotes to double quotes or vice versa.
- never change inline ifs or function calls from "inline" to "multiline".

### Imports
- Standard library imports first
- Third-party imports second
- Local imports last
- Use absolute imports for local modules
- Group imports with blank lines between groups

### Types
- Use type hints for all function parameters and return values
- Use `Union` or `|` for Python 3.10+ union types
- Use `Optional` for nullable types
- Use `cast()` when needed for type assertions
- Define data models with Pydantic BaseModel

### Naming Conventions
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`
- Variables: `snake_case`

### Error Handling
- Use try/except blocks for HTTP requests
- Raise exceptions with descriptive messages
- Log errors appropriately
- Use `raise` to re-raise caught exceptions

### Async/Await
- Use async functions for I/O operations
- Use `await` for httpx requests
- Use Textual's `@work` decorator for background tasks

### Documentation
- Use docstrings for all public functions
- Keep docstrings concise but descriptive
- Use type hints instead of documenting parameter types in docstrings

### Code Structure
- Keep functions focused on single responsibilities
- Use descriptive variable names
- Avoid magic numbers - use named constants
- Follow Textual patterns for UI components
