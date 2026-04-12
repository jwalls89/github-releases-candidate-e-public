"""Release invoke tasks."""

import os

from dotenv import load_dotenv
from git import Repo
from github import Github
from invoke import Context, Exit, task

from release_tools.cut_release import CutRelease
from release_tools.git import GitHelper
from release_tools.github import GitHubHelper
from release_tools.github_actions import GitHubActionsHelper


@task(help={"version": "Release version (e.g., 1.2.0 or v1.2.0)"})
def cut_release(_ctx: Context, version: str) -> None:
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
        CutRelease(git, github, version).run()
    except (ValueError, RuntimeError) as err:
        raise Exit(str(err), code=1) from err
