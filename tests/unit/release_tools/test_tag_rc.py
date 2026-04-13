"""Unit tests for TagRC."""

from unittest import mock

import pytest
from pytest_mock import MockerFixture
from semver import Version

from release_tools.git import GitHelper
from release_tools.github import GitHubHelper
from release_tools.tag_rc import TagRC


class TestTagRC:
    """Tests for TagRC."""

    @pytest.fixture(autouse=True)
    def setup(self, mocker: MockerFixture) -> None:
        self.mock_git = mocker.Mock(spec_set=GitHelper)
        self.mock_github = mocker.Mock(spec_set=GitHubHelper)
        self.mock_git.get_next_rc_number.return_value = 3
        self.mock_github.create_rc_tag.return_value = ("v2.0.0-rc.3", "abc123")
        self.mock_github.create_prerelease.return_value = (
            "https://github.com/owner/repo/releases/v2.0.0-rc.3"
        )
        mocker.patch(
            "release_tools.tag_rc.ReleaseVersionHelper.parse",
            return_value=Version.parse("2.0.0"),
        )

    def test_run_validates_branch_exists(self) -> None:
        TagRC(self.mock_git, self.mock_github, "2.0.0").run()

        self.mock_github.validate_release_branch_exists.assert_called_once_with("2.0.0")

    def test_run_validates_not_finalised(self) -> None:
        TagRC(self.mock_git, self.mock_github, "2.0.0").run()

        self.mock_github.validate_not_finalised.assert_called_once_with("2.0.0")

    def test_run_raises_when_branch_not_found(self) -> None:
        self.mock_github.validate_release_branch_exists.side_effect = ValueError(
            "not found"
        )

        with pytest.raises(ValueError, match="not found"):
            TagRC(self.mock_git, self.mock_github, "2.0.0").run()

    def test_run_raises_when_already_finalised(self) -> None:
        self.mock_github.validate_not_finalised.side_effect = ValueError(
            "already finalised"
        )

        with pytest.raises(ValueError, match="already finalised"):
            TagRC(self.mock_git, self.mock_github, "2.0.0").run()

    def test_run_gets_next_rc_number(self) -> None:
        TagRC(self.mock_git, self.mock_github, "2.0.0").run()

        self.mock_git.get_next_rc_number.assert_called_once_with("2.0.0")

    def test_run_creates_rc_tag_with_correct_number(self) -> None:
        TagRC(self.mock_git, self.mock_github, "2.0.0").run()

        self.mock_github.create_rc_tag.assert_called_once_with(
            "2.0.0", "release/2.0.0", rc_number=3
        )

    def test_run_creates_prerelease(self) -> None:
        TagRC(self.mock_git, self.mock_github, "2.0.0").run()

        self.mock_github.create_prerelease.assert_called_once_with(
            "v2.0.0-rc.3",
            "release/2.0.0",
        )

    def test_run_triggers_promotion(self) -> None:
        TagRC(self.mock_git, self.mock_github, "2.0.0").run()

        self.mock_github.trigger_promotion.assert_called_once_with(
            "release/2.0.0",
            "v2.0.0-rc.3",
        )

    def test_run_calls_steps_in_correct_order(self) -> None:
        TagRC(self.mock_git, self.mock_github, "2.0.0").run()

        github_methods = [call[0] for call in self.mock_github.method_calls]

        assert github_methods.index(
            "validate_release_branch_exists"
        ) < github_methods.index("validate_not_finalised")
        assert github_methods.index("create_rc_tag") < github_methods.index(
            "create_prerelease"
        )
        assert github_methods.index("create_prerelease") < github_methods.index(
            "trigger_promotion"
        )

    @mock.patch.dict("os.environ", {}, clear=True)
    def test_run_writes_summary(self, capsys: pytest.CaptureFixture[str]) -> None:
        TagRC(self.mock_git, self.mock_github, "2.0.0").run()

        captured = capsys.readouterr()
        assert "## New RC Tagged" in captured.out
        assert "v2.0.0-rc.3" in captured.out
        assert "release/2.0.0" in captured.out
        assert "abc123" in captured.out
