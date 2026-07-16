class RepoNotIngestedError(Exception):
    """Raised when a KnowledgeBase is requested for a repo with no (current-
    schema) persisted artifacts - never ingested, or ingested before this
    knowledge-layer version existed.
    """

    def __init__(self, repo_name: str) -> None:
        super().__init__(
            f"Repo '{repo_name}' hasn't been ingested (or has no artifacts for the current "
            f"knowledge schema) - run scripts/ingest_repo.py to (re-)ingest it."
        )
        self.repo_name = repo_name


class IncompatibleSchemaError(Exception):
    """Raised when a repo's persisted schema_version doesn't match what this
    build expects, so callers get a clear "re-ingest" signal instead of a
    confusing failure deep inside JSON deserialization.
    """

    def __init__(
        self, repo_name: str, found_version: int, expected_version: int
    ) -> None:
        super().__init__(
            f"Repo '{repo_name}' was ingested with knowledge schema version {found_version}, "
            f"but this build expects version {expected_version} - re-ingest with "
            f"scripts/ingest_repo.py to regenerate compatible artifacts."
        )
        self.repo_name = repo_name
        self.found_version = found_version
        self.expected_version = expected_version
