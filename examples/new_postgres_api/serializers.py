from nzrapi.serializers import ModelSerializer

from .models import Item


class ItemSerializer(ModelSerializer):
    class Meta:
        model = Item
        fields = "__all__"
        read_only_fields = ["id"]
