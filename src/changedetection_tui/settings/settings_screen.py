from typing import Any, Literal, final, overload

try:
    from typing import override
except ImportError:
    from typing_extensions import override
from pydantic import ValidationError
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.events import Key
from textual.message import Message
from textual.screen import ModalScreen
from textual.containers import Grid, HorizontalGroup, VerticalScroll
from textual.validation import Failure, ValidationResult, Validator
from textual.widgets import Footer, Label, Input, Button, Static, TabPane, TabbedContent

from changedetection_tui.settings.kb_report import KeyBindingsReport
from changedetection_tui.settings.locations import config_file
from changedetection_tui.settings import (
    SETTINGS,
    JumpModeBindings,
    KeyBindingSettings,
    MainScreenBindings,
    Settings,
    default_keymap,
)
from changedetection_tui.utils import get_nested_dict, set_nested_dict


@final
class KeybindingValidator(Validator):
    """Step 3 of key-capturing"""

    def __init__(self, *args: Any, screen: "SettingsScreen", **kwargs: Any) -> None:  # pyright: ignore [reportAny, reportExplicitAny]
        super().__init__(*args, **kwargs)  # pyright: ignore [reportAny]
        self.screen: SettingsScreen = screen
        self.report: KeyBindingsReport | None = None
        """Set during validation"""

    @override
    def validate(self, value: str) -> ValidationResult:
        if self.screen.input_kbs_validation_always_pass:
            return self.success()

        try:
            settings_from_form = self.screen._reconstruct_settings_from_form()
            report = settings_from_form.keybindings._report
        except ValidationError as exception:
            errors = exception.errors()
            if len(errors) != 1 or errors[0]["type"] != "keybindings_conflicts":
                raise
            report = errors[0].get("ctx", {}).get("report")

        if not isinstance(report, KeyBindingsReport):
            raise ValueError(f"Expected KeyBindingsReport, got {type(report)}")
        if not len(report.non_blocking_conflicts) and not len(
            report.blocking_conflicts
        ):
            return self.success()

        self.report = report
        return self.failure(failures=Failure(validator=self))


