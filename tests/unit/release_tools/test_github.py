"""Unit tests for GitHubHelper."""

import pytest
from github import UnknownObjectException
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

    # -- create_rc_tag --

    def test_create_rc_tag_creates_ref_at_branch_tip(
        self, mocker: MockerFixture
    ) -> None:
        mock_branch = mocker.Mock()
        mock_branch.commit.sha = "abc123"
        self.mock_repo.get_branch.return_value = mock_branch

        tag_name, commit_sha = self.helper.create_rc_tag("1.2.0", "release/1.2.0")

        assert tag_name == "v1.2.0-rc.1"
        assert commit_sha == "abc123"
        self.mock_repo.get_branch.assert_called_once_with("release/1.2.0")
        self.mock_repo.create_git_ref.assert_called_once_with(
            ref="refs/tags/v1.2.0-rc.1", sha="abc123"
        )

    def test_create_rc_tag_uses_custom_rc_number(self, mocker: MockerFixture) -> None:
        mock_branch = mocker.Mock()
        mock_branch.commit.sha = "abc123"
        self.mock_repo.get_branch.return_value = mock_branch

        tag_name, _ = self.helper.create_rc_tag("1.2.0", "release/1.2.0", rc_number=3)

        assert tag_name == "v1.2.0-rc.3"
        self.mock_repo.create_git_ref.assert_called_once_with(
            ref="refs/tags/v1.2.0-rc.3", sha="abc123"
        )

    # -- create_release_branch --

    def test_create_release_branch_creates_ref_from_tag(
        self, mocker: MockerFixture
    ) -> None:
        source_ref = mocker.Mock(object=mocker.Mock(sha="abc123", type="commit"))
        self.mock_repo.get_git_ref.return_value = source_ref

        commit_sha = self.helper.create_release_branch("1.3.1", source_tag="v1.3.0")

        assert commit_sha == "abc123"
        self.mock_repo.get_git_ref.assert_called_once_with("tags/v1.3.0")
        self.mock_repo.create_git_ref.assert_called_once_with(
            ref="refs/heads/release/1.3.1", sha="abc123"
        )

    def test_create_release_branch_dereferences_annotated_tag(
        self, mocker: MockerFixture
    ) -> None:
        tag_object = mocker.Mock(sha="tag_obj_sha", type="tag")
        self.mock_repo.get_git_ref.return_value = mocker.Mock(object=tag_object)
        self.mock_repo.get_git_tag.return_value = mocker.Mock(
            object=mocker.Mock(sha="commit_sha")
        )

        commit_sha = self.helper.create_release_branch("1.3.1", source_tag="v1.3.0")

        assert commit_sha == "commit_sha"
        self.mock_repo.get_git_tag.assert_called_once_with("tag_obj_sha")

    def test_create_release_branch_raises_when_tag_not_found(self) -> None:
        self.mock_repo.get_git_ref.side_effect = UnknownObjectException(404, {}, {})

        with pytest.raises(ValueError, match="not found on GitHub"):
            self.helper.create_release_branch("1.3.1", source_tag="v9.9.9")

    # -- trigger_promotion --

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

    def test_validate_tag_exists_passes_when_tag_found(self) -> None:
        self.helper.validate_tag_exists("v1.0.0-rc.1")

        self.mock_repo.get_git_ref.assert_called_once_with("tags/v1.0.0-rc.1")

    def test_validate_tag_exists_raises_when_tag_not_found(self) -> None:
        self.mock_repo.get_git_ref.side_effect = UnknownObjectException(404, {}, {})

        with pytest.raises(ValueError, match="does not exist"):
            self.helper.validate_tag_exists("v1.0.0-rc.1")

    def test_validate_release_branch_exists_passes_when_branch_found(
        self,
    ) -> None:
        self.helper.validate_release_branch_exists("1.0.0")

        self.mock_repo.get_branch.assert_called_once_with("release/1.0.0")

    def test_validate_release_branch_exists_raises_when_branch_not_found(
        self,
    ) -> None:
        self.mock_repo.get_branch.side_effect = UnknownObjectException(404, {}, {})

        with pytest.raises(ValueError, match="No release branch"):
            self.helper.validate_release_branch_exists("1.0.0")

    # -- validate_not_finalised --

    def test_validate_not_finalised_passes_when_tag_absent(self) -> None:
        self.mock_repo.get_git_ref.side_effect = UnknownObjectException(404, {}, {})

        self.helper.validate_not_finalised("1.0.0")

        self.mock_repo.get_git_ref.assert_called_once_with("tags/v1.0.0")

    def test_validate_not_finalised_raises_when_tag_exists(self) -> None:
        with pytest.raises(ValueError, match="already finalised"):
            self.helper.validate_not_finalised("1.0.0")

    # -- validate_release_branch_does_not_exist --

    def test_validate_release_branch_does_not_exist_passes_when_absent(
        self,
    ) -> None:
        self.mock_repo.get_branch.side_effect = UnknownObjectException(404, {}, {})

        self.helper.validate_release_branch_does_not_exist("1.0.0")

        self.mock_repo.get_branch.assert_called_once_with("release/1.0.0")

    def test_validate_release_branch_does_not_exist_raises_when_exists(
        self,
    ) -> None:
        with pytest.raises(ValueError, match="already exists"):
            self.helper.validate_release_branch_does_not_exist("1.0.0")

    # -- create_final_tag --

    def test_create_final_tag_creates_tag_and_ref_when_new(
        self, mocker: MockerFixture
    ) -> None:
        self.mock_repo.get_git_ref.side_effect = [
            UnknownObjectException(404, {}, {}),  # tag doesn't exist
            mocker.Mock(object=mocker.Mock(sha="abc123", type="commit")),  # source ref
        ]
        mock_tag = mocker.Mock(sha="tag_obj_sha")
        self.mock_repo.create_git_tag.return_value = mock_tag

        result = self.helper.create_final_tag(
            "v1.2.0", "v1.2.0-rc.1", message="Release v1.2.0"
        )

        assert result is True
        self.mock_repo.create_git_tag.assert_called_once_with(
            tag="v1.2.0",
            message="Release v1.2.0",
            object="abc123",
            type="commit",
        )
        self.mock_repo.create_git_ref.assert_called_once_with(
            ref="refs/tags/v1.2.0", sha="tag_obj_sha"
        )

    def test_create_final_tag_returns_false_when_tag_exists(self) -> None:
        result = self.helper.create_final_tag(
            "v1.2.0", "v1.2.0-rc.1", message="Release v1.2.0"
        )

        assert result is False
        self.mock_repo.create_git_tag.assert_not_called()

    def test_create_final_tag_raises_when_source_tag_not_found(self) -> None:
        self.mock_repo.get_git_ref.side_effect = [
            UnknownObjectException(404, {}, {}),  # tag doesn't exist
            UnknownObjectException(404, {}, {}),  # source tag not found
        ]

        with pytest.raises(ValueError, match="not found on GitHub"):
            self.helper.create_final_tag(
                "v1.2.0", "v1.2.0-rc.1", message="Release v1.2.0"
            )

    def test_create_final_tag_dereferences_annotated_source_tag(
        self, mocker: MockerFixture
    ) -> None:
        tag_object = mocker.Mock(sha="tag_obj_sha", type="tag")
        self.mock_repo.get_git_ref.side_effect = [
            UnknownObjectException(404, {}, {}),  # tag doesn't exist
            mocker.Mock(object=tag_object),  # source ref is annotated tag
        ]
        self.mock_repo.get_git_tag.return_value = mocker.Mock(
            object=mocker.Mock(sha="commit_sha")
        )
        mock_tag = mocker.Mock(sha="new_tag_sha")
        self.mock_repo.create_git_tag.return_value = mock_tag

        self.helper.create_final_tag("v1.2.0", "v1.2.0-rc.1", message="Release v1.2.0")

        self.mock_repo.get_git_tag.assert_called_once_with("tag_obj_sha")
        self.mock_repo.create_git_tag.assert_called_once_with(
            tag="v1.2.0",
            message="Release v1.2.0",
            object="commit_sha",
            type="commit",
        )

    # -- get_mergeback_count --

    def test_get_mergeback_count_returns_ahead_by(self, mocker: MockerFixture) -> None:
        mock_comparison = mocker.Mock(ahead_by=3)
        self.mock_repo.compare.return_value = mock_comparison

        result = self.helper.get_mergeback_count("release/1.2.0")

        assert result == 3
        self.mock_repo.compare.assert_called_once_with("main", "release/1.2.0")

    def test_get_mergeback_count_returns_zero_when_no_diff(
        self, mocker: MockerFixture
    ) -> None:
        mock_comparison = mocker.Mock(ahead_by=0)
        self.mock_repo.compare.return_value = mock_comparison

        result = self.helper.get_mergeback_count("release/1.2.0")

        assert result == 0

    # -- is_ancestor_of_main --

    def test_is_ancestor_of_main_true_when_behind(self, mocker: MockerFixture) -> None:
        self.mock_repo.compare.return_value = mocker.Mock(status="behind")

        assert self.helper.is_ancestor_of_main("abc123") is True
        self.mock_repo.compare.assert_called_once_with("main", "abc123")

    def test_is_ancestor_of_main_true_when_identical(
        self, mocker: MockerFixture
    ) -> None:
        self.mock_repo.compare.return_value = mocker.Mock(status="identical")

        assert self.helper.is_ancestor_of_main("abc123") is True

    def test_is_ancestor_of_main_false_when_ahead(self, mocker: MockerFixture) -> None:
        self.mock_repo.compare.return_value = mocker.Mock(status="ahead")

        assert self.helper.is_ancestor_of_main("abc123") is False

    def test_is_ancestor_of_main_false_when_diverged(
        self, mocker: MockerFixture
    ) -> None:
        self.mock_repo.compare.return_value = mocker.Mock(status="diverged")

        assert self.helper.is_ancestor_of_main("abc123") is False

    def test_is_ancestor_of_main_false_when_commit_not_found(self) -> None:
        self.mock_repo.compare.side_effect = UnknownObjectException(404, {}, {})

        assert self.helper.is_ancestor_of_main("doesnotexist") is False

    # -- find_previous_stable_release --

    def test_find_previous_stable_release_returns_first_stable_tag(
        self, mocker: MockerFixture
    ) -> None:
        releases = [
            mocker.Mock(draft=False, prerelease=False, tag_name="v1.0.0"),
        ]
        self.mock_repo.get_releases.return_value = releases

        result = self.helper.find_previous_stable_release("v2.0.0")

        assert result == "v1.0.0"

    def test_find_previous_stable_release_skips_drafts_and_prereleases(
        self, mocker: MockerFixture
    ) -> None:
        releases = [
            mocker.Mock(draft=True, prerelease=False, tag_name="v3.0.0"),
            mocker.Mock(draft=False, prerelease=True, tag_name="v2.0.0-rc.1"),
            mocker.Mock(draft=False, prerelease=False, tag_name="v1.0.0"),
        ]
        self.mock_repo.get_releases.return_value = releases

        result = self.helper.find_previous_stable_release("v2.0.0")

        assert result == "v1.0.0"

    def test_find_previous_stable_release_skips_excluded_tag(
        self, mocker: MockerFixture
    ) -> None:
        releases = [
            mocker.Mock(draft=False, prerelease=False, tag_name="v2.0.0"),
            mocker.Mock(draft=False, prerelease=False, tag_name="v1.0.0"),
        ]
        self.mock_repo.get_releases.return_value = releases

        result = self.helper.find_previous_stable_release("v2.0.0")

        assert result == "v1.0.0"

    def test_find_previous_stable_release_returns_none_when_empty(
        self,
    ) -> None:
        self.mock_repo.get_releases.return_value = []

        result = self.helper.find_previous_stable_release("v1.0.0")

        assert result is None

    # -- publish_stable_release --

    def test_publish_stable_release_creates_release_when_none_exists(
        self,
    ) -> None:
        self.mock_repo.get_release.side_effect = UnknownObjectException(404, {}, {})
        self.mock_repo.generate_release_notes.return_value.body = "notes"

        self.helper.publish_stable_release("v1.0.0", "v0.9.0")

        self.mock_repo.create_git_release.assert_called_once_with(
            tag="v1.0.0",
            name="v1.0.0",
            message="notes",
            make_latest="true",
        )

    def test_publish_stable_release_deletes_draft_then_creates(
        self, mocker: MockerFixture
    ) -> None:
        mock_existing = mocker.Mock(draft=True)
        self.mock_repo.get_release.return_value = mock_existing
        self.mock_repo.generate_release_notes.return_value.body = "notes"

        self.helper.publish_stable_release("v1.0.0", None)

        mock_existing.delete_release.assert_called_once()
        self.mock_repo.create_git_release.assert_called_once()

    def test_publish_stable_release_skips_when_published_exists(
        self, mocker: MockerFixture
    ) -> None:
        mock_existing = mocker.Mock(draft=False)
        self.mock_repo.get_release.return_value = mock_existing

        self.helper.publish_stable_release("v1.0.0", None)

        self.mock_repo.create_git_release.assert_not_called()

    def test_publish_stable_release_passes_previous_tag(self) -> None:
        self.mock_repo.get_release.side_effect = UnknownObjectException(404, {}, {})
        self.mock_repo.generate_release_notes.return_value.body = "notes"

        self.helper.publish_stable_release("v1.0.0", "v0.9.0")

        call_kwargs = self.mock_repo.generate_release_notes.call_args.kwargs
        assert call_kwargs["previous_tag_name"] == "v0.9.0"

    def test_publish_stable_release_uses_notset_when_no_previous(
        self,
    ) -> None:
        self.mock_repo.get_release.side_effect = UnknownObjectException(404, {}, {})
        self.mock_repo.generate_release_notes.return_value.body = "notes"

        self.helper.publish_stable_release("v1.0.0", None)

        call_kwargs = self.mock_repo.generate_release_notes.call_args.kwargs
        assert call_kwargs["previous_tag_name"] is NotSet

    # -- annotate_release_with_mergeback --

    def test_annotate_release_with_mergeback_appends_note(
        self, mocker: MockerFixture
    ) -> None:
        mock_release = mocker.Mock(title="v1.0.0", body="Existing notes")
        self.mock_repo.get_release.return_value = mock_release

        self.helper.annotate_release_with_mergeback("v1.0.0", "release/1.0.0", 3)

        mock_release.update_release.assert_called_once()
        call_kwargs = mock_release.update_release.call_args.kwargs
        assert "Existing notes" in call_kwargs["message"]
        assert "Merge-back required" in call_kwargs["message"]
        assert "3 commit(s)" in call_kwargs["message"]

    # -- create_mergeback_issue --

    def test_create_mergeback_issue_creates_issue_with_correct_title(
        self,
    ) -> None:
        self.mock_repo.full_name = "owner/repo"
        self.mock_repo.create_issue.return_value.html_url = (
            "https://github.com/owner/repo/issues/1"
        )

        self.helper.create_mergeback_issue("v1.0.0", "release/1.0.0", 3)

        call_kwargs = self.mock_repo.create_issue.call_args.kwargs
        assert call_kwargs["title"] == "Merge back: v1.0.0"

    def test_create_mergeback_issue_body_contains_instructions(
        self,
    ) -> None:
        self.mock_repo.full_name = "owner/repo"
        self.mock_repo.create_issue.return_value.html_url = (
            "https://github.com/owner/repo/issues/1"
        )

        self.helper.create_mergeback_issue("v1.0.0", "release/1.0.0", 3)

        call_kwargs = self.mock_repo.create_issue.call_args.kwargs
        assert "merge-back/1.0.0" in call_kwargs["body"]
        assert "owner/repo" in call_kwargs["body"]

    def test_create_mergeback_issue_returns_issue_url(self) -> None:
        self.mock_repo.full_name = "owner/repo"
        self.mock_repo.create_issue.return_value.html_url = (
            "https://github.com/owner/repo/issues/1"
        )

        result = self.helper.create_mergeback_issue("v1.0.0", "release/1.0.0", 3)

        assert result == "https://github.com/owner/repo/issues/1"
