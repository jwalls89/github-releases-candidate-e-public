"""Unit tests for Hotfix."""

from unittest import mock

import pytest
from pytest_mock import MockerFixture
from semver import Version

from release_tools.git import GitHelper
from release_tools.github import GitHubHelper
from release_tools.hotfix import Hotfix


class TestHotfix:
    """Tests for Hotfix."""

    @pytest.fixture(autouse=True)
    def setup(self, mocker: MockerFixture) -> None:
        self.mock_git = mocker.Mock(spec_set=GitHelper)
        self.mock_github = mocker.Mock(spec_set=GitHubHelper)
        self.mock_git.get_next_hotfix_version.return_value = Version.parse("1.3.1")
        self.mock_git.get_head_sha.return_value = "abc123"
        mocker.patch(
            "release_tools.hotfix.ReleaseVersionHelper.parse",
            return_value=Version.parse("1.3.0"),
        )

    def test_run_validates_base_tag_exists(self) -> None:
        Hotfix(self.mock_git, self.mock_github, "1.3.0").run()

        self.mock_github.validate_tag_exists.assert_called_once_with("v1.3.0")

    def test_run_raises_when_base_tag_not_found(self) -> None:
        self.mock_github.validate_tag_exists.side_effect = ValueError("not found")

        with pytest.raises(ValueError, match="not found"):
            Hotfix(self.mock_git, self.mock_github, "1.3.0").run()

    def test_run_determines_hotfix_version(self) -> None:
        Hotfix(self.mock_git, self.mock_github, "1.3.0").run()

        self.mock_git.get_next_hotfix_version.assert_called_once_with(
            Version.parse("1.3.0")
        )

    def test_run_validates_branch_does_not_exist(self) -> None:
        Hotfix(self.mock_git, self.mock_github, "1.3.0").run()

        self.mock_github.validate_release_branch_does_not_exist.assert_called_once_with(
            "1.3.1"
        )

    def test_run_raises_when_branch_already_exists(self) -> None:
        self.mock_github.validate_release_branch_does_not_exist.side_effect = (
            ValueError("already exists")
        )

        with pytest.raises(ValueError, match="already exists"):
            Hotfix(self.mock_git, self.mock_github, "1.3.0").run()

    def test_run_creates_release_branch_from_base_tag(self) -> None:
        Hotfix(self.mock_git, self.mock_github, "1.3.0").run()

        self.mock_git.create_release_branch.assert_called_once_with(
            "1.3.1", source_ref="v1.3.0"
        )

    def test_run_calls_steps_in_correct_order(self) -> None:
        Hotfix(self.mock_git, self.mock_github, "1.3.0").run()

        github_methods = [call[0] for call in self.mock_github.method_calls]
        git_methods = [call[0] for call in self.mock_git.method_calls]

        assert github_methods.index("validate_tag_exists") < github_methods.index(
            "validate_release_branch_does_not_exist"
        )
        assert git_methods.index("get_next_hotfix_version") < git_methods.index(
            "create_release_branch"
        )

    @mock.patch.dict("os.environ", {}, clear=True)
    def test_run_writes_summary(self, capsys: pytest.CaptureFixture[str]) -> None:
        Hotfix(self.mock_git, self.mock_github, "1.3.0").run()

        captured = capsys.readouterr()
        assert "## Hotfix Branch Created" in captured.out
        assert "v1.3.0" in captured.out
        assert "1.3.1" in captured.out
        assert "abc123" in captured.out