@final
class SettingsScreen(ModalScreen[None], inherit_bindings=False):
    @final
    class SettingsChanged(Message):
        def __init__(self, new_settings: Settings) -> None:
            super().__init__()
            self.new_settings = new_settings

    BINDINGS = [
        Binding(
            key="escape,ctrl+c",
            action='app.switch_mode("dashboard")',
            description="Dismiss",
            show=True,
            key_display="escape,ctrl+c",
        ),
        Binding(
            key=default_keymap["main_screen"]["focus_next"]["default"],
            action="app.focus_next",
            description="Focus Next",
            id="main_screen.focus_next",
        ),
        Binding(
            key=default_keymap["main_screen"]["focus_previous"]["default"],
            action="app.focus_previous",
            description="Focus Previous",
            id="main_screen.focus_previous",
        ),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.key_capturing_input_target: Input | None = None
        """The Input for which we are currently capturing keys"""
        self.key_capturing_input_target_previous_value: str
        """The value of key_capturing_input_target at the start of key-capturing"""
        self.settings: Settings | None = SETTINGS.get()
        """The settings currently used by the form"""
        self.input_kbs_validation_always_pass = True
        """It is necessary to skip validation when inputs get set to the
        empty string due to the user choosing a key for an action X which is
        the default key for another action Y"""
        self.kb_inputs: dict[str, Input] = {}
        """A map of namespaced_actions to Input"""
        self.kb_transient_failure_labels: dict[str, Static] = {}
        """A map of namespaced_actions to Static labels used to show transient
        errors/warning for a binding"""

    def on_mount(self):
        _ = self.query_exactly_one("ContentTabs").focus()
        self.input_kbs_validation_always_pass = False

    @on(Button.Pressed, ".button-capture")
    def start_key_capturing(self, event: Button.Pressed) -> None:
        """Step 1 of key-capturing:
        set internal state(s), disable other buttons,
        add class to input to show it is capturing."""
        input = self._lookup_input_via_id_convention(event, "--capture")
        _ = input.add_class("key-capturing")
        self.key_capturing_input_target = input
        self.key_capturing_input_target_previous_value = input.value
        for button in self.query(Button):
            button.disabled = True

    @on(Key)
    def process_captured_key(self, event: Key) -> None:
        """Step 2 of key-capturing:
        set input value to captured key."""
        # Operate only when capturing a key.
        if not self.key_capturing_input_target:
            return
        # If we are capturing we don't want to also process our actions (like dismiss).
        if event.key in self.active_bindings.keys():
            _ = event.stop()

        self.key_capturing_input_target.value = event.key
        _ = self.key_capturing_input_target.remove_class("key-capturing")
        self.key_capturing_input_target = None
        for button in self.query(Button):
            button.disabled = False

    @on(Input.Changed, ".keybinding-input")
    def process_input_validation(self, event: Input.Changed) -> None:
        """Step 4 of key-capturing:
        process validation results from step 3.
        """
        if not event.validation_result:
            return
        if event.validation_result.is_valid:
            if not event.input.has_class("prevent-spurious-cleanup"):
                self._clean_up_transients_for_input(event.input)
            _ = event.input.remove_class("prevent-spurious-cleanup")
            return

        validator = event.validation_result.failures[0].validator
        if not isinstance(validator, KeybindingValidator):
            raise ValueError(f"Expected KeybindingValidator, got {type(validator)}")
        report = validator.report
        if not report:
            raise ValueError("No report available")

        self.log(f"{report.non_blocking_conflicts=}")
        self.log(f"{report.blocking_conflicts=}")
        # here we are sure that either or both blocking_conflicts or
        # non_blocking_conflicts are filled
        self.input_kbs_validation_always_pass = True
        self._reconstruct_form_from_non_blocking_conflicts(report, event.input)
        self._prevent_input_value_when_found_in_blocking_conflicts(report, event.input)
        self.input_kbs_validation_always_pass = False

    @on(Button.Pressed, ".button-reset-to-default")
    def reset_action_to_default(self, event: Button.Pressed) -> None:
        input = self._lookup_input_via_id_convention(event, "--reset-to-default")
        context_name, action = self._extract_context_name_and_action_from_input(
            input, False
        )
        input.value = default_keymap[context_name][action]["default"]

    @on(Button.Pressed, ".button-unbind")
    def set_input_to_none(self, event: Button.Pressed) -> None:
        input = self._lookup_input_via_id_convention(event, "--unbind")
        input.value = ""

    @on(TabbedContent.TabActivated)
    def hide_or_show_reset_all_kbs_button(
        self, event: TabbedContent.TabActivated
    ) -> None:
        self.query_exactly_one("#button-reset-all-keybindings").styles.display = (
            "none" if event.pane.id == "tabpane-main" else "block"
        )

    @on(Button.Pressed, "#button-reset-all-keybindings")
    def reset_all_keybindings(self) -> None:
        self.input_kbs_validation_always_pass = True
        for namespaced_action, input in self.kb_inputs.items():
            input.value = get_nested_dict(
                default_keymap, namespaced_action + ".default"
            )
        self.input_kbs_validation_always_pass = False

    @on(Button.Pressed, "#button-save-settings")
    async def save_new_settings(self) -> None:
        _ = self.post_message(
            self.SettingsChanged(new_settings=self._reconstruct_settings_from_form())
        )
        await self.app.action_switch_mode("dashboard")

    @override
    def compose(self) -> ComposeResult:
        keybinding_validator = KeybindingValidator(screen=self)
        conf_file = config_file()
        if not self.settings:
            raise RuntimeError("Settings not initialized")
        with VerticalScroll(id="vertical-scroll-main-content", can_focus=False):
            yield Label("Settings", id="settings-title")
            with TabbedContent(
                id="tabbed-content-root",
                initial="tabpane-keybindings" if conf_file.exists() else "tabpane-main",
            ):
                with TabPane("Main", id="tabpane-main"):
                    with Grid(id="grid-required-fields-settings"):
                        yield Label(
                            Settings.model_fields["url"].metadata[0]["help"]
                            or "No Label"
                        )
                        yield Input(value=self.settings.url, id="input-for-url")
                        yield Label(
                            Settings.model_fields["api_key"].metadata[0]["help"]
                            or "No Label"
                        )
                        yield Input(value=self.settings.api_key, id="input-for-apikey")
                        yield Label(
                            "(In the API Key field you can use the $ENV_VAR syntax to avoid storing the secret value to the config file)",
                            classes="required-field-description",
                        )
                with TabPane("Keybindings", id="tabpane-keybindings"):
                    with Grid(id="keybindings-settings-grid"):
                        for context_name, fieldinfo in type(
                            self.settings.keybindings
                        ).model_fields.items():
                            context_bindings = getattr(  # pyright: ignore [reportAny]
                                self.settings.keybindings, context_name
                            )
                            if not isinstance(
                                context_bindings, (MainScreenBindings, JumpModeBindings)
                            ):
                                raise ValueError(
                                    f"Unexpected type for context_bindings: {type(context_bindings)}"
                                )

                            yield Label(
                                fieldinfo.metadata[0]["Label"] or "No Label",
                                classes="label-keybindings-section",
                            )
                            for action, action_bound_to in context_bindings:
                                with HorizontalGroup(classes="label-and-input"):
                                    action_label = Label(
                                        default_keymap[context_name][action]["label"],
                                        classes="label-for-action",
                                    )
                                    action_label.tooltip = default_keymap[context_name][
                                        action
                                    ]["description"]
                                    yield action_label
                                    input = Input(
                                        value=action_bound_to,
                                        disabled=True,
                                        id=f"{context_name}-{action}--input",
                                        classes="keybinding-input",
                                        valid_empty=True,
                                        validators=[keybinding_validator],
                                        validate_on=["changed"],
                                    )
                                    namespaced_action_name = f"{context_name}.{action}"
                                    self.kb_inputs[namespaced_action_name] = input
                                    yield input

                                with HorizontalGroup(classes="horizgroup-buttons"):
                                    yield Button(
                                        label="Capture Key",
                                        variant="primary",
                                        id=f"{context_name}-{action}--capture",
                                        classes="button-capture",
                                    )
                                    yield Button(
                                        label="Reset to default",
                                        variant="success",
                                        classes="button-reset-to-default",
                                        id=f"{context_name}-{action}--reset-to-default",
                                    )
                                    unbind_button = Button(
                                        label="Unbind",
                                        variant="warning",
                                        classes="button-unbind",
                                        id=f"{context_name}-{action}--unbind",
                                    )
                                    unbind_button.tooltip = (
                                        "Disable binding to ignore action"
                                    )
                                    yield unbind_button
                                transient_failure_static = Static(
                                    content="",
                                    classes="transient-warning-msg",
                                    id=f"{context_name}-{action}--transient_warning_msg",
                                )
                                self.kb_transient_failure_labels[
                                    namespaced_action_name
                                ] = transient_failure_static
                                transient_failure_static.display = "none"
                                yield transient_failure_static
            with HorizontalGroup(classes="global-action-buttons"):
                yield Button(
                    label="Cancel",
                    id="button-cancel-submit-settings",
                    variant="default",
                    action='app.switch_mode("dashboard")',
                )
                yield Button(
                    label="Reset all keybindings",
                    id="button-reset-all-keybindings",
                    variant="warning",
                )
                yield Button(
                    label="Save Settings",
                    id="button-save-settings",
                    variant="primary",
                    tooltip=f"Settings will be saved to {conf_file}",
                )
            yield Footer()

    def _reconstruct_settings_from_form(self) -> Settings:
        input_for_url = self.screen.query_exactly_one("#input-for-url")
        if not isinstance(input_for_url, Input):
            raise ValueError(f"Expected Input, got {type(input_for_url)}")
        form_url = input_for_url.value
        input_for_apikey = self.screen.query_exactly_one("#input-for-apikey")
        if not isinstance(input_for_apikey, Input):
            raise ValueError(f"Expected Input, got {type(input_for_apikey)}")
        form_apikey = input_for_apikey.value

        kbs_payload: dict[str, dict[str, dict[str, str]]] = {}
        for namespaced_action, input in self.kb_inputs.items():
            set_nested_dict(
                kbs_payload,
                namespaced_action,
                {
                    "value": input.value,
                    "description": "",
                },
                create_intermediates=True,
            )

        settings_from_form = Settings(
            url=form_url,
            api_key=form_apikey,
            keybindings=KeyBindingSettings(**kbs_payload),  # pyright: ignore[reportArgumentType]
        )
        return settings_from_form

    def _clean_up_transients_for_input(self, input: Input) -> None:
        namespaced_action_name = self._extract_context_name_and_action_from_input(input)
        self.kb_transient_failure_labels[namespaced_action_name].styles.display = "none"
        _ = self.kb_inputs[namespaced_action_name].remove_class("transient-warning")

    def _reconstruct_form_from_non_blocking_conflicts(
        self, report: KeyBindingsReport, input_changed: Input
    ) -> None:
        namespaced_action_name = self._extract_context_name_and_action_from_input(
            input_changed
        )
        for group in report.non_blocking_conflicts:
            for actionBind in group.actions:
                # Only when input is directly involved in non_blocking_conflicts
                # clear its invalid status
                if namespaced_action_name == actionBind.action:
                    _ = input_changed.remove_class("-invalid")
                # skip the one set by user
                if not actionBind.default_value:
                    continue
                self.kb_inputs[actionBind.action].value = ""
                self._add_transient_warning_on_input(
                    input=self.kb_inputs[actionBind.action],
                    transient_message="Action was disabled due to another action having priority.",
                )

    def _prevent_input_value_when_found_in_blocking_conflicts(
        self, report: KeyBindingsReport, input_changed: Input
    ) -> None:
        namespaced_action_name = self._extract_context_name_and_action_from_input(
            input_changed
        )
        for group in report.blocking_conflicts:
            for actionBind in group.actions:
                if namespaced_action_name == actionBind.action:
                    self._add_transient_warning_on_input(
                        input=input_changed,
                        transient_message=f'The previous value "{self.key_capturing_input_target_previous_value} was restored". Another custom binding was detected for "{input_changed.value}"',
                    )
                    input_changed.value = self.key_capturing_input_target_previous_value
                    # We have just set back the input value to its previous
                    # (before key-capturing) value. This triggers again a
                    # successful validation that (without this sentinel value)
                    # would clean up immediately the transient-warnings.
                    _ = input_changed.add_class("prevent-spurious-cleanup")
                    break

    def _add_transient_warning_on_input(
        self, input: Input, transient_message: str
    ) -> None:
        namespaced_action_name = self._extract_context_name_and_action_from_input(input)
        _ = self.kb_inputs[namespaced_action_name].add_class("transient-warning")
        transient_label = self.kb_transient_failure_labels[namespaced_action_name]
        transient_label.content = transient_message
        transient_label.styles.display = "block"

    def _lookup_input_via_id_convention(
        self, event: Button.Pressed, postfix_to_strip: str
    ) -> Input:
        button_id = event.button.id
        if not button_id:
            raise ValueError("Button has no id")
        input_id = button_id.replace(postfix_to_strip, "--input")
        input = self.query_exactly_one(f"#{input_id}")
        if not isinstance(input, Input):
            raise ValueError(f"Expected Input, got {type(input)}")
        return input

    @overload
    def _extract_context_name_and_action_from_input(self, input: Input) -> str: ...

    @overload
    def _extract_context_name_and_action_from_input(
        self, input: Input, return_as_namespaced_str: Literal[False]
    ) -> tuple[str, str]: ...

    def _extract_context_name_and_action_from_input(
        self, input: Input, return_as_namespaced_str: bool = True
    ) -> tuple[str, str] | str:
        if not input.id:
            raise ValueError("Input has no id")
        context_name, action = input.id.removesuffix("--input").split("-", 2)
        return (
            f"{context_name}.{action}"
            if return_as_namespaced_str
            else (context_name, action)
        )
