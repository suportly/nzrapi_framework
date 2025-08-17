"""
Validation utilities for nzrRest framework
"""

import re
from typing import Any, Callable, Dict, List, Optional, Union

from email_validator import EmailNotValidError, validate_email


class ValidationError(Exception):
    """Validation error exception"""

    pass


class BaseValidator:
    """Base validator class"""

    message = "Value is not valid"

    def __call__(self, value: Any) -> Any:
        """Validate the value"""
        raise NotImplementedError

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class RequiredValidator(BaseValidator):
    """Validates that a value is present"""

    message = "This field is required"

    def __call__(self, value: Any) -> Any:
        if value is None or value == "":
            raise ValidationError(self.message)
        return value


class MinLengthValidator(BaseValidator):
    """Validates minimum string length"""

    def __init__(self, min_length: int):
        self.min_length = min_length
        self.message = f"Value must be at least {min_length} characters long"

    def __call__(self, value: Any) -> Any:
        if value is not None and len(str(value)) < self.min_length:
            raise ValidationError(self.message)
        return value


class MaxLengthValidator(BaseValidator):
    """Validates maximum string length"""

    def __init__(self, max_length: int):
        self.max_length = max_length
        self.message = f"Value must be no more than {max_length} characters long"

    def __call__(self, value: Any) -> Any:
        if value is not None and len(str(value)) > self.max_length:
            raise ValidationError(self.message)
        return value


class EmailValidator(BaseValidator):
    """Validates email addresses"""

    message = "Enter a valid email address"

    def __call__(self, value: Any) -> Any:
        if value is None:
            return value

        try:
            # Use email-validator library for robust validation
            validated_email = validate_email(str(value))
            return validated_email.email
        except EmailNotValidError:
            raise ValidationError(self.message)


class RegexValidator(BaseValidator):
    """Validates against a regular expression"""

    def __init__(self, pattern: str, message: Optional[str] = None):
        self.pattern = re.compile(pattern)
        self.message = message or f"Value must match pattern: {pattern}"

    def __call__(self, value: Any) -> Any:
        if value is not None and not self.pattern.match(str(value)):
            raise ValidationError(self.message)
        return value


class NumericRangeValidator(BaseValidator):
    """Validates numeric values within a range"""

    def __init__(
        self,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
    ):
        self.min_value = min_value
        self.max_value = max_value

        if min_value is not None and max_value is not None:
            self.message = f"Value must be between {min_value} and {max_value}"
        elif min_value is not None:
            self.message = f"Value must be at least {min_value}"
        elif max_value is not None:
            self.message = f"Value must be no more than {max_value}"
        else:
            self.message = "Invalid numeric value"

    def __call__(self, value: Any) -> Any:
        if value is None:
            return value

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            raise ValidationError("Value must be numeric")

        if self.min_value is not None and numeric_value < self.min_value:
            raise ValidationError(self.message)

        if self.max_value is not None and numeric_value > self.max_value:
            raise ValidationError(self.message)

        return value


class ChoicesValidator(BaseValidator):
    """Validates that value is in a list of choices"""

    def __init__(self, choices: List[Any]):
        self.choices = choices
        self.message = f"Value must be one of: {', '.join(map(str, choices))}"

    def __call__(self, value: Any) -> Any:
        if value is not None and value not in self.choices:
            raise ValidationError(self.message)
        return value


class FunctionValidator(BaseValidator):
    """Validates using a custom function"""

    def __init__(self, func: Callable[[Any], bool], message: str):
        self.func = func
        self.message = message

    def __call__(self, value: Any) -> Any:
        if value is not None and not self.func(value):
            raise ValidationError(self.message)
        return value


def validate_value(value: Any, validators: List[BaseValidator]) -> Any:
    """Run a value through a list of validators"""
    for validator in validators:
        value = validator(value)
    return value
