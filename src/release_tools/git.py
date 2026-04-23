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

    @staticmethod
    def _parse_remote_ref_names(ls_remote_output: str, prefix: str) -> set[str]:
        r"""Parse ``git ls-remote`` output into a set of ref names.

        Each line of *ls_remote_output* has the format ``<sha>\t<refname>``.
        Only refs starting with *prefix* are included; the prefix is
        stripped from each name.  Annotated-tag dereference entries
        (ending with ``^{}``) are ignored.
        """
        ref_names: set[str] = set()
        for line in ls_remote_output.splitlines():
            if not line or "\t" not in line:
                continue
            _sha, raw_ref = line.split("\t", maxsplit=1)
            if raw_ref.endswith("^{}"):
                continue
            if raw_ref.startswith(prefix):
                ref_names.add(raw_ref.removeprefix(prefix))
        return ref_names

    @staticmethod
    def _resolve_remote_tag_sha(ls_remote_output: str, tag_name: str) -> str | None:
        r"""Return the commit SHA for *tag_name* from ``ls-remote`` output.

        For annotated tags, prefers the dereferenced ``^{}`` line
        (the actual commit SHA).  For lightweight tags, returns the
        only SHA present.  Returns ``None`` if the tag is not found.
        """
        tag_ref = f"refs/tags/{tag_name}"
        deref_ref = f"{tag_ref}^{{}}"
        tag_sha: str | None = None
        for line in ls_remote_output.splitlines():
            if not line or "\t" not in line:
                continue
            sha, raw_ref = line.split("\t", maxsplit=1)
            if raw_ref == deref_ref:
                return sha
            if raw_ref == tag_ref:
                tag_sha = sha
        return tag_sha

    def get_latest_stable_tag(self) -> Version | None:
        """Return the highest stable semver tag, or ``None``.

        Queries origin directly via ``ls-remote`` so behaviour is
        consistent regardless of local fetch state.  Only tags matching
        ``vMAJOR.MINOR.PATCH`` (no pre-release suffix) are considered.
        """
        ls_remote_output = self._repo.git.ls_remote("--tags", "origin")
        remote_tag_names = self._parse_remote_ref_names(
            ls_remote_output, prefix="refs/tags/"
        )

        versions: list[Version] = []
        for tag_name in remote_tag_names:
            match = self._STABLE_TAG_PATTERN.match(tag_name)
            if match:
                versions.append(Version.parse(match.group(1)))

        if not versions:
            return None

        return max(versions)

    def get_inflight_release(self) -> str | None:
        """Return the version string of an in-flight release, or ``None``.

        A release is in-flight when a ``release/X.Y.Z`` branch exists
        on origin but the corresponding stable tag ``vX.Y.Z`` has not
        been created yet.  Both checks query origin via ``ls-remote``.
        """
        remote_tag_output = self._repo.git.ls_remote("--tags", "origin")
        remote_tag_names = self._parse_remote_ref_names(
            remote_tag_output, prefix="refs/tags/"
        )
        stable_tags = {
            name for name in remote_tag_names if self._STABLE_TAG_PATTERN.match(name)
        }

        remote_branch_output = self._repo.git.ls_remote("--heads", "origin")
        remote_branch_names = self._parse_remote_ref_names(
            remote_branch_output, prefix="refs/heads/"
        )

        for branch_name in remote_branch_names:
            if not branch_name.startswith("release/"):
                continue
            version = branch_name.removeprefix("release/")
            if f"v{version}" not in stable_tags:
                return version

        return None

    def get_next_rc_number(self, version: str) -> int:
        """Return the next RC number for the given version.

        Queries origin via ``ls-remote`` to find existing RC tags
        for *version* and returns the next sequential number.
        Returns ``1`` if no RC tags exist yet.
        """
        ls_remote_output = self._repo.git.ls_remote("--tags", "origin")
        remote_tag_names = self._parse_remote_ref_names(
            ls_remote_output, prefix="refs/tags/"
        )

        rc_pattern = re.compile(rf"^v{re.escape(version)}-rc\.(\d+)$")
        rc_numbers: list[int] = []
        for tag_name in remote_tag_names:
            match = rc_pattern.match(tag_name)
            if match:
                rc_numbers.append(int(match.group(1)))

        if not rc_numbers:
            return 1

        return max(rc_numbers) + 1

    def get_next_hotfix_version(self, base_version: Version) -> Version:
        """Return the next available hotfix version for *base_version*.

        Scans remote tags and release branches to find the highest
        patch number in use for the same ``major.minor`` series.
        Tags (both stable and RC) and ``release/`` branches all
        count as "used", then returns the next patch version.
        """
        ls_remote_tags = self._repo.git.ls_remote("--tags", "origin")
        remote_tag_names = self._parse_remote_ref_names(
            ls_remote_tags, prefix="refs/tags/"
        )

        ls_remote_heads = self._repo.git.ls_remote("--heads", "origin")
        remote_branch_names = self._parse_remote_ref_names(
            ls_remote_heads, prefix="refs/heads/"
        )

        tag_prefix = f"v{base_version.major}.{base_version.minor}."
        tag_pattern = re.compile(
            rf"^v{base_version.major}\.{base_version.minor}\.(\d+)(?:-rc\.\d+)?$"
        )
        branch_prefix = f"release/{base_version.major}.{base_version.minor}."

        highest_patch = base_version.patch
        for tag_name in remote_tag_names:
            if not tag_name.startswith(tag_prefix):
                continue
            match = tag_pattern.match(tag_name)
            if match:
                patch = int(match.group(1))
                highest_patch = max(highest_patch, patch)

        for branch_name in remote_branch_names:
            if not branch_name.startswith(branch_prefix):
                continue
            patch_str = branch_name.removeprefix(branch_prefix)
            if patch_str.isdigit():
                highest_patch = max(highest_patch, int(patch_str))

        return Version(base_version.major, base_version.minor, highest_patch + 1)

    def get_repo_name(self) -> str:
        """Derive the GitHub ``owner/repo`` name from the origin URL."""
        origin_url = self._repo.remotes.origin.url
        # Handle SSH (git@github.com:owner/repo.git) and
        # HTTPS (https://github.com/owner/repo.git)
        cleaned = origin_url.removesuffix(".git")
        if ":" in cleaned and not cleaned.startswith("http"):
            return cleaned.split(":")[-1]
        return "/".join(cleaned.split("/")[-2:])
