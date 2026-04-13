"""Tag RC command."""

import os
from pathlib import Path

from release_tools.git import GitHelper
from release_tools.github import GitHubHelper
from release_tools.version import ReleaseVersionHelper


class TagRC:
    """Command to tag a new release candidate."""

    def __init__(self, git: GitHelper, github: GitHubHelper, raw_version: str) -> None:
        """Initialise with helpers and the release version string."""
        self._git = git
        self._github = github
        self._version = ReleaseVersionHelper.parse(raw_version)

    def run(self) -> None:
        """Orchestrate tagging a new release candidate."""
        version_str = str(self._version)
        branch = f"release/{version_str}"

        self._github.validate_release_branch_exists(version_str)
        self._github.validate_not_finalised(version_str)

        rc_number = self._git.get_next_rc_number(version_str)
        print(f"Next RC number: {rc_number}")

        tag_name = self._git.create_rc_tag(version_str, rc_number=rc_number)
        print(f"Created tag {tag_name}")

        url = self._github.create_prerelease(tag_name, branch)
        print(f"Pre-release published: {url}")

        self._github.trigger_promotion(branch, tag_name)
        print(f"Promotion pipeline triggered for {tag_name}")

        commit_sha = self._git.get_head_sha()
        self._write_summary(version_str, tag_name, commit_sha)

    @staticmethod
    def _write_summary(version: str, tag_name: str, commit_sha: str) -> None:
        """Write the tag-rc summary to step summary or stdout."""
        summary = (
            "## New RC Tagged\n"
            "\n"
            f"- **Tag:** {tag_name}\n"
            f"- **Pre-release:** {tag_name} (published)\n"
            f"- **Branch:** release/{version}\n"
            f"- **Commit:** {commit_sha}\n"
            "\n"
            "### Next steps\n"
            "1. The **Promote** workflow has been triggered"
            " automatically — check the Actions tab\n"
            "2. Any previous promote run for this release"
            " will be cancelled automatically\n"
            "3. Test will deploy automatically."
            " Approve **preprod** and **prod** when prompted\n"
            f"4. If another problem is found, fix it on `release/{version}`"
            " and run **Tag New RC** again\n"
            "5. Check the **Releases** page"
            " — the new pre-release is visible\n"
        )
        print(summary)
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            with Path(summary_path).open("a") as fh:
                fh.write(summary)
