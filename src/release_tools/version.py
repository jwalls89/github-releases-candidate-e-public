"""Version parsing and validation."""

import re

from semver import Version


class ReleaseVersionHelper:
    """Static utilities for parsing and validating release versions."""

    @staticmethod
    def parse(raw_version: str) -> Version:
        """Parse a version string into a ``semver.Version``.

        Strips an optional 'v' prefix and requires valid semver.

        Raises:
            ValueError: If the input is not valid semver.

        """
        stripped = raw_version.removeprefix("v")

        try:
            return Version.parse(stripped)
        except ValueError:
            msg = (
                "Version must be in semver format"
                f" (e.g., 1.2.0 or v1.2.0), got: {raw_version}"
            )
            raise ValueError(msg) from None

    @staticmethod
    def check_version_is_higher(
        version: Version,
        latest_release: Version | None,
    ) -> None:
        """Raise if *version* is not higher than *latest_release*.

        Passes silently when there is no previous release.

        Raises:
            ValueError: If version is not higher than the latest release.

        """
        if latest_release is None:
            return

        if version <= latest_release:
            msg = (
                f"Version {version} is not higher"
                f" than the latest release {latest_release}"
            )
            raise ValueError(msg)

    @staticmethod
    def parse_rc(raw_version: str) -> Version:
        """Parse an RC tag string into a ``semver.Version``.

        Strips an optional 'v' prefix and validates the pre-release
        suffix matches ``rc.N``.

        Raises:
            ValueError: If the input is not a valid RC tag.

        """
        version = ReleaseVersionHelper.parse(raw_version)

        if not version.prerelease or not re.match(r"^rc\.\d+$", version.prerelease):
            msg = f"Version must be an RC tag (e.g., v1.2.0-rc.1), got: {raw_version}"
            raise ValueError(msg)

        return version
