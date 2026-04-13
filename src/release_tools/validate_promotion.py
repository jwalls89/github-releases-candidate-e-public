"""Validate promotion command."""

import os
from pathlib import Path

from release_tools.github import GitHubHelper
from release_tools.version import ReleaseVersionHelper


class ValidatePromotion:
    """Command to validate an RC tag for promotion."""

    def __init__(self, github: GitHubHelper, raw_version: str) -> None:
        """Initialise with a GitHub helper and RC tag string."""
        self._github = github
        self._raw_version = raw_version

    def run(self) -> str:
        """Validate the RC tag and return the normalised tag name.

        Checks that:
        1. The version is a valid RC tag (e.g., v1.2.0-rc.1)
        2. The tag exists on GitHub
        3. The corresponding release branch exists

        Returns the normalised tag name (e.g., ``v1.2.0-rc.1``).

        Raises:
            ValueError: If any validation check fails.

        """
        version = ReleaseVersionHelper.parse_rc(self._raw_version)

        tag_name = f"v{version}"
        print(f"Validating RC tag {tag_name}...")

        self._github.validate_tag_exists(tag_name)
        print(f"  Tag {tag_name} exists")

        base_version = f"{version.major}.{version.minor}.{version.patch}"
        self._github.validate_release_branch_exists(base_version)
        print(f"  Release branch release/{base_version} exists")

        self._write_output(tag_name)
        return tag_name

    @staticmethod
    def _write_output(tag_name: str) -> None:
        """Write the validated version to GITHUB_OUTPUT or stdout."""
        output_path = os.environ.get("GITHUB_OUTPUT")
        if output_path:
            with Path(output_path).open("a") as fh:
                fh.write(f"version={tag_name}\n")
        else:
            print(f"version={tag_name}")
