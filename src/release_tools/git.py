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

        Scans all remote tags in a single ``ls-remote`` call to find
        the highest patch number in use for the same ``major.minor``
        series (counting both stable tags and RC tags as "used"),
        then returns the next patch version.
        """
        ls_remote_output = self._repo.git.ls_remote("--tags", "origin")
        remote_tag_names = self._parse_remote_ref_names(
            ls_remote_output, prefix="refs/tags/"
        )

        version_prefix = f"v{base_version.major}.{base_version.minor}."
        patch_pattern = re.compile(
            rf"^v{base_version.major}\.{base_version.minor}\.(\d+)(?:-rc\.\d+)?$"
        )

        highest_patch = base_version.patch
        for tag_name in remote_tag_names:
            if not tag_name.startswith(version_prefix):
                continue
            match = patch_pattern.match(tag_name)
            if match:
                patch = int(match.group(1))
                highest_patch = max(highest_patch, patch)

        return Version(base_version.major, base_version.minor, highest_patch + 1)

    def create_release_branch(
        self, version: str, source_ref: str | None = None
    ) -> None:
        """Create a ``release/{version}`` branch and push it to origin.

        If *source_ref* is provided, it is resolved to a commit SHA
        via ``ls-remote`` so it does not need to exist in the local
        clone.  This is used for hotfixes that branch from a stable
        tag.

        Raises:
            ValueError: If *source_ref* is not found on origin.

        """
        if source_ref:
            ls_remote_output = self._repo.git.ls_remote("--tags", "origin")
            source_sha = self._resolve_remote_tag_sha(ls_remote_output, source_ref)
            if not source_sha:
                msg = f"Source tag {source_ref} not found on origin"
                raise ValueError(msg)
            branch = self._repo.create_head(f"release/{version}", commit=source_sha)
        else:
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

    def configure_identity(self, name: str, email: str) -> None:
        """Set the git user name and email for the repo."""
        with self._repo.config_writer() as config:
            config.set_value("user", "name", name)
            config.set_value("user", "email", email)

    def create_final_tag(self, tag_name: str, source_ref: str) -> bool:
        """Create an annotated release tag at *source_ref* and push it.

        Resolves *source_ref* to a commit SHA via ``ls-remote`` so the
        tag does not need to exist in the local clone.  Returns ``True``
        if a new tag was created, ``False`` if it already existed on
        origin.

        Raises:
            ValueError: If *source_ref* is not found on origin.

        """
        ls_remote_output = self._repo.git.ls_remote("--tags", "origin")
        remote_tag_names = self._parse_remote_ref_names(
            ls_remote_output, prefix="refs/tags/"
        )

        if tag_name in remote_tag_names:
            return False

        source_sha = self._resolve_remote_tag_sha(ls_remote_output, source_ref)
        if not source_sha:
            msg = f"Source tag {source_ref} not found on origin"
            raise ValueError(msg)

        self._repo.create_tag(tag_name, ref=source_sha, message=f"Release {tag_name}")
        self._repo.remotes.origin.push(tag_name)
        return True
