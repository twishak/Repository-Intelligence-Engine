import argparse
import logging

from rich.logging import RichHandler

from codebase_agent.interface import ask_once, list_repos, run_repl


def main() -> None:
    args = _parse_args()
    logging.basicConfig(
        level=logging.WARNING,
        format="%(message)s",
        handlers=[RichHandler(show_path=False)],
    )

    if args.list:
        list_repos()
        return

    if not args.repo:
        raise SystemExit(
            "Missing repo name. Usage: python scripts/ask.py <repo> [-q QUESTION]"
        )

    if args.question:
        ask_once(args.repo, args.question)
    else:
        run_repl(args.repo)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ask natural-language questions about an ingested repository."
    )
    parser.add_argument("repo", nargs="?", help="Name of the ingested repository.")
    parser.add_argument(
        "-q",
        "--question",
        help="Ask a single question and exit, instead of starting a REPL.",
    )
    parser.add_argument(
        "--list", action="store_true", help="List ingested repositories and exit."
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
