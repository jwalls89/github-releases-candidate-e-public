"""Unit tests for ReleaseVersionHelper."""

import pytest
from semver import Version

from release_tools.version import ReleaseVersionHelper


class TestReleaseVersionHelper:
    """Tests for ReleaseVersionHelper."""

    def test_parse_returns_version_when_valid_semver(self) -> None:
        result = ReleaseVersionHelper.parse("1.2.0")

        assert result == Version.parse("1.2.0")

    def test_parse_returns_version_when_v_prefix(self) -> None:
        result = ReleaseVersionHelper.parse("v1.2.0")

        assert result == Version.parse("1.2.0")

    def test_parse_raises_value_error_when_invalid_input(self) -> None:
        with pytest.raises(ValueError, match="semver format"):
            ReleaseVersionHelper.parse("abc")

    def test_parse_raises_value_error_when_empty_string(self) -> None:
        with pytest.raises(ValueError, match="semver format"):
            ReleaseVersionHelper.parse("")

    def test_check_version_is_higher_passes_when_version_higher(self) -> None:
        ReleaseVersionHelper.check_version_is_higher(
            Version.parse("2.0.0"),
            Version.parse("1.0.0"),
        )

    def test_check_version_is_higher_raises_when_version_lower(self) -> None:
        with pytest.raises(ValueError, match="not higher"):
            ReleaseVersionHelper.check_version_is_higher(
                Version.parse("1.0.0"),
                Version.parse("2.0.0"),
            )

    def test_check_version_is_higher_raises_when_version_equal(self) -> None:
        with pytest.raises(ValueError, match="not higher"):
            ReleaseVersionHelper.check_version_is_higher(
                Version.parse("1.0.0"),
                Version.parse("1.0.0"),
            )

    def test_check_version_is_higher_passes_when_latest_release_is_none(self) -> None:
        ReleaseVersionHelper.check_version_is_higher(
            Version.parse("1.0.0"),
            None,
        )
