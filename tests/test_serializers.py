"""
Tests for nzrRest serializer system
"""

from datetime import datetime

import pytest

from nzrrest.exceptions import ValidationError
from nzrrest.serializers import (
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
        """Test CharField validation"""
        field = CharField(max_length=10)

        # Valid input
        assert field.to_internal_value("hello") == "hello"

        # Too long
        with pytest.raises(ValidationError):
            field.to_internal_value("this is too long")

    def test_integer_field(self):
        """Test IntegerField validation"""
        field = IntegerField(min_value=0, max_value=100)

        # Valid input
        assert field.to_internal_value("42") == 42
        assert field.to_internal_value(42) == 42

        # Invalid range
        with pytest.raises(ValidationError):
            field.to_internal_value(-1)

        with pytest.raises(ValidationError):
            field.to_internal_value(101)

        # Invalid type
        with pytest.raises(ValidationError):
            field.to_internal_value("not a number")

    def test_boolean_field(self):
        """Test BooleanField validation"""
        field = BooleanField()

        # Various true values
        assert field.to_internal_value(True) is True
        assert field.to_internal_value("true") is True
        assert field.to_internal_value("1") is True
        assert field.to_internal_value(1) is True

        # Various false values
        assert field.to_internal_value(False) is False
        assert field.to_internal_value("false") is False
        assert field.to_internal_value("0") is False
        assert field.to_internal_value(0) is False

    def test_datetime_field(self):
        """Test DateTimeField validation"""
        field = DateTimeField()

        # Valid datetime object
        dt = datetime.now()
        assert field.to_internal_value(dt) == dt

        # Valid ISO string
        iso_string = "2024-01-01T12:00:00"
        result = field.to_internal_value(iso_string)
        assert isinstance(result, datetime)

        # Invalid string
        with pytest.raises(ValidationError):
            field.to_internal_value("not a date")

    def test_list_field(self):
        """Test ListField validation"""
        field = ListField(child=IntegerField())

        # Valid list
        assert field.to_internal_value([1, 2, 3]) == [1, 2, 3]

        # Valid list with string numbers
        assert field.to_internal_value(["1", "2", "3"]) == [1, 2, 3]

        # Invalid list item
        with pytest.raises(ValidationError):
            field.to_internal_value([1, "not a number", 3])

        # Not a list
        with pytest.raises(ValidationError):
            field.to_internal_value("not a list")

    def test_dict_field(self):
        """Test DictField validation"""
        field = DictField()

        # Valid dict
        data = {"key": "value"}
        assert field.to_internal_value(data) == data

        # Not a dict
        with pytest.raises(ValidationError):
            field.to_internal_value("not a dict")


class TestBaseSerializer:
    """Test BaseSerializer functionality"""

    def test_simple_serializer(self):
        """Test basic serializer functionality"""

        class TestSerializer(BaseSerializer):
            name = CharField(max_length=50)
            age = IntegerField(min_value=0)
            active = BooleanField()

        # Valid data
        data = {"name": "John", "age": 30, "active": True}
        serializer = TestSerializer(data=data)

        assert serializer.is_valid()
        assert serializer.validated_data == data

    def test_serializer_validation_errors(self):
        """Test serializer validation error handling"""

        class TestSerializer(BaseSerializer):
            name = CharField(max_length=5)
            age = IntegerField(min_value=0, max_value=100)

        # Invalid data
        data = {"name": "This name is too long", "age": 150}
        serializer = TestSerializer(data=data)

        assert not serializer.is_valid()
        assert "name" in serializer.errors or "non_field_errors" in serializer.errors

    def test_serializer_required_fields(self):
        """Test required field validation"""

        class TestSerializer(BaseSerializer):
            required_field = CharField()
            optional_field = CharField(required=False)

        # Missing required field
        data = {"optional_field": "value"}
        serializer = TestSerializer(data=data)

        assert not serializer.is_valid()

    def test_serializer_with_defaults(self):
        """Test fields with default values"""

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
        """Test serialization to representation"""

        class TestSerializer(BaseSerializer):
            name = CharField()
            age = IntegerField()

        # Mock instance
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
        """Test custom validation methods"""

        class TestSerializer(BaseSerializer):
            password = CharField()
            confirm_password = CharField()

            def validate(self, data):
                if data["password"] != data["confirm_password"]:
                    raise ValidationError("Passwords don't match")
                return data

        # Mismatched passwords
        data = {"password": "secret", "confirm_password": "different"}
        serializer = TestSerializer(data=data)

        assert not serializer.is_valid()

        # Matching passwords
        data = {"password": "secret", "confirm_password": "secret"}
        serializer = TestSerializer(data=data)

        assert serializer.is_valid()


class TestModelSerializer:
    """Test ModelSerializer functionality"""

    def test_model_serializer_creation(self):
        """Test ModelSerializer basic functionality"""

        # Mock SQLAlchemy model
        class MockModel:
            class __table__:
                columns = []

        class TestModelSerializer(ModelSerializer):
            name = CharField()

            class Meta:
                model = MockModel

        serializer = TestModelSerializer()
        assert hasattr(serializer, "fields")
        assert "name" in serializer.fields

    def test_model_serializer_create(self):
        """Test model instance creation"""

        class MockModel:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        class TestModelSerializer(ModelSerializer):
            name = CharField()

            class Meta:
                model = MockModel

        data = {"name": "test"}
        serializer = TestModelSerializer(data=data)

        assert serializer.is_valid()
        instance = serializer.create(serializer.validated_data)
        assert isinstance(instance, MockModel)
        assert instance.name == "test"

    def test_model_serializer_update(self):
        """Test model instance update"""

        class MockModel:
            def __init__(self, **kwargs):
                self.name = "original"
                for key, value in kwargs.items():
                    setattr(self, key, value)

        class TestModelSerializer(ModelSerializer):
            name = CharField()

            class Meta:
                model = MockModel

        instance = MockModel()
        data = {"name": "updated"}
        serializer = TestModelSerializer(data=data)

        assert serializer.is_valid()
        updated_instance = serializer.update(instance, serializer.validated_data)
        assert updated_instance.name == "updated"
