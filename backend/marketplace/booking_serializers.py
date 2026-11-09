from rest_framework import serializers

from marketplace.booking_services import create_booking
from marketplace.models import Booking, MockPayment


class MockPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MockPayment
        fields = ('id', 'amount', 'state', 'updated_at')
        read_only_fields = fields


class BookingSerializer(serializers.ModelSerializer):
    item = serializers.IntegerField(source='item_id', min_value=1, max_value=9223372036854775807)
    item_title = serializers.CharField(source='item.title', read_only=True)
    owner = serializers.IntegerField(source='item.owner_id', read_only=True)
    owner_name = serializers.CharField(source='item.owner.name', read_only=True)
    renter_name = serializers.CharField(source='renter.name', read_only=True)
    payment = MockPaymentSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = ('id', 'item', 'item_title', 'owner', 'owner_name', 'renter', 'renter_name', 'start_date', 'end_date', 'total_price', 'status', 'dispute_open', 'created_at', 'payment')
        read_only_fields = ('id', 'renter', 'total_price', 'status', 'dispute_open', 'created_at')

    def create(self, validated_data):
        return create_booking(renter=self.context['request'].user, item_id=validated_data.pop('item_id'), **validated_data)

