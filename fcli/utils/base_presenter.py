from rich.console import Console

from ..core.config import config

console = Console()


class BasePresenter:
    _display_cache: dict[str, dict[str, str]] | None = None

    @classmethod
    def _get_display_maps(cls) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
        if cls._display_cache is None:
            d = config.display
            cls._display_cache = {
                "market": d.market_map if d.market_map else {},
                "type": d.type_map if d.type_map else {},
                "color": d.type_color if d.type_color else {},
            }
        return cls._display_cache["market"], cls._display_cache["type"], cls._display_cache["color"]

    @staticmethod
    def _get_market_display(market_value: str) -> str:
        market_map, _, _ = BasePresenter._get_display_maps()
        return market_map.get(market_value, market_value)

    @staticmethod
    def _get_type_display(type_value: str) -> tuple[str, str]:
        _, type_map, type_color = BasePresenter._get_display_maps()
        type_cn = type_map.get(type_value, type_value)
        color = type_color.get(type_value, "white")
        return type_cn, color

    @staticmethod
    def _format_change(val: float | None) -> str:
        if val is None:
            return "-"
        rounded = round(val, 1)
        if rounded == 0:
            return "0.0"
        if rounded > 0:
            return f"[bold red]+{rounded:.1f}[/bold red]"
        return f"[bold green]{rounded:.1f}[/bold green]"

    @staticmethod
    def _format_change_compact(val: float | None) -> str:
        if val is None:
            return "[dim]-[/dim]"
        rounded = round(val, 1)
        if rounded == 0:
            return "0.0"
        if rounded > 0:
            return f"[red]+{rounded:.1f}[/red]"
        return f"[green]{rounded:.1f}[/green]"

    @staticmethod
    def print_success(message: str):
        console.print(f"[green]{message}[/green]")

    @staticmethod
    def print_error(message: str):
        console.print(f"[red]{message}[/red]")

    @staticmethod
    def print_warning(message: str):
        console.print(f"[yellow]{message}[/yellow]")

    @staticmethod
    def print_info(message: str):
        console.print(f"[dim]{message}[/dim]")

    @staticmethod
    def status(message: str):
        return console.status(f"[bold green]{message}[/bold green]")
