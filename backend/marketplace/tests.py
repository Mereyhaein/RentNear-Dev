import shutil
import tempfile
from io import BytesIO

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from marketplace.models import Item, ItemImage


class ListingTests(APITestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media)
        User = get_user_model()
        self.owner = User.objects.create(email='owner@example.com', name='Owner', password='Strong-password-18')
        self.other = User.objects.create(email='other@example.com', name='Other', password='Strong-password-18')
        self.payload = dict(title='Camping tent', description='Lightweight outdoor shelter', category='Outdoor', price_per_day='20.00', location='Almaty', availability=True)
        self.item = Item.objects.create(owner=self.owner, **self.payload)

    def photo(self, name='tent.png'):
        buffer = BytesIO()
        Image.new('RGB', (20, 20), 'green').save(buffer, 'PNG')
        return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')

    def test_public_list_detail_and_anonymous_create_denied(self):
        self.assertEqual(self.client.get('/api/items/').data['count'], 1)
        self.assertEqual(self.client.get(f'/api/items/{self.item.pk}/').status_code, 200)
        self.assertEqual(self.client.post('/api/items/', self.payload).status_code, 401)

    def test_owner_crud_and_owner_cannot_be_spoofed(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post('/api/items/', {**self.payload, 'owner': self.other.pk}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['owner'], self.owner.pk)
        url = f"/api/items/{response.data['id']}/"
        self.assertEqual(self.client.patch(url, {'title': 'Updated'}, format='json').status_code, 200)
        self.assertEqual(Item.objects.get(pk=response.data['id']).title, 'Updated')
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(Item.objects.filter(pk=response.data['id']).exists())

    def test_other_user_cannot_modify_or_delete(self):
        self.client.force_authenticate(self.other)
        url = f'/api/items/{self.item.pk}/'
        self.assertEqual(self.client.patch(url, {'title': 'Stolen'}).status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, self.payload['title'])

    def test_required_fields_and_invalid_prices(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.post('/api/items/', {}, format='json').status_code, 400)
        for price in ('-1', 'NaN', 'Infinity', '1234567890', '1.001'):
            response = self.client.post('/api/items/', {**self.payload, 'price_per_day': price}, format='json')
            self.assertEqual(response.status_code, 400, response.data)
        for field in ('title', 'description', 'category', 'location'):
            self.assertEqual(self.client.post('/api/items/', {**self.payload, field: '  '}, format='json').status_code, 400)

    def test_multiple_photos_and_edit_removal(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post('/api/items/', {**self.payload, 'photos': [self.photo(), self.photo()]}, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data['images']), 2)
        self.assertTrue(response.data['images'][0]['image'].startswith('http://testserver/media/'))
        image_id = response.data['images'][0]['id']
        response = self.client.patch(f"/api/items/{response.data['id']}/", {'remove_image_ids': [image_id], 'photos': [self.photo()]}, format='multipart')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data['images']), 2)
        self.assertFalse(ItemImage.objects.filter(pk=image_id).exists())

    def test_invalid_and_oversized_photos_are_atomic(self):
        self.client.force_authenticate(self.owner)
        bad_files = [SimpleUploadedFile('bad.png', b'not an image', content_type='image/png'), self.photo('bad.svg'), SimpleUploadedFile('big.png', b'x' * (5 * 1024 * 1024 + 1), content_type='image/png')]
        for photo in bad_files:
            response = self.client.post('/api/items/', {**self.payload, 'photos': [photo]}, format='multipart')
            self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Item.objects.count(), 1)
        response = self.client.post('/api/items/', {**self.payload, 'photos': [self.photo() for _ in range(9)]}, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_cannot_remove_another_listings_photo(self):
        self.client.force_authenticate(self.owner)
        other_item = Item.objects.create(owner=self.other, **self.payload)
        photo = ItemImage.objects.create(item=other_item, image=self.photo())
        response = self.client.patch(f'/api/items/{self.item.pk}/', {'remove_image_ids': [photo.pk]}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(ItemImage.objects.filter(pk=photo.pk).exists())

    def test_availability_and_mine(self):
        self.item.availability = False
        self.item.save()
        Item.objects.create(owner=self.other, **self.payload)
        self.assertEqual(self.client.get('/api/items/').data['count'], 1)
        self.assertEqual(self.client.get('/api/items/mine/').status_code, 401)
        self.client.force_authenticate(self.owner)
        response = self.client.get('/api/items/mine/')
        self.assertEqual(response.data['count'], 1)
        self.assertFalse(response.data['results'][0]['availability'])

    def test_search_and_filter_combinations(self):
        Item.objects.create(owner=self.other, **{**self.payload, 'title': 'Camera', 'description': 'Portrait lens', 'category': 'Electronics', 'price_per_day': '45', 'location': 'Astana'})
        cases = [({'search': 'TENT shelter'}, 1), ({'search': 'portrait'}, 1), ({'category': 'outdoor'}, 1), ({'location': 'alm'}, 1), ({'min_price': '21'}, 1), ({'max_price': '20'}, 1), ({'min_price': '20', 'max_price': '20', 'category': 'Outdoor', 'location': 'Almaty', 'search': 'shelter'}, 1), ({'category': 'Electronics', 'location': 'Almaty'}, 0), ({'search': 'missing'}, 0)]
        for params, count in cases:
            response = self.client.get('/api/items/', params)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['count'], count, params)
        for params in ({'min_price': '-1'}, {'max_price': 'NaN'}, {'min_price': '30', 'max_price': '20'}, {'min_price': 'abc'}):
            self.assertEqual(self.client.get('/api/items/', params).status_code, 400)
