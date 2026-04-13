"""Unit tests for FinalisePromotion."""

from unittest import mock

import pytest
from pytest_mock import MockerFixture
from semver import Version

from release_tools.finalise_promotion import FinalisePromotion
from release_tools.git import GitHelper
from release_tools.github import GitHubHelper


class TestFinalisePromotion:
    """Tests for FinalisePromotion."""

    @pytest.fixture(autouse=True)
    def setup(self, mocker: MockerFixture) -> None:
        self.mock_git = mocker.Mock(spec_set=GitHelper)
        self.mock_github = mocker.Mock(spec_set=GitHubHelper)
        self.mock_git.create_final_tag.return_value = True
        self.mock_github.get_mergeback_count.return_value = 0
        self.mock_github.find_previous_stable_release.return_value = "v1.0.0"
        self.mock_github.create_mergeback_issue.return_value = (
            "https://github.com/owner/repo/issues/1"
        )
        mocker.patch(
            "release_tools.finalise_promotion.ReleaseVersionHelper.parse_rc",
            return_value=Version.parse("2.0.0-rc.1"),
        )

    def test_run_configures_git_identity(self) -> None:
        FinalisePromotion(self.mock_git, self.mock_github, "v2.0.0-rc.1").run()

        self.mock_git.configure_identity.assert_called_once_with(
            "github-actions[bot]",
            "github-actions[bot]@users.noreply.github.com",
        )

    def test_run_creates_final_tag_from_rc(self) -> None:
        FinalisePromotion(self.mock_git, self.mock_github, "v2.0.0-rc.1").run()

        self.mock_git.create_final_tag.assert_called_once_with("v2.0.0", "v2.0.0-rc.1")

    def test_run_finds_previous_stable_release(self) -> None:
        FinalisePromotion(self.mock_git, self.mock_github, "v2.0.0-rc.1").run()

        self.mock_github.find_previous_stable_release.assert_called_once_with("v2.0.0")

    def test_run_publishes_stable_release_with_previous_tag(self) -> None:
        FinalisePromotion(self.mock_git, self.mock_github, "v2.0.0-rc.1").run()

        self.mock_github.publish_stable_release.assert_called_once_with(
            "v2.0.0", "v1.0.0"
        )

    def test_run_publishes_stable_release_with_none_when_first(
        self,
    ) -> None:
        self.mock_github.find_previous_stable_release.return_value = None

        FinalisePromotion(self.mock_git, self.mock_github, "v2.0.0-rc.1").run()

        self.mock_github.publish_stable_release.assert_called_once_with("v2.0.0", None)

    def test_run_checks_mergeback_count(self) -> None:
        FinalisePromotion(self.mock_git, self.mock_github, "v2.0.0-rc.1").run()

        self.mock_github.get_mergeback_count.assert_called_once_with("release/2.0.0")

    def test_run_creates_mergeback_issue_when_ahead(self) -> None:
        self.mock_github.get_mergeback_count.return_value = 3

        FinalisePromotion(self.mock_git, self.mock_github, "v2.0.0-rc.1").run()

        self.mock_github.annotate_release_with_mergeback.assert_called_once_with(
            "v2.0.0", "release/2.0.0", 3
        )
        self.mock_github.create_mergeback_issue.assert_called_once_with(
            "v2.0.0", "release/2.0.0", 3
        )

    def test_run_skips_mergeback_when_not_ahead(self) -> None:
        self.mock_github.get_mergeback_count.return_value = 0

        FinalisePromotion(self.mock_git, self.mock_github, "v2.0.0-rc.1").run()

        self.mock_github.annotate_release_with_mergeback.assert_not_called()
        self.mock_github.create_mergeback_issue.assert_not_called()

    def test_run_calls_steps_in_correct_order(self) -> None:
        self.mock_github.get_mergeback_count.return_value = 2

        FinalisePromotion(self.mock_git, self.mock_github, "v2.0.0-rc.1").run()

        git_methods = [call[0] for call in self.mock_git.method_calls]
        github_methods = [call[0] for call in self.mock_github.method_calls]

        assert git_methods.index("configure_identity") < git_methods.index(
            "create_final_tag"
        )
        assert github_methods.index(
            "find_previous_stable_release"
        ) < github_methods.index("publish_stable_release")
        assert github_methods.index("publish_stable_release") < github_methods.index(
            "get_mergeback_count"
        )
        assert github_methods.index("get_mergeback_count") < github_methods.index(
            "annotate_release_with_mergeback"
        )

    @mock.patch.dict("os.environ", {}, clear=True)
    def test_run_writes_summary_without_mergeback(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self.mock_github.get_mergeback_count.return_value = 0

        FinalisePromotion(self.mock_git, self.mock_github, "v2.0.0-rc.1").run()

        captured = capsys.readouterr()
        assert "## Release Finalised" in captured.out
        assert "v2.0.0" in captured.out
        assert "v2.0.0-rc.1" in captured.out
        assert "Merge-back required" not in captured.out

    @mock.patch.dict("os.environ", {}, clear=True)
    def test_run_writes_summary_with_mergeback(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        self.mock_github.get_mergeback_count.return_value = 3

        FinalisePromotion(self.mock_git, self.mock_github, "v2.0.0-rc.1").run()

        captured = capsys.readouterr()
        assert "Merge-back required" in captured.out
        assert "3 commit(s)" in captured.out
