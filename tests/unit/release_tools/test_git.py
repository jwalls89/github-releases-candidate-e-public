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
        tag_1 = self._make_tag("v1.0.0")
        tag_2 = self._make_tag("v2.0.0")
        tag_3 = self._make_tag("v1.5.0")
        self.mock_repo.tags = [tag_1, tag_2, tag_3]

        result = self.helper.get_latest_stable_tag()

        assert result == Version.parse("2.0.0")

    def test_get_latest_stable_tag_returns_none_when_no_tags(self) -> None:
        self.mock_repo.tags = []

        result = self.helper.get_latest_stable_tag()

        assert result is None

    def test_get_latest_stable_tag_ignores_prerelease_tags(self) -> None:
        tag_stable = self._make_tag("v1.0.0")
        tag_rc = self._make_tag("v2.0.0-rc.1")
        self.mock_repo.tags = [tag_stable, tag_rc]

        result = self.helper.get_latest_stable_tag()

        assert result == Version.parse("1.0.0")

    def test_get_inflight_release_returns_version_when_no_stable_tag(
        self,
    ) -> None:
        self.mock_repo.tags = [self._make_tag("v1.0.0")]
        self.mock_origin.refs = [
            self._make_ref("origin/release/2.0.0"),
        ]

        result = self.helper.get_inflight_release()

        assert result == "2.0.0"

    def test_get_inflight_release_returns_none_when_all_finalised(
        self,
    ) -> None:
        self.mock_repo.tags = [self._make_tag("v1.0.0")]
        self.mock_origin.refs = [
            self._make_ref("origin/release/1.0.0"),
        ]

        result = self.helper.get_inflight_release()

        assert result is None

    def test_get_inflight_release_returns_none_when_no_release_branches(
        self,
    ) -> None:
        self.mock_repo.tags = []
        self.mock_origin.refs = [self._make_ref("origin/main")]

        result = self.helper.get_inflight_release()

        assert result is None

    def test_create_release_branch_creates_and_pushes_branch(self) -> None:
        mock_branch = self.mock_repo.create_head.return_value
        mock_branch.name = "release/1.2.0"

        self.helper.create_release_branch("1.2.0")

        self.mock_repo.create_head.assert_called_once_with("release/1.2.0")
        self.mock_origin.push.assert_called_once_with("release/1.2.0")

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

    @staticmethod
    def _make_tag(name: str) -> git.TagReference:
        return type("Tag", (), {"name": name})()  # type: ignore[return-value]

    @staticmethod
    def _make_ref(name: str) -> git.RemoteReference:
        return type("Ref", (), {"name": name})()  # type: ignore[return-value]
