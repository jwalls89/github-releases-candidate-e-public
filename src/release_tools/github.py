"""GitHub API operations for the release pipeline."""

from github import UnknownObjectException
from github.GithubObject import NotSet
from github.Repository import Repository


class GitHubHelper:
    """Wrapper around a GitHub repository for release operations."""

    def __init__(self, repo: Repository) -> None:
        """Initialise with a PyGithub repository."""
        self._repo = repo

    def create_prerelease(
        self,
        tag_name: str,
        target_branch: str,
        previous_tag: str | None = None,
    ) -> str:
        """Create a GitHub pre-release with auto-generated notes.

        Returns the URL of the created release.
        """
        notes = self._repo.generate_release_notes(
            tag_name=tag_name,
            target_commitish=target_branch,
            previous_tag_name=previous_tag or NotSet,
        )
        release = self._repo.create_git_release(
            tag=tag_name,
            name=tag_name,
            message=notes.body,
            target_commitish=target_branch,
            prerelease=True,
        )
        return release.html_url

    def create_rc_tag(
        self, version: str, target_branch: str, rc_number: int = 1
    ) -> str:
        """Create a lightweight RC tag via the GitHub API.

        Resolves *target_branch* to its tip commit and creates a tag
        ref pointing at it.  Returns the tag name.
        """
        tag_name = f"v{version}-rc.{rc_number}"
        branch_ref = self._repo.get_branch(target_branch)
        commit_sha = branch_ref.commit.sha
        self._repo.create_git_ref(ref=f"refs/tags/{tag_name}", sha=commit_sha)
        return tag_name

    def trigger_promotion(self, branch: str, tag_name: str) -> None:
        """Trigger the promote workflow on the given branch."""
        workflow = self._repo.get_workflow("promote.yml")
        workflow.create_dispatch(
            ref=branch,
            inputs={"version": tag_name},
        )

    def validate_tag_exists(self, tag_name: str) -> None:
        """Raise if the given tag does not exist on GitHub.

        Raises:
            ValueError: If the tag is not found.

        """
        try:
            self._repo.get_git_ref(f"tags/{tag_name}")
        except UnknownObjectException:
            msg = f"Tag {tag_name} does not exist"
            raise ValueError(msg) from None

    def validate_release_branch_exists(self, version: str) -> None:
        """Raise if the release branch for the given version does not exist.

        Raises:
            ValueError: If ``release/{version}`` branch is not found.

        """
        branch_name = f"release/{version}"
        try:
            self._repo.get_branch(branch_name)
        except UnknownObjectException:
            msg = (
                f"No release branch {branch_name} found."
                " Tags must belong to a release branch."
            )
            raise ValueError(msg) from None

    def validate_not_finalised(self, version: str) -> None:
        """Raise if the given version already has a final release tag.

        Raises:
            ValueError: If the stable tag ``v{version}`` exists.

        """
        try:
            self._repo.get_git_ref(f"tags/v{version}")
        except UnknownObjectException:
            return
        msg = (
            f"Release v{version} is already finalised."
            " Use the Hotfix workflow to create a patch release instead."
        )
        raise ValueError(msg)

    def validate_release_branch_does_not_exist(self, version: str) -> None:
        """Raise if the release branch for the given version already exists.

        Raises:
            ValueError: If ``release/{version}`` branch is found.

        """
        branch_name = f"release/{version}"
        try:
            self._repo.get_branch(branch_name)
        except UnknownObjectException:
            return
        msg = f"Branch {branch_name} already exists"
        raise ValueError(msg)

    def create_final_tag(self, tag_name: str, source_tag: str, message: str) -> bool:
        """Create an annotated release tag via the GitHub API.

        Resolves *source_tag* to a commit SHA on the remote and creates
        an annotated tag object plus its ref.  No local clone state is
        needed.

        Returns ``True`` if a new tag was created, ``False`` if it
        already existed.

        Raises:
            ValueError: If *source_tag* does not exist.

        """
        try:
            self._repo.get_git_ref(f"tags/{tag_name}")
        except UnknownObjectException:
            pass
        else:
            return False

        try:
            source_ref = self._repo.get_git_ref(f"tags/{source_tag}")
        except UnknownObjectException:
            msg = f"Source tag {source_tag} not found on GitHub"
            raise ValueError(msg) from None

        source_sha = source_ref.object.sha
        # Dereference if annotated tag (points to tag object, not commit)
        if source_ref.object.type == "tag":
            tag_obj = self._repo.get_git_tag(source_sha)
            source_sha = tag_obj.object.sha

        git_tag = self._repo.create_git_tag(
            tag=tag_name,
            message=message,
            object=source_sha,
            type="commit",
        )
        self._repo.create_git_ref(ref=f"refs/tags/{tag_name}", sha=git_tag.sha)
        return True

    def get_mergeback_count(self, branch: str) -> int:
        """Count commits on *branch* that are not on ``main``.

        Uses the GitHub compare API so no local history is needed.
        """
        comparison = self._repo.compare("main", branch)
        return comparison.ahead_by

    def find_previous_stable_release(self, exclude_tag: str) -> str | None:
        """Find the previous stable release tag, excluding *exclude_tag*.

        Returns the tag name of the most recent non-draft,
        non-pre-release release, or ``None`` if there is none.
        """
        for release in self._repo.get_releases():
            if release.draft or release.prerelease:
                continue
            if release.tag_name == exclude_tag:
                continue
            return release.tag_name
        return None

    def publish_stable_release(self, tag_name: str, previous_tag: str | None) -> None:
        """Create the final stable GitHub Release for *tag_name*.

        If a draft release already exists for the tag it is deleted
        first. If a published release already exists the method
        returns without making changes.
        """
        try:
            existing = self._repo.get_release(tag_name)
            if existing.draft:
                existing.delete_release()
            else:
                return
        except UnknownObjectException:
            pass

        notes = self._repo.generate_release_notes(
            tag_name=tag_name,
            previous_tag_name=previous_tag or NotSet,
        )
        self._repo.create_git_release(
            tag=tag_name,
            name=tag_name,
            message=notes.body,
            make_latest="true",
        )

    def annotate_release_with_mergeback(
        self, tag_name: str, branch: str, ahead_count: int
    ) -> None:
        """Append a merge-back warning to the release body."""
        release = self._repo.get_release(tag_name)
        merge_note = (
            "\n\n---\n\n"
            "\u26a0\ufe0f **Merge-back required:** This release has"
            f" {ahead_count} commit(s) on `{branch}` that are not on"
            " `main`. See the merge-back issue for instructions."
        )
        release.update_release(
            name=release.title,
            message=release.body + merge_note,
        )

    def create_mergeback_issue(
        self, tag_name: str, branch: str, ahead_count: int
    ) -> str:
        """Create a merge-back issue and return its URL."""
        merge_version = tag_name.removeprefix("v")
        repo_name = self._repo.full_name
        body = (
            f"Release **{tag_name}** has {ahead_count} commit(s) on"
            f" `{branch}` that need merging back to `main`.\n\n"
            "## Steps\n\n"
            "```bash\n"
            "git fetch origin\n"
            "git checkout main\n"
            "git pull origin main\n"
            f"git checkout -b merge-back/{merge_version}\n"
            f"git merge origin/{branch}\n"
            "# Resolve conflicts if any\n"
            f"git push origin merge-back/{merge_version}\n"
            "```\n\n"
            f"Then open a PR from `merge-back/{merge_version}` to `main`:\n\n"
            f"https://github.com/{repo_name}"
            f"/compare/main...merge-back/{merge_version}?expand=1\n\n"
            "Close this issue once the PR is merged."
        )
        issue = self._repo.create_issue(
            title=f"Merge back: {tag_name}",
            body=body,
        )
        return issue.html_url
