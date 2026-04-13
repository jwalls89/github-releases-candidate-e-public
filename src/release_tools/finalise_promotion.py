"""Finalise promotion command."""

import os
from pathlib import Path

from release_tools.git import GitHelper
from release_tools.github import GitHubHelper
from release_tools.version import ReleaseVersionHelper


class FinalisePromotion:
    """Command to finalise a promoted RC into a stable release."""

    def __init__(self, git: GitHelper, github: GitHubHelper, raw_version: str) -> None:
        """Initialise with helpers and the RC tag string."""
        self._git = git
        self._github = github
        self._raw_version = raw_version

    def run(self) -> None:
        """Orchestrate finalising a promoted RC into a stable release.

        1. Parse the RC tag and derive the final version
        2. Create the annotated final tag
        3. Find the previous stable release for changelog
        4. Publish the stable GitHub Release
        5. Detect merge-back need and create issue if required
        6. Write a step summary
        """
        version = ReleaseVersionHelper.parse_rc(self._raw_version)
        rc_tag = f"v{version}"
        base_version = f"{version.major}.{version.minor}.{version.patch}"
        final_tag = f"v{base_version}"
        branch = f"release/{base_version}"

        print(f"Finalising {rc_tag} as {final_tag}...")

        created = self._github.create_final_tag(
            final_tag, rc_tag, message=f"Release {final_tag}"
        )
        if created:
            print(f"  Created tag {final_tag}")
        else:
            print(f"  Tag {final_tag} already exists — skipped")

        previous_tag = self._github.find_previous_stable_release(final_tag)
        if previous_tag:
            print(f"  Previous stable release: {previous_tag}")
        else:
            print("  No previous stable release found")

        self._github.publish_stable_release(final_tag, previous_tag)
        print(f"  Published release {final_tag}")

        ahead_count = self._github.get_mergeback_count(branch)

        if ahead_count > 0:
            print(
                f"  Release branch is {ahead_count} commit(s)"
                " ahead of main — merge-back required"
            )
            self._github.annotate_release_with_mergeback(final_tag, branch, ahead_count)
            self._github.create_mergeback_issue(final_tag, branch, ahead_count)
            print("  Created merge-back issue")
        else:
            print("  No merge-back needed")

        self._write_summary(final_tag, rc_tag, ahead_count, branch)

    @staticmethod
    def _write_summary(
        final_tag: str,
        rc_tag: str,
        ahead_count: int,
        branch: str,
    ) -> None:
        """Write the finalisation summary to step summary or stdout."""
        summary = (
            "## Release Finalised\n"
            "\n"
            f"- **Release:** {final_tag}"
            " (stable \u2014 visible on Releases page)\n"
            f"- **From RC:** {rc_tag}\n"
            "\n"
            "### Releases page now shows\n"
            f"- **{final_tag}** \u2014 Latest (stable release)\n"
            "- Previous pre-releases show the RC history\n"
        )
        if ahead_count > 0:
            summary += (
                "\n"
                f"\u26a0\ufe0f **Merge-back required** \u2014"
                f" {ahead_count} commit(s) on `{branch}` need"
                " merging to main. See issue.\n"
            )
        print(summary)
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            with Path(summary_path).open("a") as fh:
                fh.write(summary)
