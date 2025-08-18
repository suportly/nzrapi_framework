from nzrapi.routing import Router

from .views import ItemListCreateView, ItemRetrieveUpdateDestroyView

router = Router()

router.add_api_view("/items", ItemListCreateView)
router.add_api_view("/items/{item_id:int}", ItemRetrieveUpdateDestroyView)
