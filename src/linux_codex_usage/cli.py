import argparse


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

    parser.error("This command is not implemented yet.")
    return 2

