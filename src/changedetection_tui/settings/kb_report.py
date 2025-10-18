from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from changedetection_tui.settings import (
        JumpModeBindings,
        MainScreenBindings,
        KeyBindingSettings,
    )


@dataclass
class ActionBinding:
    action: str
    key: str | None
    default_value: bool


@dataclass
class ConflictGroup:
    key: str
    actions: list[ActionBinding]


class KeyBindingsReport:
    """Report for a keybindings model"""

    def __init__(self, keybindings: "KeyBindingSettings") -> None:
        self.keybindings: KeyBindingSettings = keybindings
        c = self._get_conflicts()
        self.non_blocking_conflicts: list[ConflictGroup] = c[1]
        """A list of groups where each group has 1 non-default actions"""
        self.blocking_conflicts: list[ConflictGroup] = c[0]
        """A list of groups where each group has 2 or more non-default actions"""

    def _get_conflicts(self) -> tuple[list[ConflictGroup], list[ConflictGroup]]:
        """
        Returns blocking and non-blocking conflicts.

        Returns:
            2 conflict lists.
            The first list has blocking conflicts, the second has non-blocking ones.

            A blocking conflict has at least 2 non-default actions
            A non blocking conflict has at most 1 non-default actions

            The implementation build a reverse key-to-action(s) dict.
            Each list has N groups, each groups is related to a specific key and list its conflicting Actions.
        """
        non_default_actions = self.keybindings.non_default_actions
        raw_conflicts: list[ConflictGroup] = []
        for context_name in type(self.keybindings).model_fields.keys():
            context_bindings = cast(
                "MainScreenBindings | JumpModeBindings",
                getattr(self.keybindings, context_name),
            )
            key_to_actions: dict[str, list[ActionBinding]] = {}
            for action, key in context_bindings.model_dump().items():
                namespaced_action_name = f"{context_name}.{action}"
                ab = ActionBinding(
                    action=namespaced_action_name,
                    key=key,
                    default_value=(namespaced_action_name not in non_default_actions),
                )
                key_to_actions.setdefault(key, []).append(ab)
            # Only add conflicts within this context
            context_conflicts = [
                ConflictGroup(key=k, actions=v)
                for k, v in key_to_actions.items()
                if len(v) >= 2
            ]
            raw_conflicts.extend(context_conflicts)

        blocking_conflicts = [
            group
            for group in raw_conflicts
            if len([act for act in group.actions if not act.default_value]) >= 2
        ]
        non_blocking_conflicts = [
            group
            for group in raw_conflicts
            if len([act for act in group.actions if not act.default_value]) == 1
        ]
        return blocking_conflicts, non_blocking_conflicts

    def get_confliction_kbs_message(self) -> str:
        message = ""
        for group in self.blocking_conflicts:
            message += f'Key "{group.key}" is assigned to the following actions:\n'
            for action in group.actions:
                message += f"  - {action.action}\n"
        return message.rstrip("\n")
