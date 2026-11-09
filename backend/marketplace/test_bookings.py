from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from marketplace.models import Booking, Item, MockPayment


def fixtures():
    User = get_user_model()
    owner = User.objects.create(email='book-owner@example.com', name='Owner')
    renter = User.objects.create(email='renter@example.com', name='Renter')
    stranger = User.objects.create(email='stranger@example.com', name='Stranger')
    item = Item.objects.create(owner=owner, title='Camera', description='Camera with lens', category='Electronics', price_per_day='12.50', location='Almaty')
    return owner, renter, stranger, item


class BookingApiTests(APITestCase):
    def setUp(self):
        self.owner, self.renter, self.stranger, self.item = fixtures()
        self.today = timezone.localdate()
        self.start = self.today + timedelta(days=3)
        self.end = self.start + timedelta(days=2)
        self.client.force_authenticate(self.renter)

    def payload(self, **changes):
        return {'item': self.item.pk, 'start_date': self.start.isoformat(), 'end_date': self.end.isoformat(), **changes}

    def book(self, **changes):
        return self.client.post('/api/bookings/', self.payload(**changes), format='json')

    def operation(self, booking_id, name):
        return self.client.post(f'/api/bookings/{booking_id}/{name}/', {}, format='json')

    def test_booking_creates_confirmed_booking_and_held_payment(self):
        response = self.book(total_price='0', status='completed', renter=self.owner.pk, payment={'state': 'released'})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['renter'], self.renter.pk)
        self.assertEqual(response.data['status'], 'confirmed')
        self.assertEqual(response.data['total_price'], '37.50')
        self.assertEqual(response.data['payment']['state'], 'held')
        self.assertEqual(response.data['payment']['amount'], '37.50')
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(MockPayment.objects.count(), 1)

    def test_login_required_for_creation_read_and_transitions(self):
        booking = self.book().data
        self.client.force_authenticate(None)
        self.assertEqual(self.book().status_code, 401)
        self.assertEqual(self.client.get('/api/bookings/').status_code, 401)
        self.assertEqual(self.client.get(f"/api/bookings/{booking['id']}/").status_code, 401)
        for operation in ('cancel', 'complete', 'open-dispute'):
            self.assertEqual(self.operation(booking['id'], operation).status_code, 401)

    def test_owner_and_unavailable_item_rejected(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.book().status_code, 400)
        self.client.force_authenticate(self.renter)
        self.item.availability = False
        self.item.save()
        self.assertEqual(self.book().status_code, 400)
        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(MockPayment.objects.count(), 0)

    def test_invalid_missing_past_reversed_and_excessive_dates(self):
        for payload in ({}, self.payload(start_date='not-a-date'), self.payload(start_date=(self.today-timedelta(days=1)).isoformat()), self.payload(end_date=(self.start-timedelta(days=1)).isoformat()), self.payload(item=99999)):
            response = self.client.post('/api/bookings/', payload, format='json')
            self.assertIn(response.status_code, (400, 404), response.data)
        self.item.price_per_day = Decimal('99999999.99')
        self.item.save()
        self.assertEqual(self.book().status_code, 400)
        self.assertEqual(Booking.objects.count(), 0)

    def test_same_day_rental_is_one_day(self):
        response = self.book(start_date=self.today.isoformat(), end_date=self.today.isoformat())
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['total_price'], '12.50')

    def test_overlap_boundaries_and_nonoverlap(self):
        self.assertEqual(self.book().status_code, 201)
        for start, end in ((self.start, self.end), (self.start-timedelta(days=1), self.start), (self.end, self.end+timedelta(days=1)), (self.start+timedelta(days=1), self.end), (self.start-timedelta(days=1), self.end+timedelta(days=1))):
            self.assertEqual(self.book(start_date=start.isoformat(), end_date=end.isoformat()).status_code, 400)
        self.assertEqual(self.book(start_date=(self.end+timedelta(days=1)).isoformat(), end_date=(self.end+timedelta(days=1)).isoformat()).status_code, 201)

    def test_pending_bookings_block_and_cancelled_do_not(self):
        existing = Booking.objects.create(item=self.item, renter=self.stranger, start_date=self.start, end_date=self.end, total_price='37.50', status='pending')
        MockPayment.objects.create(booking=existing, amount=existing.total_price)
        self.assertEqual(self.book().status_code, 400)
        self.client.force_authenticate(self.stranger)
        self.assertEqual(self.operation(existing.pk, 'cancel').status_code, 200)
        self.client.force_authenticate(self.renter)
        self.assertEqual(self.book().status_code, 201)

    def test_participant_visibility_and_immutable_fields(self):
        booking_id = self.book().data['id']
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get('/api/bookings/').data['count'], 1)
        self.client.force_authenticate(self.stranger)
        self.assertEqual(self.client.get('/api/bookings/').data['count'], 0)
        self.assertEqual(self.client.get(f'/api/bookings/{booking_id}/').status_code, 404)
        for operation in ('cancel', 'complete', 'open-dispute'):
            self.assertEqual(self.operation(booking_id, operation).status_code, 404)
        self.client.force_authenticate(self.renter)
        self.assertEqual(self.client.patch(f'/api/bookings/{booking_id}/', {'status': 'completed'}, format='json').status_code, 405)
        self.assertEqual(self.client.delete(f'/api/bookings/{booking_id}/').status_code, 405)

    def test_cancellation_cancels_hold_and_rebooking_is_allowed(self):
        booking_id = self.book().data['id']
        response = self.operation(booking_id, 'cancel')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], 'cancelled')
        self.assertEqual(response.data['payment']['state'], 'cancelled')
        self.assertEqual(self.operation(booking_id, 'cancel').status_code, 400)
        self.assertEqual(self.operation(booking_id, 'complete').status_code, 403)
        self.assertEqual(self.book().status_code, 201)

    def test_owner_can_cancel_before_start(self):
        booking_id = self.book().data['id']
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.operation(booking_id, 'cancel').data['payment']['state'], 'cancelled')

    def test_completion_requires_owner_and_past_end_date(self):
        booking_id = self.book().data['id']
        self.assertEqual(self.operation(booking_id, 'complete').status_code, 403)
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.operation(booking_id, 'complete').status_code, 400)
        with patch('marketplace.booking_services.timezone.localdate', return_value=self.end):
            self.assertEqual(self.operation(booking_id, 'complete').status_code, 400)
        with patch('marketplace.booking_services.timezone.localdate', return_value=self.end+timedelta(days=1)):
            response = self.operation(booking_id, 'complete')
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['status'], 'completed')
            self.assertEqual(response.data['payment']['state'], 'released')
            self.assertEqual(self.operation(booking_id, 'complete').status_code, 400)

    def test_cannot_cancel_started_rental(self):
        booking_id = self.book().data['id']
        with patch('marketplace.booking_services.timezone.localdate', return_value=self.start):
            self.assertEqual(self.operation(booking_id, 'cancel').status_code, 400)
        self.assertEqual(MockPayment.objects.get(booking_id=booking_id).state, 'held')

    def test_dispute_keeps_hold_active_and_blocks_release_or_cancel(self):
        booking_id = self.book().data['id']
        self.assertEqual(self.operation(booking_id, 'open-dispute').status_code, 400)
        with patch('marketplace.booking_services.timezone.localdate', return_value=self.start):
            response = self.operation(booking_id, 'open-dispute')
            self.assertEqual(response.status_code, 200, response.data)
            self.assertTrue(response.data['dispute_open'])
        self.client.force_authenticate(self.owner)
        with patch('marketplace.booking_services.timezone.localdate', return_value=self.end+timedelta(days=1)):
            self.assertEqual(self.operation(booking_id, 'complete').status_code, 400)
            self.assertEqual(self.operation(booking_id, 'cancel').status_code, 400)
        self.assertEqual(MockPayment.objects.get(booking_id=booking_id).state, 'held')

    def test_atomic_rollback_if_payment_creation_fails(self):
        with patch('marketplace.booking_services.MockPayment.objects.create', side_effect=RuntimeError('simulated failure')):
            with self.assertRaises(RuntimeError):
                self.book()
        self.assertEqual(Booking.objects.count(), 0)

    def test_public_availability_no_identity_and_booking_history_protected(self):
        self.book()
        self.client.force_authenticate(None)
        response = self.client.get(f'/api/items/{self.item.pk}/availability/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['booked_periods']), 1)
        self.assertEqual(set(response.data['booked_periods'][0]), {'start_date', 'end_date'})
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.delete(f'/api/items/{self.item.pk}/').status_code, 400)
        self.assertTrue(Item.objects.filter(pk=self.item.pk).exists())
        self.assertEqual(MockPayment.objects.count(), 1)

    def test_backfill_preserves_legacy_bookings_and_creates_payment_once(self):
        import importlib
        from types import SimpleNamespace
        from django.apps import apps
        from django.db import connection
        migration = importlib.import_module('marketplace.migrations.0004_backfill_mock_payments')
        for status in ('pending', 'confirmed', 'cancelled', 'completed'):
            Booking.objects.create(item=self.item, renter=self.renter, start_date=self.start, end_date=self.end, total_price='37.50', status=status)
        migration.backfill(apps, SimpleNamespace(connection=connection))
        migration.backfill(apps, SimpleNamespace(connection=connection))
        self.assertEqual(Booking.objects.count(), 4)
        self.assertEqual(MockPayment.objects.count(), 4)
        for booking in Booking.objects.all():
            self.assertEqual(booking.payment.state, {'cancelled': 'cancelled', 'completed': 'released'}.get(booking.status, 'held'))


class ConcurrentBookingTests(TransactionTestCase):
    def setUp(self):
        self.owner, self.renter, self.stranger, self.item = fixtures()

    def run_concurrent_requests(self, offset=0):
        barrier = Barrier(2)
        def request(user_id, days):
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=user_id)
                client = APIClient()
                client.force_authenticate(user)
                start = timezone.localdate() + timedelta(days=3+days)
                barrier.wait(timeout=10)
                response = client.post('/api/bookings/', {'item': self.item.pk, 'start_date': start.isoformat(), 'end_date': (start+timedelta(days=1)).isoformat()}, format='json')
                return response.status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(request, self.renter.pk, 0)
            b = pool.submit(request, self.stranger.pk, offset)
            return sorted([a.result(timeout=20), b.result(timeout=20)])

    def test_concurrent_overlapping_requests_only_one_succeeds(self):
        self.assertEqual(self.run_concurrent_requests(), [201, 400])
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(MockPayment.objects.count(), 1)

    def test_concurrent_nonoverlapping_requests_both_succeed(self):
        self.assertEqual(self.run_concurrent_requests(offset=2), [201, 201])
        self.assertEqual(Booking.objects.count(), 2)
        self.assertEqual(MockPayment.objects.count(), 2)
