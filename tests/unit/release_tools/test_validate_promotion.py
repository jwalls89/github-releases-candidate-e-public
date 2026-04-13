"""Unit tests for ValidatePromotion."""

from unittest import mock

import pytest
from pytest_mock import MockerFixture
from semver import Version

from release_tools.github import GitHubHelper
from release_tools.validate_promotion import ValidatePromotion


class TestValidatePromotion:
    """Tests for ValidatePromotion."""

    @pytest.fixture(autouse=True)
    def setup(self, mocker: MockerFixture) -> None:
        self.mock_github = mocker.Mock(spec_set=GitHubHelper)
        mocker.patch(
            "release_tools.validate_promotion.ReleaseVersionHelper.parse_rc",
            return_value=Version.parse("1.2.0-rc.1"),
        )

    def test_run_returns_normalised_tag_name(self) -> None:
        result = ValidatePromotion(self.mock_github, "v1.2.0-rc.1").run()

        assert result == "v1.2.0-rc.1"

    def test_run_validates_tag_exists(self) -> None:
        ValidatePromotion(self.mock_github, "v1.2.0-rc.1").run()

        self.mock_github.validate_tag_exists.assert_called_once_with("v1.2.0-rc.1")

    def test_run_validates_release_branch_exists(self) -> None:
        ValidatePromotion(self.mock_github, "v1.2.0-rc.1").run()

        self.mock_github.validate_release_branch_exists.assert_called_once_with("1.2.0")

    def test_run_raises_when_invalid_rc_tag(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "release_tools.validate_promotion.ReleaseVersionHelper.parse_rc",
            side_effect=ValueError("RC tag"),
        )

        with pytest.raises(ValueError, match="RC tag"):
            ValidatePromotion(self.mock_github, "1.2.0").run()

    def test_run_raises_when_tag_not_found(self) -> None:
        self.mock_github.validate_tag_exists.side_effect = ValueError("does not exist")

        with pytest.raises(ValueError, match="does not exist"):
            ValidatePromotion(self.mock_github, "v1.2.0-rc.1").run()

    def test_run_raises_when_branch_not_found(self) -> None:
        self.mock_github.validate_release_branch_exists.side_effect = ValueError(
            "No release branch"
        )

        with pytest.raises(ValueError, match="No release branch"):
            ValidatePromotion(self.mock_github, "v1.2.0-rc.1").run()

    def test_run_checks_tag_before_branch(self) -> None:
        ValidatePromotion(self.mock_github, "v1.2.0-rc.1").run()

        methods = [call[0] for call in self.mock_github.method_calls]
        assert methods.index("validate_tag_exists") < methods.index(
            "validate_release_branch_exists"
        )

    @mock.patch.dict("os.environ", {}, clear=True)
    def test_run_prints_version_when_no_github_output(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        ValidatePromotion(self.mock_github, "v1.2.0-rc.1").run()

        captured = capsys.readouterr()
        assert "version=v1.2.0-rc.1" in captured.out

    def test_run_writes_to_github_output(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        output_file = tmp_path / "github_output"
        output_file.write_text("")

        with mock.patch.dict("os.environ", {"GITHUB_OUTPUT": str(output_file)}):
            ValidatePromotion(self.mock_github, "v1.2.0-rc.1").run()

        assert "version=v1.2.0-rc.1" in output_file.read_text()
