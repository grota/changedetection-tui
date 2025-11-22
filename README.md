<div align="center">
  <h1>Changedetection TUI</h1>
</div>

<div align="center">

[![PyPI - Version](https://img.shields.io/pypi/v/changedetection-tui?style=for-the-badge&logo=pypi&logoColor=green)](https://pypi.org/project/changedetection-tui/)
[![Docker Image Version](https://img.shields.io/docker/v/grota/changedetection-tui?style=for-the-badge&logo=docker&label=docker&color=blue)](hub.docker.com/r/grota/changedetection-tui)
[![GitHub Release](https://img.shields.io/github/v/release/grota/changedetection-tui?style=for-the-badge&logo=github&labelColor=black&color=slategray)](https://github.com/grota/changedetection-tui/releases)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/changedetection-tui?style=for-the-badge&logo=python)](https://pypi.org/project/changedetection-tui)

</div>

<div align="center">

[![CI](https://github.com/grota/changedetection-tui/actions/workflows/ci.yml/badge.svg?event=push)](https://github.com/grota/changedetection-tui/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?logo=leanpub)](https://opensource.org/licenses/MIT)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

</div>

A terminal user interface (TUI) client for the opensource [changedetection.io](https://github.com/dgtlmoon/changedetection.io) project.


## 🖼️ Screenshots

### Main view

![main_view](https://github.com/user-attachments/assets/3449a9f2-1af4-4b7e-ae3c-f8802694e4d3)


<details>
<summary>Non compact view</summary>
<img width="1718" height="1020" alt="Real-time dashboard view of your monitored URLs" src="https://github.com/user-attachments/assets/9f78eb27-a6bb-454c-9733-26a0bbd98c97" />
</details>

### Jump mode

![jump_mode_compact](https://github.com/user-attachments/assets/920848b8-ee2f-4034-b63d-934617d05754)

<details>
<summary>Non compact view</summary>
<img width="1526" height="1014" alt="cdtui_jump_mode" src="https://github.com/user-attachments/assets/1ecdbee0-1f99-440f-ba5d-2ee8f3bd357a" />
</details>


### Settings (keybindings)

<img width="1104" height="1291" alt="cdtui_keybindings" src="https://github.com/user-attachments/assets/e6c29806-8fd1-473c-8e32-cc308449a850" />


### Diff selection modal

<img width="1389" height="651" alt="Diff selection modal" src="https://github.com/user-attachments/assets/b307e1bb-721b-4a7a-8924-5d60fe325432" />


## ✨ Features

- Real-time dashboard view of your monitored URLs
- Diff viewer (in terminal)
- Fast and lightweight
- Configurable keybindings, url and api key
- based on python's [Textual](https://textual.textualize.io/)


## 🚀 Installation

### Using uv (recommended)

```bash
uvx --from changedetection-tui cdtui
```

Or install as a tool:

```bash
uv tool install changedetection-tui
# $PATH must contain `uv tool dir`
cdtui
```

### Using pip

```bash
pip install changedetection-tui
```

### Using docker

Images are pushed both on the official [docker hub](https://hub.docker.com/r/grota/changedetection-tui)
and on Github's [container registry](https://github.com/grota/changedetection-tui/pkgs/container/changedetection-tui).
The images are the same, use whatever you want.

```bash
mkdir ~/.config/cdtui/

docker run --rm -it -v ~/.config/cdtui/:/home/appuser/.config/cdtui/ -u $(id -u):$(id -g) grota/changedetection-tui
# or
docker run --rm -it -v ~/.config/cdtui/:/home/appuser/.config/cdtui/ -u $(id -u):$(id -g) ghcr.io/grota/changedetection-tui
```

### Pushed tags

These are the docker image tags we push to both registries:

- The major-only semver tag (e.g. `grota/changedetection-tui:1`)
- The full semver tags (e.g. `grota/changedetection-tui:1.2.3`)
- The _latest_ tag: which corresponds to the last commit on the default branch (_main_)

## ⚡️ Usage

### 🚀 Quick Start

```bash
cdtui --url http://your-changedetection-url-here --api-key your-api-key-here
```

### 📖 Other ways to specify URL and API key

<img width="754" height="448" alt="cdtui_help" src="https://github.com/user-attachments/assets/ae485b6b-c472-496a-99a8-cc700f7f2f81" />

The URL and the API key values found can also be persisted to the configuration file after launch via settings, here's a screenshot of the main section.

<img width="1110" height="469" alt="Main settings" src="https://github.com/user-attachments/assets/30ebf7fe-3633-451a-9794-af73b2dc4a95" />

Where you can see that you can avoid storing the API key secret to the configuration file by using the environment variable syntax.

### Keybindings

Current keybindings can be seen in the footer, they can be remapped in settings.

- Open Jump Mode: ctrl+j
- Quit: ctrl+c
- Open settings; ctrl+o
- Focus next: tab
- Focus previous: shift+tab
- Open palette: ctrl+p
- Move left/down/up/right: hjkl
- Dismiss jump mode: esc/ctrl+c

## Roadmap

- [x] implement compact view mode
- [x] improve docker documentation usage
- [ ] create video demo?
- [ ] custom diff views?

## 👨‍💻 Development

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

```bash
# Clone the repository
git clone https://github.com/grota/changedetection-tui.git
cd changedetection-tui

# Install dependencies
uv sync --dev

# Run from venv
uv run cdtui

# Run in development mode
uv run textual console -x SYSTEM  -x WORKER -x DEBUG -x EVENT
# Run connecting to textual's console
uv run textual run --dev .venv/bin/cdtui
```

### Development Tools

```bash
# Install precommits (ruff linting and formatting)
uv run pre-commit install

# Run tests
uv run pytest

# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# optional: run a local installation of changedetection for development
docker compose -f compose-dev.yaml up -d

# Update changelog and create tag
uv run cz bump
```

### 📂 Project Structure

```
src/changedetection_tui/
├── __main__.py       # CLI entry point
├── app.py            # Main application
├── main_screen.py    # Main screen layout
├── dashboard/        # Dashboard components
├── settings/         # Settings management
├── utils.py          # Utility functions
└── tui.scss          # Textual CSS styling
```

## 📙 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links and acknowledgements

- [changedetection.io](https://github.com/dgtlmoon/changedetection.io)
- [Textual Framework](https://textual.textualize.io/)
- [GitHub Repository](https://github.com/grota/changedetection-tui)
- [Issue Tracker](https://github.com/grota/changedetection-tui/issues)
- [posting](https://github.com/darrenburns/posting) for showing me how to use `textual`
