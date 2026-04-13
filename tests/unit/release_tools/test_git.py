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
            self._fake_ls_remote("refs/tags/v1.0.0")
            + "\nabc123\trefs/tags/v1.0.0^{}"
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
        self.mock_repo.git.ls_remote.return_value = self._fake_ls_remote(
            "refs/tags/v1.3.0",
        )

        result = self.helper.get_next_hotfix_version(Version.parse("1.3.0"))

        assert result == Version(1, 3, 1)

    def test_get_next_hotfix_version_skips_existing_stable_patches(self) -> None:
        self.mock_repo.git.ls_remote.return_value = self._fake_ls_remote(
            "refs/tags/v1.3.0",
            "refs/tags/v1.3.1",
        )

        result = self.helper.get_next_hotfix_version(Version.parse("1.3.0"))

        assert result == Version(1, 3, 2)

    def test_get_next_hotfix_version_skips_existing_rc_patches(self) -> None:
        self.mock_repo.git.ls_remote.return_value = self._fake_ls_remote(
            "refs/tags/v1.3.0",
            "refs/tags/v1.3.1-rc.1",
        )

        result = self.helper.get_next_hotfix_version(Version.parse("1.3.0"))

        assert result == Version(1, 3, 2)

    def test_get_next_hotfix_version_finds_highest_across_stable_and_rc(
        self,
    ) -> None:
        self.mock_repo.git.ls_remote.return_value = self._fake_ls_remote(
            "refs/tags/v1.3.0",
            "refs/tags/v1.3.1",
            "refs/tags/v1.3.2-rc.1",
        )

        result = self.helper.get_next_hotfix_version(Version.parse("1.3.0"))

        assert result == Version(1, 3, 3)

    def test_get_next_hotfix_version_ignores_other_minor_versions(self) -> None:
        self.mock_repo.git.ls_remote.return_value = self._fake_ls_remote(
            "refs/tags/v1.3.0",
            "refs/tags/v1.4.1",
        )

        result = self.helper.get_next_hotfix_version(Version.parse("1.3.0"))

        assert result == Version(1, 3, 1)

    def test_get_next_hotfix_version_ignores_other_major_versions(self) -> None:
        self.mock_repo.git.ls_remote.return_value = self._fake_ls_remote(
            "refs/tags/v1.3.0",
            "refs/tags/v2.3.1",
        )

        result = self.helper.get_next_hotfix_version(Version.parse("1.3.0"))

        assert result == Version(1, 3, 1)

    def test_create_release_branch_creates_and_pushes_branch(self) -> None:
        mock_branch = self.mock_repo.create_head.return_value
        mock_branch.name = "release/1.2.0"

        self.helper.create_release_branch("1.2.0")

        self.mock_repo.create_head.assert_called_once_with("release/1.2.0")
        self.mock_origin.push.assert_called_once_with("release/1.2.0")

    def test_create_release_branch_with_source_ref(self) -> None:
        mock_branch = self.mock_repo.create_head.return_value
        mock_branch.name = "release/1.3.1"
        self.mock_repo.git.ls_remote.return_value = self._fake_ls_remote(
            "refs/tags/v1.3.0",
        )

        self.helper.create_release_branch("1.3.1", source_ref="v1.3.0")

        self.mock_repo.create_head.assert_called_once_with(
            "release/1.3.1", commit="0" * 40
        )
        self.mock_origin.push.assert_called_once_with("release/1.3.1")

    def test_create_release_branch_raises_when_source_ref_not_found(self) -> None:
        self.mock_repo.git.ls_remote.return_value = ""

        with pytest.raises(ValueError, match="not found on origin"):
            self.helper.create_release_branch("1.3.1", source_ref="v1.3.0")

    def test_create_rc_tag_creates_and_pushes_tag(self) -> None:
        self.helper.create_rc_tag("1.2.0")

        self.mock_repo.create_tag.assert_called_once_with("v1.2.0-rc.1")
        self.mock_origin.push.assert_called_once_with("v1.2.0-rc.1")

    def test_create_rc_tag_returns_tag_name(self) -> None:
        result = self.helper.create_rc_tag("1.2.0")

        assert result == "v1.2.0-rc.1"

    def test_create_rc_tag_uses_custom_rc_number(self) -> None:
        result = self.helper.create_rc_tag("1.2.0", rc_number=3)

        assert result == "v1.2.0-rc.3"
        self.mock_repo.create_tag.assert_called_once_with("v1.2.0-rc.3")

    def test_get_repo_name_parses_ssh_url(self) -> None:
        self.mock_origin.url = "git@github.com:owner/repo.git"

        result = self.helper.get_repo_name()

        assert result == "owner/repo"

    def test_get_repo_name_parses_https_url(self) -> None:
        self.mock_origin.url = "https://github.com/owner/repo.git"

        result = self.helper.get_repo_name()

        assert result == "owner/repo"

    def test_get_head_sha_returns_commit_hexsha(self) -> None:
        self.mock_repo.head.commit.hexsha = "abc123def456"

        result = self.helper.get_head_sha()

        assert result == "abc123def456"

    def test_configure_identity_sets_user_name_and_email(
        self, mocker: MockerFixture
    ) -> None:
        mock_writer = mocker.MagicMock()
        self.mock_repo.config_writer.return_value = mock_writer
        mock_config = mock_writer.__enter__.return_value

        self.helper.configure_identity("Bot", "bot@example.com")

        mock_config.set_value.assert_any_call("user", "name", "Bot")
        mock_config.set_value.assert_any_call("user", "email", "bot@example.com")

    def test_create_final_tag_creates_and_pushes_when_new(self) -> None:
        self.mock_repo.git.ls_remote.return_value = self._fake_ls_remote(
            "refs/tags/v1.2.0-rc.1",
        )

        result = self.helper.create_final_tag("v1.2.0", "v1.2.0-rc.1")

        assert result is True
        self.mock_repo.create_tag.assert_called_once_with(
            "v1.2.0", ref="0" * 40, message="Release v1.2.0"
        )
        self.mock_origin.push.assert_called_once_with("v1.2.0")

    def test_create_final_tag_returns_false_when_tag_exists(self) -> None:
        self.mock_repo.git.ls_remote.return_value = self._fake_ls_remote(
            "refs/tags/v1.2.0",
            "refs/tags/v1.2.0-rc.1",
        )

        result = self.helper.create_final_tag("v1.2.0", "v1.2.0-rc.1")

        assert result is False
        self.mock_repo.create_tag.assert_not_called()

    def test_create_final_tag_raises_when_source_ref_not_found(self) -> None:
        self.mock_repo.git.ls_remote.return_value = ""

        with pytest.raises(ValueError, match="not found on origin"):
            self.helper.create_final_tag("v1.2.0", "v1.2.0-rc.1")

    def test_create_final_tag_prefers_dereferenced_sha(self) -> None:
        self.mock_repo.git.ls_remote.return_value = (
            "aaa111\trefs/tags/v1.2.0-rc.1\n"
            "bbb222\trefs/tags/v1.2.0-rc.1^{}"
        )

        self.helper.create_final_tag("v1.2.0", "v1.2.0-rc.1")

        self.mock_repo.create_tag.assert_called_once_with(
            "v1.2.0", ref="bbb222", message="Release v1.2.0"
        )

    @staticmethod
    def _fake_ls_remote(*ref_paths: str) -> str:
        """Build fake ``git ls-remote`` output for the given ref paths."""
        dummy_sha = "0" * 40
        return "\n".join(f"{dummy_sha}\t{ref_path}" for ref_path in ref_paths)
