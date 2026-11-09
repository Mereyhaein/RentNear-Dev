from django.db.models import Q
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from marketplace.booking_serializers import BookingSerializer
from marketplace.booking_services import transition_booking
from marketplace.models import Booking
from marketplace.views import ItemPagination


class BookingViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BookingSerializer
    pagination_class = ItemPagination

    def get_queryset(self):
        return Booking.objects.filter(Q(renter=self.request.user) | Q(item__owner=self.request.user)).select_related('item__owner', 'renter', 'payment').order_by('-created_at', '-id')

    def transition(self, request, operation):
        booking = self.get_object()
        booking = transition_booking(booking_id=booking.pk, user=request.user, operation=operation)
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        return self.transition(request, 'cancel')

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        return self.transition(request, 'complete')

    @action(detail=True, methods=['post'], url_path='open-dispute')
    def open_dispute(self, request, pk=None):
        return self.transition(request, 'open_dispute')
