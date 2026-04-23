"""Release invoke tasks."""

import os

from dotenv import load_dotenv
from git import Repo
from github import Github
from invoke import Context, Exit, task

from release_tools.cut_release import CutRelease
from release_tools.finalise_promotion import FinalisePromotion
from release_tools.git import GitHelper
from release_tools.github import GitHubHelper
from release_tools.github_actions import GitHubActionsHelper
from release_tools.hotfix import Hotfix
from release_tools.tag_rc import TagRC
from release_tools.validate_promotion import ValidatePromotion


@task(
    help={
        "version": "Release version (e.g., 1.2.0 or v1.2.0)",
        "commit-id": (
            "Optional 40-char commit SHA on main to cut from."
            " Defaults to the tip of the default branch."
        ),
    }
)
def cut_release(_ctx: Context, version: str, commit_id: str | None = None) -> None:
    """Cut a new release candidate.

    On GitHub Actions, GH_TOKEN and GITHUB_REPOSITORY are provided
    by the runner environment. When running locally, create a ``.env``
    file in the project root with::

        GH_TOKEN=<personal access token with repo scope>

    The repository name is derived from the git origin remote.
    """
    git = GitHelper(Repo("."))

    if GitHubActionsHelper.is_running_in_actions():
        token = os.environ["GH_TOKEN"]
        repo_name = os.environ["GITHUB_REPOSITORY"]
    else:
        load_dotenv()
        token = os.environ["GH_TOKEN"]
        repo_name = git.get_repo_name()

    github = GitHubHelper(Github(token).get_repo(repo_name))

    try:
        CutRelease(git, github, version, commit_id or None).run()
    except (ValueError, RuntimeError) as err:
        raise Exit(str(err), code=1) from err


@task(help={"version": "RC tag to validate (e.g., v1.2.0-rc.1)"})
def validate_promotion(_ctx: Context, version: str) -> None:
    """Validate an RC tag for promotion.

    Checks that the version is a valid RC tag, the tag exists on
    GitHub, and the corresponding release branch exists.

    On GitHub Actions, GH_TOKEN and GITHUB_REPOSITORY are provided
    by the runner environment. When running locally, create a ``.env``
    file in the project root with::

        GH_TOKEN=<personal access token with repo scope>

    The repository name is derived from the git origin remote.
    """
    if GitHubActionsHelper.is_running_in_actions():
        token = os.environ["GH_TOKEN"]
        repo_name = os.environ["GITHUB_REPOSITORY"]
    else:
        load_dotenv()
        token = os.environ["GH_TOKEN"]
        repo_name = GitHelper(Repo(".")).get_repo_name()

    github = GitHubHelper(Github(token).get_repo(repo_name))

    try:
        ValidatePromotion(github, version).run()
    except ValueError as err:
        raise Exit(str(err), code=1) from err


@task(help={"version": "RC tag to finalise (e.g., v1.2.0-rc.1)"})
def finalise_promotion(_ctx: Context, version: str) -> None:
    """Finalise a promoted RC into a stable release.

    Creates the final tag, publishes the stable GitHub Release,
    and handles merge-back detection.

    On GitHub Actions, GH_TOKEN and GITHUB_REPOSITORY are provided
    by the runner environment. When running locally, create a ``.env``
    file in the project root with::

        GH_TOKEN=<personal access token with repo scope>

    The repository name is derived from the git origin remote.
    """
    git = GitHelper(Repo("."))

    if GitHubActionsHelper.is_running_in_actions():
        token = os.environ["GH_TOKEN"]
        repo_name = os.environ["GITHUB_REPOSITORY"]
    else:
        load_dotenv()
        token = os.environ["GH_TOKEN"]
        repo_name = git.get_repo_name()

    github = GitHubHelper(Github(token).get_repo(repo_name))

    try:
        FinalisePromotion(git, github, version).run()
    except (ValueError, RuntimeError) as err:
        raise Exit(str(err), code=1) from err


@task(help={"version": "Release version (e.g., 1.2.0 or v1.2.0)"})
def tag_rc(_ctx: Context, version: str) -> None:
    """Tag a new release candidate on an existing release branch.

    Auto-increments the RC number, creates the tag and pre-release,
    and triggers the promotion pipeline.

    On GitHub Actions, GH_TOKEN and GITHUB_REPOSITORY are provided
    by the runner environment. When running locally, create a ``.env``
    file in the project root with::

        GH_TOKEN=<personal access token with repo scope>

    The repository name is derived from the git origin remote.
    """
    git = GitHelper(Repo("."))

    if GitHubActionsHelper.is_running_in_actions():
        token = os.environ["GH_TOKEN"]
        repo_name = os.environ["GITHUB_REPOSITORY"]
    else:
        load_dotenv()
        token = os.environ["GH_TOKEN"]
        repo_name = git.get_repo_name()

    github = GitHubHelper(Github(token).get_repo(repo_name))

    try:
        TagRC(git, github, version).run()
    except (ValueError, RuntimeError) as err:
        raise Exit(str(err), code=1) from err


@task(help={"base_version": "Release version to hotfix (e.g., 1.3.0 or v1.3.0)"})
def hotfix(_ctx: Context, base_version: str) -> None:
    """Create a hotfix release branch from a finalised release.

    Determines the next available patch version, validates no
    branch conflict, and creates the release branch from the
    base release tag.

    On GitHub Actions, GH_TOKEN and GITHUB_REPOSITORY are provided
    by the runner environment. When running locally, create a ``.env``
    file in the project root with::

        GH_TOKEN=<personal access token with repo scope>

    The repository name is derived from the git origin remote.
    """
    git = GitHelper(Repo("."))

    if GitHubActionsHelper.is_running_in_actions():
        token = os.environ["GH_TOKEN"]
        repo_name = os.environ["GITHUB_REPOSITORY"]
    else:
        load_dotenv()
        token = os.environ["GH_TOKEN"]
        repo_name = git.get_repo_name()

    github = GitHubHelper(Github(token).get_repo(repo_name))

    try:
        Hotfix(git, github, base_version).run()
    except (ValueError, RuntimeError) as err:
        raise Exit(str(err), code=1) from err
