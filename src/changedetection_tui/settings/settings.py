from contextvars import ContextVar
from typing import Annotated, Any, Callable

try:
    from typing import override
except ImportError:
    from typing_extensions import override
from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    FieldSerializationInfo,
    create_model,
    field_serializer,
    model_validator,
)
from pydantic_core import PydanticCustomError
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)
import changedetection_tui.settings.locations as locations
from changedetection_tui.settings.kb_report import KeyBindingsReport


def parse_yaml_key_bindings(value: dict[str, str] | None) -> str | None:
    if not isinstance(value, dict):
        raise Exception(
            f'Unexpected value in yaml {value=}, should be a dict with a "value" key'
        )
    return value.get("value", None)


def base_serialize_keybinding_to_yaml_dict(
    field_name: str, value: str | None
) -> dict[str, Any]:
    if value is not None and not isinstance(value, str):
        raise Exception(f"Unexpected value {value.__class__}")
    desc = None
    for sub_model in [MainScreenBindings, JumpModeBindings]:
        if field_name in sub_model.model_fields:
            desc = sub_model.model_fields[field_name].description
            break
    if not desc:
        raise Exception(f"Missing description for field {field_name}")
    return {
        "description": desc,
        "value": value,
    }


KeyBinding = Annotated[str | None, BeforeValidator(parse_yaml_key_bindings)]

default_keymap = {
    "main_screen": {
        "open_jump_mode": {
            "default": "ctrl+j",
            "description": "KeyBinding to invoke jump-mode.",
            "label": "Launch jump-mode",
        },
        "quit": {
            "default": "ctrl+c",
            "description": "KeyBinding to quit the application.",
            "label": "Quit",
        },
        "open_settings": {
            "default": "ctrl+o",
            "description": "KeyBinding to open the application settings.",
            "label": "Open Settings",
        },
        "focus_next": {
            "default": "tab",
            "description": "KeyBinding to move focus to the next item.",
            "label": "Focus next item",
        },
        "focus_previous": {
            "default": "shift+tab",
            "description": "KeyBinding to move focus to the previous item.",
            "label": "Focus previous item",
        },
        "open_palette": {
            "default": "ctrl+p",
            "description": "KeyBinding to invoke the palette.",
            "label": "Open Palette",
        },
        "main_list_go_left": {
            "default": "h",
            "description": "KeyBinding to go left in main list.",
            "label": "Go left",
        },
        "main_list_go_down": {
            "default": "j",
            "description": "KeyBinding to go down in main list.",
            "label": "Go down",
        },
        "main_list_go_up": {
            "default": "k",
            "description": "KeyBinding to go up in main list.",
            "label": "Go up",
        },
        "main_list_go_right": {
            "default": "l",
            "description": "KeyBinding to go right in main list.",
            "label": "Go right",
        },
    },
    "jump_mode": {
        "dismiss_jump_mode_1": {
            "default": "escape",
            "description": "KeyBinding to dismiss the jump overlay.",
            "label": "Dismiss the overlay",
        },
        "dismiss_jump_mode_2": {
            "default": "ctrl+c",
            "description": "KeyBinding to dismiss the jump overlay.",
            "label": "Dismiss the overlay",
        },
    },
}
MainScreenBindings: type[BaseModel] = create_model(  # pyright: ignore[reportCallIssue, reportUnknownVariableType]
    "MainScreenBindings",
    **{
        k: (KeyBinding, Field(default=v["default"], description=v["description"]))
        for k, v in default_keymap["main_screen"].items()
    },  # pyright: ignore[reportArgumentType]
)

JumpModeBindings: type[BaseModel] = create_model(  # pyright: ignore[reportCallIssue, reportUnknownVariableType]
    "JumpModeBindings",
    **{
        k: (KeyBinding, Field(default=v["default"], description=v["description"]))
        for k, v in default_keymap["jump_mode"].items()
    },  # pyright: ignore[reportArgumentType]
)


