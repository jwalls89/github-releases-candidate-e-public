import pytest
from packaging.version import Version

from release_tools.version import parse


class TestNormaliseAndValidate:
    def test_plain_semver(self):
        assert normalise_and_validate("1.2.0") == Version("1.2.0")

    def test_strips_v_prefix(self):
        assert normalise_and_validate("v1.2.0") == Version("1.2.0")

    def test_rejects_two_part_version(self):
        with pytest.raises(ValueError, match="MAJOR.MINOR.PATCH"):
            normalise_and_validate("1.2")

    def test_rejects_four_part_version(self):
        with pytest.raises(ValueError, match="MAJOR.MINOR.PATCH"):
            normalise_and_validate("1.2.3.4")

    def test_rejects_non_numeric(self):
        with pytest.raises(ValueError, match="semver format"):
            normalise_and_validate("abc")

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="semver format"):
            normalise_and_validate("")

    def test_rejects_prerelease_suffix(self):
        with pytest.raises(ValueError, match="MAJOR.MINOR.PATCH"):
            normalise_and_validate("1.2.0-rc.1")

    def test_returns_version_object(self):
        result = normalise_and_validate("3.10.1")
        assert isinstance(result, Version)
        assert result.major == 3
        assert result.minor == 10
        assert result.micro == 1
