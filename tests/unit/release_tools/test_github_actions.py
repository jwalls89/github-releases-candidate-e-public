"""Unit tests for GitHubActionsHelper."""

from pytest_mock import MockerFixture

from release_tools.github_actions import GitHubActionsHelper


class TestGitHubActionsHelper:
    """Tests for GitHubActionsHelper."""

    def test_is_running_in_actions_returns_true_when_env_set(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.dict("os.environ", {"GITHUB_ACTIONS": "true"})

        assert GitHubActionsHelper.is_running_in_actions() is True

    def test_is_running_in_actions_returns_false_when_env_not_set(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.dict("os.environ", {}, clear=True)

        assert GitHubActionsHelper.is_running_in_actions() is False

    def test_is_running_in_actions_returns_false_when_env_not_true(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.dict("os.environ", {"GITHUB_ACTIONS": "false"})

        assert GitHubActionsHelper.is_running_in_actions() is False