class KeyBindingSettings(BaseModel):
    main_screen: Annotated[MainScreenBindings, {"Label": "Main KeyBindings"}] = Field(
        default_factory=MainScreenBindings
    )  # pyright: ignore[reportInvalidTypeForm, reportUnknownVariableType]
    jump_mode: Annotated[JumpModeBindings, {"Label": "Jump-mode KeyBindings"}] = Field(
        default_factory=JumpModeBindings
    )  # pyright: ignore[reportInvalidTypeForm, reportUnknownVariableType]
    _report: KeyBindingsReport | None = None

    @field_serializer(*list(default_keymap.keys()))
    def serialize_keybindings(
        self,
        value: MainScreenBindings | JumpModeBindings,
        info: FieldSerializationInfo,  # pyright: ignore[reportInvalidTypeForm]
    ) -> dict[str, Any]:
        # Serialize nested bindings recursively
        result = {}
        for field_name, field_value in value.model_dump().items():
            result[field_name] = base_serialize_keybinding_to_yaml_dict(
                field_name, field_value
            )
        return result

    @override
    def model_post_init(self, context: Any) -> None:
        from changedetection_tui.settings.kb_report import KeyBindingsReport

        self._report = KeyBindingsReport(self)

    @model_validator(mode="after")
    def cannot_have_conflicts(self):
        if not self._report:
            raise ValueError("Report not set")
        if len(self._report.blocking_conflicts):
            raise PydanticCustomError(
                "keybindings_conflicts",
                "There are conflicting keybindings in the configuration:\n"
                + "{conflicting_kbs_message}\n"
                + "Please edit {config_file} to remove the conflicts or the delete the file to use the defaults.",
                {
                    "report": self._report,
                    "conflicting_kbs_message": self._report.get_confliction_kbs_message(),
                    "config_file": locations.config_file(),
                },
            )
        return self

    @model_validator(mode="after")
    def unbind_default_keybinds_when_user_overrides(self):
        if not self._report:
            raise ValueError("Report not set")
        from changedetection_tui.utils import set_nested_attr

        for group in self._report.non_blocking_conflicts:
            for action_binding in group.actions:
                # Do not clobber the user ones.
                if not action_binding.default_value:
                    continue
                action = action_binding.action
                set_nested_attr(self, action, None)
        return self

    @property
    def non_default_actions(self) -> set[str]:
        """
        A set of namespaced action strings which are the actions set to non default keybinding.
        Unbound actions are not present in this set.
        """
        return self._return_actions(
            lambda current_value, default_value: (
                bool(current_value) and current_value != default_value
            )
        )

    @property
    def unbound_actions(self) -> set[str]:
        """
        A set of namespaced action strings which are the actions set to None
        """
        return self._return_actions(lambda current_value, _: not current_value)

    def _return_actions(self, predicate: Callable[[str | None, str], bool]):
        toreturn: set[str] = set()
        for context_name in type(self).model_fields.keys():
            context_bindings: MainScreenBindings | JumpModeBindings = getattr(
                self, context_name
            )
            bindings_type = type(context_bindings)
            context_defaults = bindings_type()
            for action in bindings_type.model_fields:
                current_value = getattr(context_bindings, action)
                default_value = getattr(context_defaults, action)
                if predicate(current_value, default_value):
                    namespaced_action_name = f"{context_name}.{action}"
                    toreturn.add(namespaced_action_name)
        return toreturn


class Settings(BaseSettings):
    url: Annotated[
        str,
        {
            "click_args": ("--url", "-u"),
            "envvar": "CDTUI_URL",
            "help": "The changedetection URL",
        },
    ]
    api_key: Annotated[
        str,
        {
            "click_args": ("--api-key", "-a"),
            "envvar": "CDTUI_APIKEY",
            "help": "The changedetection API key",
        },
    ]
    compact_mode: Annotated[
        bool,
        {
            "help": "Display in compact mode",
        },
    ] = True
    keybindings: KeyBindingSettings = Field(default_factory=KeyBindingSettings)

    @classmethod
    @override
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return init_settings, YamlConfigSettingsSource(
            settings_cls=settings_cls,
            yaml_file=locations.config_file(),
            yaml_file_encoding="utf-8",
        )


SETTINGS: ContextVar[Settings] = ContextVar("settings")
