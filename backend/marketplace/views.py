from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from marketplace.models import Item, Booking
from marketplace.serializers import ItemSerializer


class OwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.method in permissions.SAFE_METHODS or obj.owner_id == request.user.pk


class ItemPagination(PageNumberPagination):
    page_size = 24


class ItemViewSet(viewsets.ModelViewSet):
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, OwnerOrReadOnly]
    pagination_class = ItemPagination

    def get_queryset(self):
        items = Item.objects.select_related('owner').prefetch_related('images').order_by('-created_at', '-id')
        if self.action == 'mine':
            return items.filter(owner=self.request.user)
        if self.action != 'list':
            return items
        items = items.filter(availability=True)
        params = self.request.query_params
        for word in params.get('search', '').split():
            items = items.filter(Q(title__icontains=word) | Q(description__icontains=word))
        if params.get('category'):
            items = items.filter(category__iexact=params['category'].strip())
        if params.get('location'):
            items = items.filter(location__icontains=params['location'].strip())
        prices = {}
        for key in ('min_price', 'max_price'):
            if params.get(key):
                try:
                    value = Decimal(params[key])
                    if not value.is_finite() or value < 0 or value > Decimal('99999999.99'):
                        raise InvalidOperation
                    prices[key] = value
                except (InvalidOperation, ValueError):
                    raise serializers.ValidationError({key: 'Enter a valid non-negative price.'})
        if 'min_price' in prices and 'max_price' in prices and prices['min_price'] > prices['max_price']:
            raise serializers.ValidationError({'max_price': 'Maximum price must be at least minimum price.'})
        if 'min_price' in prices:
            items = items.filter(price_per_day__gte=prices['min_price'])
        if 'max_price' in prices:
            items = items.filter(price_per_day__lte=prices['max_price'])
        return items

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, permission_classes=[permissions.IsAuthenticated])
    def mine(self, request):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    @action(detail=False, permission_classes=[permissions.AllowAny])
    def categories(self, request):
        return Response(list(Item.objects.filter(availability=True).order_by('category').values_list('category', flat=True).distinct()))


    @transaction.atomic
    def perform_update(self, serializer):
        serializer.instance = Item.objects.select_for_update().get(pk=serializer.instance.pk)
        serializer.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        instance = Item.objects.select_for_update().get(pk=instance.pk)
        try:
            instance.delete()
        except ProtectedError:
            raise serializers.ValidationError({'detail': 'This item has booking history. Mark it unavailable instead.'})

    @action(detail=True, permission_classes=[permissions.AllowAny])
    def availability(self, request, pk=None):
        item = self.get_object()
        periods = item.bookings.filter(status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED], end_date__gte=timezone.localdate()).order_by('start_date').values('start_date', 'end_date')
        return Response({'availability': item.availability, 'booked_periods': list(periods)})
