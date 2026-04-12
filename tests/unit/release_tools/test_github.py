"""Unit tests for GitHubHelper."""

import pytest
from github.GithubObject import NotSet
from github.Repository import Repository
from pytest_mock import MockerFixture

from release_tools.github import GitHubHelper


class TestGitHubHelper:
    """Tests for GitHubHelper."""

    @pytest.fixture(autouse=True)
    def setup(self, mocker: MockerFixture) -> None:
        self.mock_repo = mocker.Mock(spec_set=Repository)
        self.helper = GitHubHelper(self.mock_repo)

    def test_create_prerelease_calls_generate_release_notes(self) -> None:
        self.helper.create_prerelease("v1.0.0-rc.1", "release/1.0.0")

        self.mock_repo.generate_release_notes.assert_called_once()

    def test_create_prerelease_passes_previous_tag_when_provided(
        self,
    ) -> None:
        self.helper.create_prerelease("v1.0.0-rc.1", "release/1.0.0", "v0.9.0")

        call_kwargs = self.mock_repo.generate_release_notes.call_args.kwargs
        assert call_kwargs["previous_tag_name"] == "v0.9.0"

    def test_create_prerelease_uses_notset_when_no_previous_tag(
        self,
    ) -> None:
        self.helper.create_prerelease("v1.0.0-rc.1", "release/1.0.0")

        call_kwargs = self.mock_repo.generate_release_notes.call_args.kwargs
        assert call_kwargs["previous_tag_name"] is NotSet

    def test_create_prerelease_creates_release_with_generated_notes(
        self,
    ) -> None:
        self.mock_repo.generate_release_notes.return_value.body = (
            "## Changes\n- Fixed bug"
        )

        self.helper.create_prerelease("v1.0.0-rc.1", "release/1.0.0")

        self.mock_repo.create_git_release.assert_called_once_with(
            tag="v1.0.0-rc.1",
            name="v1.0.0-rc.1",
            message="## Changes\n- Fixed bug",
            target_commitish="release/1.0.0",
            prerelease=True,
        )

    def test_create_prerelease_returns_html_url(self) -> None:
        self.mock_repo.create_git_release.return_value.html_url = (
            "https://github.com/owner/repo/releases/v1.0.0-rc.1"
        )

        result = self.helper.create_prerelease("v1.0.0-rc.1", "release/1.0.0")

        assert result == "https://github.com/owner/repo/releases/v1.0.0-rc.1"

    def test_trigger_promotion_dispatches_workflow(self) -> None:
        self.helper.trigger_promotion("release/1.0.0", "v1.0.0-rc.1")

        self.mock_repo.get_workflow.assert_called_once_with("promote.yml")
        mock_dispatch = self.mock_repo.get_workflow.return_value.create_dispatch
        mock_dispatch.assert_called_once()

    def test_trigger_promotion_passes_correct_inputs(self) -> None:
        self.helper.trigger_promotion("release/1.0.0", "v1.0.0-rc.1")

        mock_dispatch = self.mock_repo.get_workflow.return_value.create_dispatch
        mock_dispatch.assert_called_once_with(
            ref="release/1.0.0",
            inputs={"version": "v1.0.0-rc.1"},
        )
