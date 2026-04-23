"""Unit tests for CutRelease."""

from unittest import mock

import pytest
from pytest_mock import MockerFixture
from semver import Version

from release_tools.cut_release import CutRelease
from release_tools.git import GitHelper
from release_tools.github import GitHubHelper


class TestCutRelease:
    """Tests for CutRelease."""

    @pytest.fixture(autouse=True)
    def setup(self, mocker: MockerFixture) -> None:
        self.mock_git = mocker.Mock(spec_set=GitHelper)
        self.mock_github = mocker.Mock(spec_set=GitHubHelper)
        self.mock_git.get_latest_stable_tag.return_value = Version.parse("1.0.0")
        self.mock_git.get_inflight_release.return_value = None
        self.mock_github.create_rc_tag.return_value = ("v2.0.0-rc.1", "abc123")
        mocker.patch(
            "release_tools.cut_release.ReleaseVersionHelper.parse",
            return_value=Version.parse("2.0.0"),
        )
        mocker.patch(
            "release_tools.cut_release.ReleaseVersionHelper.check_version_is_higher",
        )

    def test_run_creates_branch_and_tag_when_valid_version(self) -> None:
        CutRelease(self.mock_git, self.mock_github, "2.0.0").run()

        self.mock_git.create_release_branch.assert_called_once_with("2.0.0")
        self.mock_github.create_rc_tag.assert_called_once_with("2.0.0", "release/2.0.0")

    def test_run_raises_when_version_not_higher(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "release_tools.cut_release.ReleaseVersionHelper.check_version_is_higher",
            side_effect=ValueError("not higher"),
        )

        with pytest.raises(ValueError, match="not higher"):
            CutRelease(self.mock_git, self.mock_github, "0.5.0").run()

    def test_run_raises_when_release_inflight(self) -> None:
        self.mock_git.get_inflight_release.return_value = "1.5.0"

        with pytest.raises(RuntimeError, match="still in-flight"):
            CutRelease(self.mock_git, self.mock_github, "2.0.0").run()

    def test_run_calls_create_prerelease_with_previous_tag(self) -> None:
        CutRelease(self.mock_git, self.mock_github, "2.0.0").run()

        self.mock_github.create_prerelease.assert_called_once_with(
            "v2.0.0-rc.1",
            "release/2.0.0",
            "v1.0.0",
        )

    def test_run_calls_create_prerelease_with_none_when_no_latest(self) -> None:
        self.mock_git.get_latest_stable_tag.return_value = None

        CutRelease(self.mock_git, self.mock_github, "2.0.0").run()

        self.mock_github.create_prerelease.assert_called_once_with(
            "v2.0.0-rc.1",
            "release/2.0.0",
            None,
        )

    def test_run_calls_trigger_promotion(self) -> None:
        CutRelease(self.mock_git, self.mock_github, "2.0.0").run()

        self.mock_github.trigger_promotion.assert_called_once_with(
            "release/2.0.0",
            "v2.0.0-rc.1",
        )

    @mock.patch.dict("os.environ", {}, clear=True)
    def test_run_writes_summary(self, capsys: pytest.CaptureFixture[str]) -> None:
        CutRelease(self.mock_git, self.mock_github, "2.0.0").run()

        captured = capsys.readouterr()
        assert "## Release Cut" in captured.out
        assert "release/2.0.0" in captured.out
        assert "v2.0.0-rc.1" in captured.out
        assert "abc123" in captured.out

    def test_run_calls_steps_in_correct_order(self) -> None:
        CutRelease(self.mock_git, self.mock_github, "2.0.0").run()

        github_methods = [c[0] for c in self.mock_github.method_calls]

        assert github_methods.index("create_rc_tag") < github_methods.index(
            "create_prerelease"
        )
        assert github_methods.index("create_prerelease") < github_methods.index(
            "trigger_promotion"
        )

    def test_run_skips_ancestor_check_when_commit_id_not_given(self) -> None:
        CutRelease(self.mock_git, self.mock_github, "2.0.0").run()

        self.mock_github.is_ancestor_of_main.assert_not_called()

    def test_run_checks_ancestor_when_commit_id_given(self) -> None:
        self.mock_github.is_ancestor_of_main.return_value = True

        CutRelease(self.mock_git, self.mock_github, "2.0.0", commit_id="a" * 40).run()

        self.mock_github.is_ancestor_of_main.assert_called_once_with("a" * 40)
        self.mock_git.create_release_branch.assert_called_once_with("2.0.0")

    def test_run_raises_when_commit_not_ancestor_of_main(self) -> None:
        self.mock_github.is_ancestor_of_main.return_value = False

        with pytest.raises(ValueError, match="not on main"):
            CutRelease(
                self.mock_git, self.mock_github, "2.0.0", commit_id="b" * 40
            ).run()

        self.mock_git.create_release_branch.assert_not_called()
