"""
Application Profile Registry

Central registry for all traffic application profiles.

Every traffic generator, experiment and dataset builder
retrieves application definitions from this registry.
"""

from typing import Dict

from .application_profile import ApplicationProfile


PROFILE_REGISTRY: Dict[str, ApplicationProfile] = {}


def register(profile: ApplicationProfile) -> None:
    """
    Register an application profile.

    Raises:
        ValueError:
            If another profile with the same application_id
            already exists.
    """

    if profile.application_id in PROFILE_REGISTRY:

        raise ValueError(
            f"Duplicate application profile: {profile.application_id}"
        )

    PROFILE_REGISTRY[profile.application_id] = profile


def get(application_id: str) -> ApplicationProfile:
    """
    Retrieve a registered application profile.
    """

    return PROFILE_REGISTRY[application_id]


def list_profiles():
    """
    Return all registered application profiles.
    """

    return list(PROFILE_REGISTRY.values())