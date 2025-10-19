import os

try:
    from typing import override
except ImportError:
    from typing_extensions import override
import click
from urllib.parse import urlparse
from pydantic import ValidationError
from changedetection_tui.app import TuiApp
from changedetection_tui.settings import SETTINGS, Settings
import changedetection_tui.settings.locations as locations


class URL(click.ParamType):
    name: str = "url"

    @override
    def convert(
        self, value: str, param: click.Parameter | None, ctx: click.Context | None
    ):
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https"):
            self.fail(
                f"invalid URL scheme ({parsed.scheme}). Only HTTP(S) URLs are allowed",
                param,
                ctx,
            )
        return value


short_description = f"A {click.style('TUI', bold=True)} client for " + click.style(
    "changedetection.io", fg="bright_blue"
)


def get_url_and_apikey_help() -> str:
    return f"""
\b
{click.style("URL", italic=True)} and {click.style("API key", italic=True)} are both {click.style("required", fg="yellow", bold=True)} to operate.
This list is searched in order until a value is found:

\b
- Command line switches. ({", ".join(Settings.model_fields["url"].metadata[0]["click_args"])}) / ({", ".join(Settings.model_fields["api_key"].metadata[0]["click_args"])})
- Environment variables. ({Settings.model_fields["url"].metadata[0]["envvar"]} / {Settings.model_fields["api_key"].metadata[0]["envvar"]})
- Configuration file. ({click.style(locations.config_file(), fg="green")})
- Interactive prompt.
"""


def get_help() -> str:
    return f"""
{short_description}
{get_url_and_apikey_help()}
"""


@click.command(
    context_settings={"help_option_names": ["--help", "-h"]},
    help=get_help(),
    epilog="Repo at: https://github.com/grota/changedetection-tui",
)
@click.pass_context
@click.option(
    *Settings.model_fields["url"].metadata[0]["click_args"],
    type=URL(),
    show_envvar=True,
    envvar=Settings.model_fields["url"].metadata[0]["envvar"],
    help=Settings.model_fields["url"].metadata[0]["help"],
)
@click.option(
    *Settings.model_fields["api_key"].metadata[0]["click_args"],
    type=str,
    show_envvar=True,
    envvar=Settings.model_fields["api_key"].metadata[0]["envvar"],
    help=Settings.model_fields["api_key"].metadata[0]["help"],
)
@click.version_option()
def cli(ctx: click.Context, **kwargs: str) -> None:
    """
    A TUI client to changedetection.io
    """
    os.environ["PYDANTIC_ERRORS_INCLUDE_URL"] = "0"

    try:
        settings = make_settings(ctx, **kwargs)
    except ValidationError as exception:
        raise click.ClickException(exception.__repr__())

    _ = SETTINGS.set(settings)

    TuiApp().run()


def make_settings(ctx: click.Context, **kwargs: str) -> Settings:
    allowed = set(Settings.model_fields.keys())
    filtered = {key: value for key, value in kwargs.items() if key in allowed and value}
    try:
        return Settings(**filtered)  # pyright: ignore [reportArgumentType]
    except ValidationError as e:
        missing_props = [
            e["loc"][0]
            for e in e.errors()
            if e["loc"] and isinstance(e["loc"][0], str) and e["type"] == "missing"
        ]
        if not missing_props:
            raise

        message = get_url_and_apikey_help().replace("\b\n", "").removeprefix("\n")
        more_help = click.style(
            ctx.command_path + " " + ctx.help_option_names[0], fg="bright_blue"
        )
        message += f"\nSee '{more_help}' for more help.\n\n"
        message += (
            f"Missing: {', '.join(click.style(x, fg='red') for x in missing_props)}"
        )
        message += (
            "\nYou will now be prompted for missing values."
            + "\nValues specified here can be persisted to the config file after launch via settings.\n"
        )
        click.echo(message)

        for missing_prop in missing_props:
            match missing_prop:
                case "url":
                    filtered["url"] = click.prompt(
                        text="Please specify the URL",
                        type=URL(),
                    )
                case "api_key":
                    filtered["api_key"] = click.prompt(
                        text="Please specify the API key (input will be hidden)",
                        hide_input=True,
                    )
                case _:
                    raise click.ClickException(f"Unknown parameter {missing_prop}")
        return Settings(**filtered)  # pyright: ignore [reportArgumentType]


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
