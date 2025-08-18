from nzrapi.permissions import IsAuthenticated
from nzrapi.views import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from .models import Item
from .serializers import ItemSerializer


class ItemListCreateView(ListCreateAPIView):
    """
    View to list all items or create a new one.
    """

    model_class = Item
    serializer_class = ItemSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["name", "description"]
    ordering_fields = ["id", "name"]
    search_fields = ["name", "description"]


class ItemRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    """
    View to retrieve, update, or delete an item by its ID.
    """

    model_class = Item
    serializer_class = ItemSerializer
    lookup_field = "id"
    lookup_url_kwarg = "item_id"
