from rest_framework.routers import DefaultRouter
from marketplace.views import ItemViewSet
from marketplace.booking_views import BookingViewSet

router = DefaultRouter()
router.register('items', ItemViewSet, basename='item')
router.register('bookings', BookingViewSet, basename='booking')
urlpatterns = router.urls
