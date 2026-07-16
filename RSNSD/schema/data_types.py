"""
Supported dataset data types.
"""

from enum import Enum


class DataType(str, Enum):

    INTEGER = "int"

    FLOAT = "float"

    STRING = "string"

    BOOLEAN = "bool"

    DATETIME = "datetime"

    CATEGORY = "category"