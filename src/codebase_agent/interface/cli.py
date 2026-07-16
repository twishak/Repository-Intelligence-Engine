from rich.console import Console

from codebase_agent.graph import answer_question
from codebase_agent.llm import GroqClient
from codebase_agent.retrieval import CodeRetriever
from codebase_agent.storage import CodeVectorStore

_EXIT_COMMANDS = {"exit", "quit", "q"}


def ask_once(repo_name: str, question: str, console: Console | None = None) -> str:
    console = console or Console()
    _require_ingested(repo_name)

    answer = answer_question(repo_name, question)
    console.print(answer)
    return answer


def run_repl(repo_name: str, console: Console | None = None) -> None:
    console = console or Console()
    _require_ingested(repo_name)
    console.print(
        f"Ask questions about [bold]{repo_name}[/bold] (type 'exit' to quit)\n"
    )

    # Reused across turns so the embedding model and Groq client are only
    # initialized once per session, not on every question.
    llm = GroqClient()
    retriever = CodeRetriever()

    while True:
        try:
            question = console.input("[bold cyan]> [/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        if not question:
            continue
        if question.lower() in _EXIT_COMMANDS:
            break

        with console.status("thinking..."):
            answer = answer_question(repo_name, question, llm=llm, retriever=retriever)
        console.print(answer)
        console.print()


def list_repos(console: Console | None = None) -> list[str]:
    console = console or Console()
    repos = CodeVectorStore().list_repos()
    if not repos:
        console.print("No repositories ingested yet. Run scripts/ingest_repo.py first.")
    for repo in repos:
        console.print(repo)
    return repos


def _require_ingested(repo_name: str) -> None:
    if not CodeVectorStore().has_collection(repo_name):
        raise SystemExit(
            f"Repo '{repo_name}' hasn't been ingested yet. "
            f"Run 'python scripts/ingest_repo.py <path-or-url>' first, "
            f"or pass --list to see available repos."
        )
