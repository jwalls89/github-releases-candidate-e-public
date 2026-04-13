"""Cut release command."""

import os
from pathlib import Path

from release_tools.git import GitHelper
from release_tools.github import GitHubHelper
from release_tools.version import ReleaseVersionHelper


class CutRelease:
    """Command to cut a new release candidate."""

    def __init__(self, git: GitHelper, github: GitHubHelper, raw_version: str) -> None:
        """Initialise with a git helper, GitHub helper, and version string."""
        self._git = git
        self._github = github
        self._raw_version = raw_version

    def run(self) -> None:
        """Orchestrate cutting a new release candidate."""
        version = ReleaseVersionHelper.parse(self._raw_version)

        latest = self._git.get_latest_stable_tag()
        ReleaseVersionHelper.check_version_is_higher(version, latest)

        inflight = self._git.get_inflight_release()
        if inflight:
            msg = (
                f"Release {inflight} is still in-flight"
                " (no final tag). Only one release at a time."
            )
            raise RuntimeError(msg)

        version_str = str(version)
        branch = f"release/{version_str}"

        print(f"Creating release branch {branch}...")
        self._git.create_release_branch(version_str)

        print(f"Creating RC tag v{version_str}-rc.1...")
        tag_name, commit_sha = self._github.create_rc_tag(version_str, branch)

        previous_tag = f"v{latest}" if latest else None
        print(f"Publishing pre-release {tag_name}...")
        self._github.create_prerelease(tag_name, branch, previous_tag)

        print("Triggering promotion pipeline...")
        self._github.trigger_promotion(branch, tag_name)

        self._write_summary(version_str, tag_name, commit_sha)

    @staticmethod
    def _write_summary(version: str, tag_name: str, commit_sha: str) -> None:
        """Write the cut-release summary to step summary or stdout."""
        summary = (
            "## Release Cut\n"
            "\n"
            f"- **Branch:** release/{version}\n"
            f"- **Tag:** {tag_name}\n"
            f"- **Pre-release:** {tag_name} (visible on Releases page)\n"
            f"- **Commit:** {commit_sha}\n"
            "\n"
            "### Next steps\n"
            "1. The **Promote** workflow has been triggered"
            " automatically — check the Actions tab\n"
            "2. Test will deploy automatically."
            " Approve **preprod** and **prod** when prompted\n"
            f"3. If a problem is found, fix it on `release/{version}`"
            f" and run **Tag New RC** (from that branch)"
            f" with version `{version}`\n"
            "4. Check the **Releases** page to see the"
            " draft and pre-release\n"
        )
        print(summary)
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            with Path(summary_path).open("a") as fh:
                fh.write(summary)
