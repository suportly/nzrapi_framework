"""
Serializer system inspired by Django REST Framework
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union

from sqlalchemy import Column
from sqlalchemy.ext.asyncio import AsyncSession

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
        self.field_name: Optional[str] = None
        self.parent: Optional["BaseSerializer"] = None

    def bind(self, field_name: str, parent: "BaseSerializer"):
        self.field_name = field_name
        self.parent = parent

    def get_attribute(self, instance: Any) -> Any:
        source = self.source or self.field_name
        return getattr(instance, source, None)

    def get_value(self, data: Dict[str, Any]) -> Any:
        return data.get(self.field_name)

    def to_internal_value(self, data: Any) -> Any:
        return data

    def to_representation(self, value: Any) -> Any:
        return value

    def run_validation(self, data: Any) -> Any:
        if data is None:
            if not self.allow_null:
                raise ValidationError("This field cannot be null.")
            return None

        value = self.to_internal_value(data)
        for validator in self.validators:
            try:
                validator(value)
            except ValidatorError as e:
                raise ValidationError(str(e))
        return value


class CharField(Field):
    def __init__(self, max_length: Optional[int] = None, **kwargs):
        self.max_length = max_length
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> str:
        value = str(data)
        if self.max_length and len(value) > self.max_length:
            raise ValidationError(f"Ensure this field has no more than {self.max_length} characters.")
        return value


class IntegerField(Field):
    def __init__(self, min_value: Optional[int] = None, max_value: Optional[int] = None, **kwargs):
        self.min_value = min_value
        self.max_value = max_value
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> int:
        try:
            value = int(data)
        except (TypeError, ValueError):
            raise ValidationError("A valid integer is required.")

        if self.min_value is not None and value < self.min_value:
            raise ValidationError(f"Ensure this value is greater than or equal to {self.min_value}.")

        if self.max_value is not None and value > self.max_value:
            raise ValidationError(f"Ensure this value is less than or equal to {self.max_value}.")

        return value


class BooleanField(Field):
    def to_internal_value(self, data: Any) -> bool:
        true_values = {True, "true", "True", "1", 1}
        false_values = {False, "false", "False", "0", 0}
        if data in true_values:
            return True
        if data in false_values:
            return False
        raise ValidationError("A valid boolean is required.")


class DateTimeField(Field):
    def to_internal_value(self, data: Any) -> datetime:
        if isinstance(data, datetime):
            return data
        try:
            return datetime.fromisoformat(str(data))
        except (TypeError, ValueError):
            raise ValidationError("A valid ISO-formatted datetime is required.")


class ListField(Field):
    def __init__(self, child: Field, **kwargs):
        self.child = child
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> list:
        if not isinstance(data, list):
            raise ValidationError("A valid list is required.")

        internal_list = []
        errors = []
        for index, item in enumerate(data):
            try:
                internal_list.append(self.child.run_validation(item))
            except ValidationError as e:
                errors.append({index: e.args[0]})

        if errors:
            raise ValidationError(errors={'errors': errors})

        return internal_list


class DictField(Field):
    def to_internal_value(self, data: Any) -> dict:
        if not isinstance(data, dict):
            raise ValidationError("A valid dict is required.")
        return data


# ... (other field types can be similarly refactored) ...


class BaseSerializer:
    if TYPE_CHECKING:
        fields: Dict[str, Field]

    def __init__(self, instance=None, data: Optional[dict] = None, **kwargs):
        self.instance = instance
        if data is not None:
            self.initial_data = data
        self.many = kwargs.get("many", False)
        self._validated_data: Optional[Dict[str, Any]] = None
        self._errors: Dict[str, Any] = {}
        self.fields = self._get_fields()
        for field_name, field in self.fields.items():
            field.bind(field_name, self)

    @classmethod
    def _get_fields(cls) -> Dict[str, Field]:
        return {name: field for name, field in cls.__dict__.items() if isinstance(field, Field)}

    def is_valid(self, raise_exception=False) -> bool:
        if not hasattr(self, "initial_data"):
            raise TypeError(
                "Cannot call .is_valid() as no `data=` keyword argument was passed when instantiating the serializer."
            )

        validated_data = {}
        errors = {}

        for field_name, field in self.fields.items():
            if field.read_only:
                continue

            try:
                value = field.get_value(self.initial_data)
                if value is None and field.default is not None:
                    value = field.default
                if field.required and value is None:
                    errors[field_name] = ["This field is required."]
                    continue
                if value is not None:
                    validated_data[field_name] = field.run_validation(value)
            except ValidationError as e:
                errors[field_name] = e.args[0]

        if not errors:
            try:
                if hasattr(self, "validate"):
                    validated_data = self.validate(validated_data)
            except ValidationError as e:
                errors["non_field_errors"] = e.args[0]

        if errors:
            self._errors = errors
            if raise_exception:
                raise ValidationError(errors=self._errors)
            return False

        self._validated_data = validated_data
        return True

    @property
    def data(self):
        if self.many:
            return [self.to_representation(item) for item in self.instance]
        return self.to_representation(self.instance)

    @property
    def errors(self):
        return self._errors

    @property
    def validated_data(self):
        return self._validated_data

    def to_representation(self, instance: Any) -> Dict[str, Any]:
        ret = {}
        for field_name, field in self.fields.items():
            if not field.write_only:
                attribute = field.get_attribute(instance)
                ret[field_name] = field.to_representation(attribute)
        return ret

    async def save(self, session: AsyncSession, **kwargs):
        assert not self._errors, "Cannot call .save() on an invalid serializer."
        validated_data = {**self.validated_data, **kwargs}

        if self.instance is not None:
            self.instance = await self.update(self.instance, validated_data, session)
        else:
            self.instance = await self.create(validated_data, session)

        return self.instance

    async def create(self, validated_data: dict, session: AsyncSession):
        raise NotImplementedError("`create()` must be implemented.")

    async def update(self, instance: Any, validated_data: dict, session: AsyncSession):
        raise NotImplementedError("`update()` must be implemented.")


class ModelSerializer(BaseSerializer):
    class Meta:
        model: Type[Any]
        fields: Union[List[str], str] = "__all__"
        read_only_fields: List[str] = []

    async def create(self, validated_data: dict, session: AsyncSession):
        ModelClass = self.Meta.model
        instance = ModelClass()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance

    async def update(self, instance: Any, validated_data: dict, session: AsyncSession):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance

    @classmethod
    def _get_fields(cls) -> Dict[str, Field]:
        declared_fields = super()._get_fields()

        if not hasattr(cls, "Meta") or not hasattr(cls.Meta, "model"):
            return declared_fields

        model = cls.Meta.model
        model_fields = {c.name: c for c in model.__table__.columns}

        field_names: Union[List[str], str]
        if hasattr(cls.Meta, "fields"):
            field_names = cls.Meta.fields
        else:
            field_names = []

        field_names_list: List[str]
        if field_names == "__all__":
            field_names_list = list(model_fields.keys())
        else:
            field_names_list = field_names  # type: ignore

        final_fields = declared_fields.copy()

        for field_name in field_names_list:
            if field_name in final_fields:
                continue

            column = model_fields.get(field_name)
            if column is None:
                continue

            kwargs = {}
            if hasattr(cls.Meta, "read_only_fields") and field_name in cls.Meta.read_only_fields:
                kwargs["read_only"] = True

            if str(column.type).startswith("VARCHAR") or str(column.type).startswith("TEXT"):
                final_fields[field_name] = CharField(**kwargs)
            elif str(column.type).startswith("INTEGER"):
                final_fields[field_name] = IntegerField(**kwargs)

        return final_fields
