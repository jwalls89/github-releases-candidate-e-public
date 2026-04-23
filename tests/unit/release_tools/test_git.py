"""Unit tests for GitHelper."""

import git
import pytest
from pytest_mock import MockerFixture
from semver import Version

from release_tools.git import GitHelper


class TestGitHelper:
    """Tests for GitHelper."""

    @pytest.fixture(autouse=True)
    def setup(self, mocker: MockerFixture) -> None:
        self.mock_repo = mocker.Mock(spec_set=git.Repo)
        self.mock_origin = mocker.Mock()
        self.mock_repo.remotes.origin = self.mock_origin
        self.helper = GitHelper(self.mock_repo)

    def test_get_latest_stable_tag_returns_highest_when_multiple_tags(
        self,
    ) -> None:
        self.mock_repo.git.ls_remote.return_value = self._fake_ls_remote(
            "refs/tags/v1.0.0",
            "refs/tags/v2.0.0",
            "refs/tags/v1.5.0",
        )

        result = self.helper.get_latest_stable_tag()

        assert result == Version.parse("2.0.0")
        self.mock_repo.git.ls_remote.assert_called_once_with("--tags", "origin")

    def test_get_latest_stable_tag_returns_none_when_no_tags(self) -> None:
        self.mock_repo.git.ls_remote.return_value = ""

        result = self.helper.get_latest_stable_tag()

        assert result is None

    def test_get_latest_stable_tag_ignores_prerelease_tags(self) -> None:
        self.mock_repo.git.ls_remote.return_value = self._fake_ls_remote(
            "refs/tags/v1.0.0",
            "refs/tags/v2.0.0-rc.1",
        )

        result = self.helper.get_latest_stable_tag()

        assert result == Version.parse("1.0.0")

    def test_get_latest_stable_tag_ignores_dereference_entries(self) -> None:
        self.mock_repo.git.ls_remote.return_value = (
            self._fake_ls_remote("refs/tags/v1.0.0") + "\nabc123\trefs/tags/v1.0.0^{}"
        )

        result = self.helper.get_latest_stable_tag()

        assert result == Version.parse("1.0.0")

    def test_get_inflight_release_returns_version_when_no_stable_tag(
        self,
    ) -> None:
        self.mock_repo.git.ls_remote.side_effect = [
            self._fake_ls_remote("refs/tags/v1.0.0"),
            self._fake_ls_remote("refs/heads/release/2.0.0"),
        ]

        result = self.helper.get_inflight_release()

        assert result == "2.0.0"

    def test_get_inflight_release_returns_none_when_all_finalised(
        self,
    ) -> None:
        self.mock_repo.git.ls_remote.side_effect = [
            self._fake_ls_remote("refs/tags/v1.0.0"),
            self._fake_ls_remote("refs/heads/release/1.0.0"),
        ]

        result = self.helper.get_inflight_release()

        assert result is None

    def test_get_inflight_release_returns_none_when_no_release_branches(
        self,
    ) -> None:
        self.mock_repo.git.ls_remote.side_effect = [
            "",
            self._fake_ls_remote("refs/heads/main"),
        ]

        result = self.helper.get_inflight_release()

        assert result is None

    def test_get_next_rc_number_returns_1_when_no_rc_tags(self) -> None:
        self.mock_repo.git.ls_remote.return_value = ""

        result = self.helper.get_next_rc_number("1.0.0")

        assert result == 1

    def test_get_next_rc_number_returns_next_after_highest(self) -> None:
        self.mock_repo.git.ls_remote.return_value = self._fake_ls_remote(
            "refs/tags/v1.0.0-rc.1",
            "refs/tags/v1.0.0-rc.2",
            "refs/tags/v1.0.0-rc.3",
        )

        result = self.helper.get_next_rc_number("1.0.0")

        assert result == 4

    def test_get_next_rc_number_ignores_other_version_rc_tags(self) -> None:
        self.mock_repo.git.ls_remote.return_value = self._fake_ls_remote(
            "refs/tags/v2.0.0-rc.5",
        )

        result = self.helper.get_next_rc_number("1.0.0")

        assert result == 1

    def test_get_next_rc_number_ignores_stable_tags(self) -> None:
        self.mock_repo.git.ls_remote.return_value = self._fake_ls_remote(
            "refs/tags/v1.0.0",
            "refs/tags/v1.0.0-rc.2",
        )

        result = self.helper.get_next_rc_number("1.0.0")

        assert result == 3

    def test_get_next_rc_number_handles_non_sequential(self) -> None:
        self.mock_repo.git.ls_remote.return_value = self._fake_ls_remote(
            "refs/tags/v1.0.0-rc.1",
            "refs/tags/v1.0.0-rc.5",
        )

        result = self.helper.get_next_rc_number("1.0.0")

        assert result == 6

    def test_get_next_hotfix_version_returns_patch_plus_1_when_no_higher(
        self,
    ) -> None:
        self.mock_repo.git.ls_remote.side_effect = [
            self._fake_ls_remote("refs/tags/v1.3.0"),
            "",
        ]

        result = self.helper.get_next_hotfix_version(Version.parse("1.3.0"))

        assert result == Version(1, 3, 1)

    def test_get_next_hotfix_version_skips_existing_stable_patches(self) -> None:
        self.mock_repo.git.ls_remote.side_effect = [
            self._fake_ls_remote("refs/tags/v1.3.0", "refs/tags/v1.3.1"),
            "",
        ]

        result = self.helper.get_next_hotfix_version(Version.parse("1.3.0"))

        assert result == Version(1, 3, 2)

    def test_get_next_hotfix_version_skips_existing_rc_patches(self) -> None:
        self.mock_repo.git.ls_remote.side_effect = [
            self._fake_ls_remote("refs/tags/v1.3.0", "refs/tags/v1.3.1-rc.1"),
            "",
        ]

        result = self.helper.get_next_hotfix_version(Version.parse("1.3.0"))

        assert result == Version(1, 3, 2)

    def test_get_next_hotfix_version_finds_highest_across_stable_and_rc(
        self,
    ) -> None:
        self.mock_repo.git.ls_remote.side_effect = [
            self._fake_ls_remote(
                "refs/tags/v1.3.0", "refs/tags/v1.3.1", "refs/tags/v1.3.2-rc.1"
            ),
            "",
        ]

        result = self.helper.get_next_hotfix_version(Version.parse("1.3.0"))

        assert result == Version(1, 3, 3)

    def test_get_next_hotfix_version_ignores_other_minor_versions(self) -> None:
        self.mock_repo.git.ls_remote.side_effect = [
            self._fake_ls_remote("refs/tags/v1.3.0", "refs/tags/v1.4.1"),
            "",
        ]

        result = self.helper.get_next_hotfix_version(Version.parse("1.3.0"))

        assert result == Version(1, 3, 1)

    def test_get_next_hotfix_version_ignores_other_major_versions(self) -> None:
        self.mock_repo.git.ls_remote.side_effect = [
            self._fake_ls_remote("refs/tags/v1.3.0", "refs/tags/v2.3.1"),
            "",
        ]

        result = self.helper.get_next_hotfix_version(Version.parse("1.3.0"))

        assert result == Version(1, 3, 1)

    def test_get_next_hotfix_version_skips_existing_release_branches(self) -> None:
        self.mock_repo.git.ls_remote.side_effect = [
            self._fake_ls_remote("refs/tags/v1.3.0"),
            self._fake_ls_remote("refs/heads/release/1.3.1"),
        ]

        result = self.helper.get_next_hotfix_version(Version.parse("1.3.0"))

        assert result == Version(1, 3, 2)

    def test_get_next_hotfix_version_considers_both_tags_and_branches(self) -> None:
        self.mock_repo.git.ls_remote.side_effect = [
            self._fake_ls_remote("refs/tags/v1.3.0", "refs/tags/v1.3.1"),
            self._fake_ls_remote("refs/heads/release/1.3.2"),
        ]

        result = self.helper.get_next_hotfix_version(Version.parse("1.3.0"))

        assert result == Version(1, 3, 3)

    def test_get_repo_name_parses_ssh_url(self) -> None:
        self.mock_origin.url = "git@github.com:owner/repo.git"

        result = self.helper.get_repo_name()

        assert result == "owner/repo"

    def test_get_repo_name_parses_https_url(self) -> None:
        self.mock_origin.url = "https://github.com/owner/repo.git"

        result = self.helper.get_repo_name()

        assert result == "owner/repo"

    @staticmethod
    def _fake_ls_remote(*ref_paths: str) -> str:
        """Build fake ``git ls-remote`` output for the given ref paths."""
        dummy_sha = "0" * 40
        return "\n".join(f"{dummy_sha}\t{ref_path}" for ref_path in ref_paths)
