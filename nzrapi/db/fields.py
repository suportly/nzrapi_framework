from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)


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
