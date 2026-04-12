"""GitHub API operations for the release pipeline."""

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

    def trigger_promotion(self, branch: str, tag_name: str) -> None:
        """Trigger the promote workflow on the given branch."""
        workflow = self._repo.get_workflow("promote.yml")
        workflow.create_dispatch(
            ref=branch,
            inputs={"version": tag_name},
        )
