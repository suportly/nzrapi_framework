from enum import Enum
from typing import Any, Type, TypeVar

from sqlalchemy import JSON as JSONType
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    Float,
    Integer,
    String,
    Text,
)

E = TypeVar("E", bound=Enum)


def StringColumn(max_length: int = 255, **kwargs):
    """A string column with a max length."""
    return Column(String(max_length), **kwargs)


def IntegerColumn(**kwargs):
    """An integer column."""
    return Column(Integer, **kwargs)


def TextColumn(**kwargs):
    """A text column for unlimited length text."""
    return Column(Text, **kwargs)


def FloatColumn(**kwargs):
    """A float column."""
    return Column(Float, **kwargs)


def BooleanColumn(**kwargs):
    """A boolean column."""
    return Column(Boolean, **kwargs)


def DateTimeColumn(**kwargs):
    """A datetime column."""
    return Column(DateTime, **kwargs)


def JSONColumn(**kwargs):
    """A JSON column for storing JSON data."""
    return Column(JSONType, **kwargs)


def EnumColumn(enum_type: Type[E], **kwargs) -> Column:
    """A column that stores an enum value.

    Args:
        enum_type: The Python enum class to use for this column
        **kwargs: Additional arguments to pass to the SQLAlchemy Column

    Returns:
        A SQLAlchemy Column configured to store the enum values
    """
    return Column(SQLEnum(enum_type), **kwargs)
