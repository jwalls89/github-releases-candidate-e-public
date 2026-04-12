"""GitHub Actions environment utilities."""

import os


class GitHubActionsHelper:
    """Utilities for detecting and interacting with GitHub Actions."""

    @staticmethod
    def is_running_in_actions() -> bool:
        """Return True if running inside a GitHub Actions workflow."""
        return os.environ.get("GITHUB_ACTIONS") == "true"
