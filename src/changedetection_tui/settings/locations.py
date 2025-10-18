from pathlib import Path
from xdg_base_dirs import xdg_config_home


def config_directory(create_dir: bool = False) -> Path:
    """Return (possibly creating) the application config directory."""
    directory = xdg_config_home() / "cdtui"
    if create_dir:
        directory.mkdir(exist_ok=True, parents=True)
    return directory


def config_file(create_dir: bool = False) -> Path:
    return config_directory(create_dir) / "config.yaml"
