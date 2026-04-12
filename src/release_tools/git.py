"""Git operations for the release pipeline."""

import re

from git import Repo
from semver import Version


class GitHelper:
    """Wrapper around a git repo for release operations."""

    _STABLE_TAG_PATTERN = re.compile(r"^v([0-9]+\.[0-9]+\.[0-9]+)$")

    def __init__(self, repo: Repo) -> None:
        """Initialise with a git repo."""
        self._repo = repo

    def get_latest_stable_tag(self) -> Version | None:
        """Return the highest stable semver tag, or ``None``.

        Only tags matching ``vMAJOR.MINOR.PATCH`` (no pre-release
        suffix) are considered.
        """
        versions: list[Version] = []

        for tag in self._repo.tags:
            match = self._STABLE_TAG_PATTERN.match(tag.name)
            if match:
                versions.append(Version.parse(match.group(1)))

        if not versions:
            return None

        return max(versions)

    def get_inflight_release(self) -> str | None:
        """Return the version string of an in-flight release, or ``None``.

        A release is in-flight when a ``release/X.Y.Z`` branch exists
        on origin but the corresponding stable tag ``vX.Y.Z`` has not
        been created yet.
        """
        stable_tags = {
            tag.name
            for tag in self._repo.tags
            if self._STABLE_TAG_PATTERN.match(tag.name)
        }

        for ref in self._repo.remotes.origin.refs:
            if not ref.name.startswith("origin/release/"):
                continue
            version = ref.name.removeprefix("origin/release/")
            if f"v{version}" not in stable_tags:
                return version

        return None

    def create_release_branch(self, version: str) -> None:
        """Create a ``release/{version}`` branch and push it to origin."""
        branch = self._repo.create_head(f"release/{version}")
        self._repo.remotes.origin.push(branch.name)

    def create_rc_tag(self, version: str, rc_number: int = 1) -> str:
        """Create an RC tag and push it to origin.

        Returns the tag name.
        """
        tag_name = f"v{version}-rc.{rc_number}"
        self._repo.create_tag(tag_name)
        self._repo.remotes.origin.push(tag_name)
        return tag_name

    def get_repo_name(self) -> str:
        """Derive the GitHub ``owner/repo`` name from the origin URL."""
        origin_url = self._repo.remotes.origin.url
        # Handle SSH (git@github.com:owner/repo.git) and
        # HTTPS (https://github.com/owner/repo.git)
        cleaned = origin_url.removesuffix(".git")
        if ":" in cleaned and not cleaned.startswith("http"):
            return cleaned.split(":")[-1]
        return "/".join(cleaned.split("/")[-2:])

    def get_head_sha(self) -> str:
        """Return the SHA of the current HEAD commit."""
        return self._repo.head.commit.hexsha
