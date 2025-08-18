"""
Tests for NzrApi serializer system
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql.sqltypes import Integer, String

from nzrapi.exceptions import ValidationError
from nzrapi.serializers import (
    BaseSerializer,
    BooleanField,
    CharField,
    DateTimeField,
    DictField,
    IntegerField,
    ListField,
    ModelSerializer,
)


class TestFields:
    """Test individual field types"""

    def test_char_field(self):
        field = CharField(max_length=10)
        assert field.to_internal_value("hello") == "hello"
        with pytest.raises(ValidationError):
            field.to_internal_value("this is too long")

    def test_integer_field(self):
        field = IntegerField(min_value=0, max_value=100)
        assert field.to_internal_value("42") == 42
        assert field.to_internal_value(42) == 42
        with pytest.raises(ValidationError):
            field.to_internal_value(-1)
        with pytest.raises(ValidationError):
            field.to_internal_value(101)
        with pytest.raises(ValidationError):
            field.to_internal_value("not a number")

    def test_boolean_field(self):
        field = BooleanField()
        assert field.to_internal_value(True) is True
        assert field.to_internal_value("true") is True
        assert field.to_internal_value("1") is True
        assert field.to_internal_value(1) is True
        assert field.to_internal_value(False) is False
        assert field.to_internal_value("false") is False
        assert field.to_internal_value("0") is False
        assert field.to_internal_value(0) is False

    def test_datetime_field(self):
        field = DateTimeField()
        dt = datetime.now()
        assert field.to_internal_value(dt) == dt
        iso_string = "2024-01-01T12:00:00"
        result = field.to_internal_value(iso_string)
        assert isinstance(result, datetime)
        with pytest.raises(ValidationError):
            field.to_internal_value("not a date")

    def test_list_field(self):
        field = ListField(child=IntegerField())
        assert field.to_internal_value([1, 2, 3]) == [1, 2, 3]
        assert field.to_internal_value(["1", "2", "3"]) == [1, 2, 3]
        with pytest.raises(ValidationError):
            field.to_internal_value([1, "not a number", 3])
        with pytest.raises(ValidationError):
            field.to_internal_value("not a list")

    def test_dict_field(self):
        field = DictField()
        data = {"key": "value"}
        assert field.to_internal_value(data) == data
        with pytest.raises(ValidationError):
            field.to_internal_value("not a dict")


class TestBaseSerializer:
    """Test BaseSerializer functionality"""

    def test_simple_serializer(self):
        class TestSerializer(BaseSerializer):
            name = CharField(max_length=50)
            age = IntegerField(min_value=0)
            active = BooleanField()

        data = {"name": "John", "age": 30, "active": True}
        serializer = TestSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data == data

    def test_serializer_validation_errors(self):
        class TestSerializer(BaseSerializer):
            name = CharField(max_length=5)
            age = IntegerField(min_value=0, max_value=100)

        data = {"name": "This name is too long", "age": 150}
        serializer = TestSerializer(data=data)
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "age" in serializer.errors

    def test_serializer_required_fields(self):
        class TestSerializer(BaseSerializer):
            required_field = CharField()
            optional_field = CharField(required=False)

        data = {"optional_field": "value"}
        serializer = TestSerializer(data=data)
        assert not serializer.is_valid()
        assert "required_field" in serializer.errors

    def test_serializer_with_defaults(self):
        class TestSerializer(BaseSerializer):
            name = CharField()
            status = CharField(default="active")
            count = IntegerField(default=0)

        data = {"name": "test"}
        serializer = TestSerializer(data=data)
        assert serializer.is_valid()
        validated = serializer.validated_data
        assert validated["name"] == "test"
        assert validated["status"] == "active"
        assert validated["count"] == 0

    def test_serializer_to_representation(self):
        class TestSerializer(BaseSerializer):
            name = CharField()
            age = IntegerField()

        class MockInstance:
            def __init__(self):
                self.name = "John"
                self.age = 30

        instance = MockInstance()
        serializer = TestSerializer(instance=instance)
        data = serializer.data
        assert data["name"] == "John"
        assert data["age"] == 30

    def test_custom_validation(self):
        class TestSerializer(BaseSerializer):
            password = CharField()
            confirm_password = CharField()

            def validate(self, data):
                if data["password"] != data["confirm_password"]:
                    raise ValidationError("Passwords don't match")
                return data

        data = {"password": "secret", "confirm_password": "different"}
        serializer = TestSerializer(data=data)
        assert not serializer.is_valid()
        assert "non_field_errors" in serializer.errors

        data = {"password": "secret", "confirm_password": "secret"}
        serializer = TestSerializer(data=data)
        assert serializer.is_valid()


class TestModelSerializer:
    """Test ModelSerializer functionality"""

    @pytest.fixture
    def MockModel(self):
        class _Column:
            def __init__(self, name, type):
                self.name = name
                self.type = type

        class _MockModel:
            def __init__(self, **kwargs):
                self.id = None
                for key, value in kwargs.items():
                    setattr(self, key, value)

            class __table__:
                columns = [_Column("id", Integer), _Column("name", String)]

        return _MockModel

    @pytest.fixture
    def TestModelSerializer(self, MockModel):
        class _TestModelSerializer(ModelSerializer):
            name = CharField()

            class Meta:
                model = MockModel
                fields = ["id", "name"]
                read_only_fields = ["id"]

        return _TestModelSerializer

    @pytest.mark.asyncio
    async def test_model_serializer_create(self, TestModelSerializer, MockModel):
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        data = {"name": "test"}
        serializer = TestModelSerializer(data=data)

        assert serializer.is_valid(raise_exception=True)
        instance = await serializer.create(serializer.validated_data, session=mock_session)

        mock_session.add.assert_called_once_with(instance)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(instance)
        assert isinstance(instance, MockModel)
        assert instance.name == "test"

    @pytest.mark.asyncio
    async def test_model_serializer_update(self, TestModelSerializer, MockModel):
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        instance = MockModel(name="original")
        data = {"name": "updated"}
        serializer = TestModelSerializer(instance=instance, data=data)

        assert serializer.is_valid(raise_exception=True)
        updated_instance = await serializer.update(instance, serializer.validated_data, session=mock_session)

        mock_session.add.assert_called_once_with(updated_instance)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(updated_instance)
        assert updated_instance.name == "updated"
