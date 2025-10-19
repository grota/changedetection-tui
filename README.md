<div align="center">

  <h1>Changedetection TUI</h1>
</div>

<div align="center">

![GitHub Release](https://img.shields.io/github/v/release/grota/changedetection-tui?style=flat&logo=github&labelColor=black&color=369eff)
![PyPI - Version](https://img.shields.io/pypi/v/changedetection-tui)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/changedetection-tui)](https://pypi.org/project/changedetection-tui)
[![CI](https://github.com/grota/changedetection-tui/actions/workflows/ci.yml/badge.svg?event=push)](https://github.com/grota/changedetection-tui/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)


</div>

A terminal user interface (TUI) client for the opensource [changedetection.io](https://github.com/dgtlmoon/changedetection.io) project.


## 🖼️ Screenshots

### Main view

<img width="1718" height="1020" alt="Real-time dashboard view of your monitored URLs" src="https://github.com/user-attachments/assets/9f78eb27-a6bb-454c-9733-26a0bbd98c97" />

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
uvx changedetection-tui
```

Or install as a tool:

```bash
uv tool install changedetection-tui
```

### Using pip

```bash
pip install changedetection-tui
```

### Using docker

> [!WARNING]
> Not implemented yet.

## ⚡️ Usage

### 🚀 Quick Start

```bash
cdtui --url http://your-changedetection-url-here --api-key your-api-key-here
```

### 📖 Other ways to specify URL and api-key

<img width="754" height="448" alt="cdtui_help" src="https://github.com/user-attachments/assets/ae485b6b-c472-496a-99a8-cc700f7f2f81" />

The URL and the API key values found can also be persisted to the config file after launch via settings, here's a screenshot of the main section.

<img width="1110" height="469" alt="Main settings" src="https://github.com/user-attachments/assets/30ebf7fe-3633-451a-9794-af73b2dc4a95" />

Where you can see that you can avoid storing the api key secret to the config file by using the environment variable syntax.

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

# Run in development mode
uv run cdtui
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

## 🔗 Links

- [changedetection.io](https://github.com/dgtlmoon/changedetection.io)
- [Textual Framework](https://textual.textualize.io/)
- [GitHub Repository](https://github.com/grota/changedetection-tui)
- [Issue Tracker](https://github.com/grota/changedetection-tui/issues)
