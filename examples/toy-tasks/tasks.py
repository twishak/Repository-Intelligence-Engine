"""Minimal in-memory task manager used as a demo repo."""

from utils import format_task_line, slugify


class TaskManager:
    """Tracks tasks by slug and whether they're complete."""

    def __init__(self) -> None:
        self._tasks: dict[str, tuple[str, bool]] = {}

    def add_task(self, title: str) -> str:
        """Add a new task and return its slug."""
        slug = slugify(title)
        self._tasks[slug] = (title, False)
        return slug

    def complete_task(self, slug: str) -> None:
        """Mark a task complete. Raises KeyError if it doesn't exist."""
        title, _ = self._tasks[slug]
        self._tasks[slug] = (title, True)

    def render(self) -> list[str]:
        """Render every task as a checklist line, in insertion order."""
        return [format_task_line(title, done) for title, done in self._tasks.values()]
