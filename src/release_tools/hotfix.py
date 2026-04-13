"""Hotfix command."""

import os
from pathlib import Path

from release_tools.git import GitHelper
from release_tools.github import GitHubHelper
from release_tools.version import ReleaseVersionHelper


class Hotfix:
    """Command to create a hotfix release branch."""

    def __init__(self, git: GitHelper, github: GitHubHelper, raw_version: str) -> None:
        """Initialise with helpers and the base version string."""
        self._git = git
        self._github = github
        self._base_version = ReleaseVersionHelper.parse(raw_version)

    def run(self) -> None:
        """Orchestrate creating a hotfix release branch."""
        base_version_str = str(self._base_version)
        base_tag = f"v{base_version_str}"

        print(f"Hotfixing {base_tag}...")

        self._github.validate_tag_exists(base_tag)

        hotfix_version = self._git.get_next_hotfix_version(self._base_version)
        hotfix_version_str = str(hotfix_version)
        print(f"Hotfix version: {hotfix_version_str}")

        self._github.validate_release_branch_does_not_exist(hotfix_version_str)

        self._git.create_release_branch(hotfix_version_str, source_ref=base_tag)
        print(f"Created branch release/{hotfix_version_str} from {base_tag}")

        commit_sha = self._git.get_head_sha()
        self._write_summary(base_version_str, hotfix_version_str, commit_sha)

    @staticmethod
    def _write_summary(base_version: str, hotfix_version: str, commit_sha: str) -> None:
        """Write the hotfix summary to step summary or stdout."""
        summary = (
            "## Hotfix Branch Created\n"
            "\n"
            f"- **Hotfixing:** v{base_version}\n"
            f"- **Hotfix version:** {hotfix_version}\n"
            f"- **Branch:** release/{hotfix_version}\n"
            f"- **Branched from:** v{base_version} ({commit_sha})\n"
            "\n"
            "### Next steps\n"
            f"1. Push your fix to `release/{hotfix_version}`"
            " (directly or via PR)\n"
            "2. Run **Tag New RC**"
            f" (from branch `release/{hotfix_version}`)"
            f" with version `{hotfix_version}` to start promotion\n"
            "3. After prod deployment, the merge-back issue"
            " will be created automatically\n"
        )
        print(summary)
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            with Path(summary_path).open("a") as fh:
                fh.write(summary)
