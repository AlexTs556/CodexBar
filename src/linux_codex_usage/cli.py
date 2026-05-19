import argparse
from .cache import UsageCache
from .codexbar_client import CodexBarClient, CodexBarError
from .config import (
    AppConfig,
    create_default_config,
    default_config_path,
    resolve_codexbar_path,
)
from .formatters.json_formatter import format_json
from .formatters.text_formatter import format_text
from .formatters.waybar_formatter import format_waybar
from .models import UsageReport
from .normalize import normalize_usage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linux-codex-usage",
        description="Show normalized AI coding usage data on Linux.",
    )
    subparsers = parser.add_subparsers(dest="command")

    status = subparsers.add_parser("status", help="Fetch and print usage status.")
    status.add_argument(
        "--format",
        choices=("text", "json", "waybar"),
        default="text",
        help="Output format.",
    )
    status.add_argument(
        "--provider",
        action="append",
        dest="providers",
        help="Provider to fetch. Can be passed multiple times.",
    )
    status.add_argument(
        "--codexbar-path",
        default=None,
        help="Path to the codexbar executable.",
    )
    status.add_argument(
        "--source",
        choices=("auto", "web", "cli", "oauth", "api"),
        default=None,
        help="CodexBar provider source strategy.",
    )
    status.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    cost = subparsers.add_parser("cost", help="Fetch and print local cost usage.")
    cost.add_argument(
        "--format",
        choices=("text", "json", "waybar"),
        default="text",
        help="Output format.",
    )
    cost.add_argument(
        "--provider",
        action="append",
        dest="providers",
        help="Provider to fetch. Can be passed multiple times.",
    )
    cost.add_argument(
        "--days",
        type=int,
        default=None,
        help="History window in days.",
    )
    cost.add_argument(
        "--codexbar-path",
        default=None,
        help="Path to the codexbar executable.",
    )
    cost.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )

    config = subparsers.add_parser("config", help="Manage local configuration.")
    config_subparsers = config.add_subparsers(dest="config_command")
    config_subparsers.add_parser("init", help="Create a default config file.")
    config_subparsers.add_parser("check", help="Print the active config.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "status":
        return _status(args)

    if args.command == "cost":
        return _cost(args)

    if args.command == "config":
        return _config(args)

    parser.error("unknown command")
    return 2


def _status(args: argparse.Namespace) -> int:
    config = AppConfig.load()
    providers = args.providers or config.providers
    codexbar_path = resolve_codexbar_path(args.codexbar_path, config)
    cache = UsageCache.default()

    try:
        client = CodexBarClient(codexbar_path, timeout_seconds=config.timeout_seconds)
        report = normalize_usage(client.fetch_usage_json(providers, source=args.source))
        cache.save(report)
    except CodexBarError as exc:
        report = _cached_or_error(cache, str(exc), config.use_cache_on_error)

    _print_report(args.format, report, config, pretty=args.pretty)
    return 0 if not report.error or report.stale else 1


def _cost(args: argparse.Namespace) -> int:
    config = AppConfig.load()
    providers = args.providers or config.providers
    codexbar_path = resolve_codexbar_path(args.codexbar_path, config)
    cache = UsageCache.default()

    try:
        client = CodexBarClient(codexbar_path, timeout_seconds=config.timeout_seconds)
        report = normalize_usage(client.fetch_cost_json(providers, days=args.days))
        cache.save(report)
    except CodexBarError as exc:
        report = _cached_or_error(cache, str(exc), config.use_cache_on_error)

    _print_report(args.format, report, config, pretty=args.pretty)
    return 0 if not report.error or report.stale else 1


def _cached_or_error(
    cache: UsageCache,
    error: str,
    use_cache_on_error: bool,
) -> UsageReport:
    if use_cache_on_error:
        cached = cache.load()
        if cached:
            cached.stale = True
            cached.error = error
            return cached

    return UsageReport(providers=[], error=error)


def _print_report(
    output_format: str,
    report: UsageReport,
    config: AppConfig,
    pretty: bool = False,
) -> None:
    if output_format == "json":
        print(format_json(report, pretty=pretty))
        return
    if output_format == "waybar":
        print(
            format_waybar(
                report,
                warning_threshold=config.warning_threshold,
                critical_threshold=config.critical_threshold,
            )
        )
        return
    print(format_text(report))


def _config(args: argparse.Namespace) -> int:
    if args.config_command == "init":
        path = create_default_config()
        print(path)
        return 0

    if args.config_command == "check":
        config = AppConfig.load()
        print(config.to_toml(), end="")
        print(f"# path = {default_config_path()}")
        return 0

    raise SystemExit("config subcommand required")
