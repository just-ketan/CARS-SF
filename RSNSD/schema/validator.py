"""
Schema validation utilities.

Ensures that the feature registry is internally consistent before
any schema artifacts are generated.
"""

from .exceptions import SchemaValidationError


class SchemaValidator:

    @staticmethod
    def validate(features):

        SchemaValidator._validate_unique_names(features)

        SchemaValidator._validate_ranges(features)

        SchemaValidator._validate_roles(features)

        SchemaValidator._validate_descriptions(features)

    @staticmethod
    def _validate_unique_names(features):

        names = set()

        for feature in features:

            if feature.name in names:

                raise SchemaValidationError(
                    f"Duplicate feature name: {feature.name}"
                )

            names.add(feature.name)

    @staticmethod
    def _validate_ranges(features):

        for feature in features:

            if (
                feature.minimum is not None
                and feature.maximum is not None
                and feature.minimum > feature.maximum
            ):

                raise SchemaValidationError(
                    f"Invalid range for '{feature.name}' "
                    f"({feature.minimum} > {feature.maximum})"
                )

    @staticmethod
    def _validate_roles(features):

        for feature in features:

            if feature.ml_role is None:

                raise SchemaValidationError(
                    f"{feature.name} has no ML role."
                )

    @staticmethod
    def _validate_descriptions(features):

        for feature in features:

            if not feature.description.strip():

                raise SchemaValidationError(
                    f"{feature.name} has empty description."
                )