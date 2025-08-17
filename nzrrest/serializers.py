"""
Serializer system inspired by Django REST Framework
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union

from sqlalchemy import Column

from .exceptions import ValidationError
from .validators import BaseValidator
from .validators import ValidationError as ValidatorError
from .validators import validate_value


class Field:
    """Base field class for serializers"""

    def __init__(
        self,
        required: bool = True,
        allow_null: bool = False,
        default: Any = None,
        validators: Optional[List[BaseValidator]] = None,
        source: Optional[str] = None,
        read_only: bool = False,
        write_only: bool = False,
        help_text: Optional[str] = None,
    ):
        self.required = required
        self.allow_null = allow_null
        self.default = default
        self.validators = validators or []
        self.source = source
        self.read_only = read_only
        self.write_only = write_only
        self.help_text = help_text

        # Set at bind time
        self.field_name: Optional[str] = None
        self.parent: Optional["BaseSerializer"] = None

    def bind(self, field_name: str, parent: "BaseSerializer"):
        """Bind field to a serializer"""
        self.field_name = field_name
        self.parent = parent

    def get_attribute(self, instance: Any) -> Any:
        """Get attribute value from instance"""
        if self.source:
            attr_name = self.source
        else:
            attr_name = self.field_name

        if hasattr(instance, attr_name):
            return getattr(instance, attr_name)
        elif hasattr(instance, "__getitem__"):
            try:
                return instance[attr_name]
            except (KeyError, TypeError):
                pass

        return None

    def get_value(self, data: Dict[str, Any]) -> Any:
        """Get value from input data"""
        field_name = self.source or self.field_name

        if field_name in data:
            return data[field_name]
        elif self.default is not None:
            return self.default() if callable(self.default) else self.default
        elif not self.required:
            return None
        else:
            raise ValidationError(f"Field '{self.field_name}' is required")

    def validate(self, value: Any) -> Any:
        """Validate field value"""
        # Check for null values
        if value is None:
            if not self.allow_null:
                raise ValidationError(f"Field '{self.field_name}' cannot be null")
            return value

        # Run custom validators
        try:
            value = validate_value(value, self.validators)
        except ValidatorError as e:
            raise ValidationError(str(e))

        # Run field-specific validation
        return self.to_internal_value(value)

    def to_internal_value(self, data: Any) -> Any:
        """Convert input data to internal representation"""
        return data

    def to_representation(self, value: Any) -> Any:
        """Convert internal value to serialized representation"""
        return value


class CharField(Field):
    """String field"""

    def __init__(self, max_length: Optional[int] = None, **kwargs):
        self.max_length = max_length
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> str:
        value = str(data)
        if self.max_length and len(value) > self.max_length:
            raise ValidationError(f"String too long (max {self.max_length} characters)")
        return value


class IntegerField(Field):
    """Integer field"""

    def __init__(self, min_value: Optional[int] = None, max_value: Optional[int] = None, **kwargs):
        self.min_value = min_value
        self.max_value = max_value
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> int:
        try:
            value = int(data)
        except (TypeError, ValueError):
            raise ValidationError("Invalid integer value")

        if self.min_value is not None and value < self.min_value:
            raise ValidationError(f"Value must be at least {self.min_value}")

        if self.max_value is not None and value > self.max_value:
            raise ValidationError(f"Value must be no more than {self.max_value}")

        return value


class FloatField(Field):
    """Float field"""

    def to_internal_value(self, data: Any) -> float:
        try:
            return float(data)
        except (TypeError, ValueError):
            raise ValidationError("Invalid float value")


class BooleanField(Field):
    """Boolean field"""

    def to_internal_value(self, data: Any) -> bool:
        if isinstance(data, bool):
            return data

        # Handle string representations
        if isinstance(data, str):
            lower_data = data.lower()
            if lower_data in ("true", "1", "yes", "on"):
                return True
            elif lower_data in ("false", "0", "no", "off"):
                return False

        # Handle numeric values
        try:
            return bool(int(data))
        except (TypeError, ValueError):
            raise ValidationError("Invalid boolean value")


class DateTimeField(Field):
    """DateTime field"""

    def to_internal_value(self, data: Any) -> datetime:
        if isinstance(data, datetime):
            return data

        if isinstance(data, str):
            try:
                return datetime.fromisoformat(data.replace("Z", "+00:00"))
            except ValueError:
                raise ValidationError("Invalid datetime format. Use ISO format")

        raise ValidationError("Invalid datetime value")

    def to_representation(self, value: Optional[datetime]) -> Optional[str]:
        if value:
            return value.isoformat()
        return None


class ListField(Field):
    """List field with optional child field"""

    def __init__(self, child: Field, **kwargs):
        self.child = child
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> List[Any]:
        if not isinstance(data, list):
            raise ValidationError("Expected a list")

        if self.child:
            result = []
            for item in data:
                try:
                    result.append(self.child.to_internal_value(item))
                except ValidationError as e:
                    raise ValidationError(f"List item validation error: {e}")
            return result

        return data


class DictField(Field):
    """Dictionary field"""

    def to_internal_value(self, data: Any) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise ValidationError("Expected a dictionary")
        return data


class BaseSerializer:
    """Base serializer class inspired by DRF"""

    if TYPE_CHECKING:
        fields: Dict[str, Field]

    def __init__(self, instance=None, data=None, *, many=False, context=None, **kwargs):
        self.instance = instance
        self.initial_data = data
        self.many = many
        self.context = context or {}
        self._validated_data = None
        self._errors = None

        # Bind fields
        self.fields = self._get_fields()
        for field_name, field in self.fields.items():
            field.bind(field_name, self)

    @classmethod
    def _get_fields(cls) -> Dict[str, Field]:
        """Get fields from class definition"""
        fields = {}

        # Get declared fields
        for name in dir(cls):
            value = getattr(cls, name)
            if isinstance(value, Field):
                fields[name] = value

        return fields

    @property
    def data(self) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Get serialized data"""
        if self.instance is None:
            raise ValueError("Cannot serialize without instance")

        if self.many:
            return [self.to_representation(item) for item in self.instance]
        else:
            return self.to_representation(self.instance)

    @property
    def validated_data(self) -> Dict[str, Any]:
        """Get validated data after calling is_valid()"""
        if self._validated_data is None:
            raise ValueError("Must call is_valid() before accessing validated_data")
        return self._validated_data

    @property
    def errors(self) -> Dict[str, Any]:
        """Get validation errors"""
        if self._errors is None:
            raise ValueError("Must call is_valid() before accessing errors")
        return self._errors

    def is_valid(self, *, raise_exception: bool = False) -> bool:
        """Validate the input data"""
        if self.initial_data is None:
            self._errors = {"non_field_errors": ["No data provided"]}
            if raise_exception:
                raise ValidationError("No data provided")
            return False

        try:
            self._validated_data = self.to_internal_value(self.initial_data)
            self._errors = {}
            return True
        except ValidationError as e:
            self._errors = {"non_field_errors": [str(e)]}
            if raise_exception:
                raise e
            return False
        except Exception as e:
            self._errors = {"non_field_errors": [f"Unexpected error: {str(e)}"]}
            if raise_exception:
                raise ValidationError(f"Unexpected error: {str(e)}")
            return False

    def to_internal_value(self, data: Any) -> Dict[str, Any]:
        """Convert input data to validated internal representation"""
        if not isinstance(data, dict):
            raise ValidationError("Expected a dictionary")

        validated_data = {}
        errors = {}

        for field_name, field in self.fields.items():
            if field.write_only:
                continue

            try:
                value = field.get_value(data)
                validated_value = field.validate(value)
                validated_data[field_name] = validated_value
            except ValidationError as e:
                errors[field_name] = str(e)

        if errors:
            raise ValidationError(str(errors))

        # Run object-level validation
        validated_data = self.validate(validated_data)

        return validated_data

    def to_representation(self, instance: Any) -> Dict[str, Any]:
        """Convert instance to serialized representation"""
        data = {}

        for field_name, field in self.fields.items():
            if field.read_only:
                continue

            try:
                attribute = field.get_attribute(instance)
                value = field.to_representation(attribute)
                data[field_name] = value
            except Exception:
                # Skip fields that can't be serialized
                pass

        return data

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Object-level validation (override in subclasses)"""
        return data

    def create(self, validated_data: Dict[str, Any]) -> Any:
        """Create instance from validated data (override in subclasses)"""
        raise NotImplementedError("Subclasses must implement create()")

    def update(self, instance: Any, validated_data: Dict[str, Any]) -> Any:
        """Update instance with validated data (override in subclasses)"""
        raise NotImplementedError("Subclasses must implement update()")

    def save(self, **kwargs) -> Any:
        """Save the serializer data"""
        if not self.is_valid():
            raise ValidationError("Cannot save invalid data")

        validated_data = {**self.validated_data, **kwargs}

        if self.instance is not None:
            return self.update(self.instance, validated_data)
        else:
            return self.create(validated_data)


class ModelSerializer(BaseSerializer):
    """Serializer that works with SQLAlchemy models"""

    if TYPE_CHECKING:

        class _Meta:
            model: Type[Any]
            fields: Union[List[str], str]
            exclude: List[str]
            read_only_fields: List[str]
            extra_kwargs: Dict[str, Dict[str, Any]]

        Meta: _Meta

    @classmethod
    def _get_fields(cls) -> Dict[str, Field]:
        """Get fields from model and meta configuration"""
        fields = super()._get_fields()

        # If no explicit fields declared, infer from model
        if not fields and hasattr(cls, "Meta") and cls.Meta.model:
            fields = cls._get_model_fields()

        return fields

    @classmethod
    def _get_model_fields(cls) -> Dict[str, Field]:
        """Infer fields from SQLAlchemy model"""
        if not hasattr(cls, "Meta") or not cls.Meta.model:
            return {}

        model = cls.Meta.model
        fields = {}

        # Get model columns
        if hasattr(model, "__table__"):
            for column in model.__table__.columns:
                field_name = column.name

                # Skip excluded fields
                if hasattr(cls.Meta, "exclude") and cls.Meta.exclude and field_name in cls.Meta.exclude:
                    continue

                # Skip if not in explicit fields list
                if hasattr(cls.Meta, "fields") and cls.Meta.fields != "__all__" and field_name not in cls.Meta.fields:
                    continue

                # Create field based on column type
                field = cls._create_field_from_column(column)
                if field:
                    fields[field_name] = field

        return fields

    @classmethod
    def _create_field_from_column(cls, column: Column) -> Optional[Field]:
        """Create field from SQLAlchemy column"""
        # This is a simplified mapping - in reality you'd handle more types
        type_name = str(column.type)

        kwargs: Dict[str, Any] = {
            "required": not column.nullable and column.default is None,
            "allow_null": column.nullable,
        }

        field_class_map = {
            "VARCHAR": CharField,
            "TEXT": CharField,
            "INTEGER": IntegerField,
            "FLOAT": FloatField,
            "REAL": FloatField,
            "BOOLEAN": BooleanField,
            "DATETIME": DateTimeField,
            "TIMESTAMP": DateTimeField,
        }

        field_class: Type[Field] = CharField  # Default
        for type_key, f_class in field_class_map.items():
            if type_key in type_name:
                field_class = f_class
                break

        if field_class in [CharField] and hasattr(column.type, "length") and column.type.length:
            kwargs["max_length"] = column.type.length

        return field_class(**kwargs)

    def create(self, validated_data: Dict[str, Any]) -> Any:
        """Create model instance"""
        if not hasattr(self.Meta, "model") or not self.Meta.model:
            raise ValueError("Meta.model not specified")

        return self.Meta.model(**validated_data)

    def update(self, instance: Any, validated_data: Dict[str, Any]) -> Any:
        """Update model instance"""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        return instance
