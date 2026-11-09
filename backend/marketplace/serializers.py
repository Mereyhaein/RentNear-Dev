from decimal import Decimal
from pathlib import Path

from django.db import transaction
from rest_framework import serializers

from marketplace.models import Item, ItemImage


class PhotoField(serializers.ImageField):
    def to_internal_value(self, data):
        if data.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Each photo must be 5 MB or smaller.')
        image = super().to_internal_value(data)
        if image.image.format not in {'JPEG', 'PNG', 'WEBP'} or Path(image.name).suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
            raise serializers.ValidationError('Upload JPEG, PNG or WebP photos only.')
        return image


class ItemImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemImage
        fields = ('id', 'image')


class ItemSerializer(serializers.ModelSerializer):
    owner = serializers.IntegerField(source='owner_id', read_only=True)
    owner_name = serializers.CharField(source='owner.name', read_only=True)
    images = ItemImageSerializer(many=True, read_only=True)
    photos = serializers.ListField(child=PhotoField(), write_only=True, required=False, max_length=8)
    remove_image_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    price_per_day = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0'))

    class Meta:
        model = Item
        fields = ('id', 'owner', 'owner_name', 'title', 'description', 'category', 'price_per_day', 'location', 'availability', 'created_at', 'images', 'photos', 'remove_image_ids')
        read_only_fields = ('id', 'created_at')

    def validate(self, attrs):
        removed = set(attrs.get('remove_image_ids', []))
        existing = set(self.instance.images.values_list('id', flat=True)) if self.instance else set()
        if not removed.issubset(existing):
            raise serializers.ValidationError({'remove_image_ids': 'Select photos belonging to this listing.'})
        if len(existing - removed) + len(attrs.get('photos', [])) > 8:
            raise serializers.ValidationError({'photos': 'A listing can have up to 8 photos.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        photos = validated_data.pop('photos', [])
        validated_data.pop('remove_image_ids', None)
        item = Item.objects.create(**validated_data)
        for photo in photos:
            ItemImage.objects.create(item=item, image=photo)
        return item

    @transaction.atomic
    def update(self, instance, validated_data):
        photos = validated_data.pop('photos', [])
        removed = validated_data.pop('remove_image_ids', [])
        instance = super().update(instance, validated_data)
        instance.images.filter(id__in=removed).delete()
        for photo in photos:
            ItemImage.objects.create(item=instance, image=photo)
        return instance
