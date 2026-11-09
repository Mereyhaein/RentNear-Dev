"""Booking writes serialize on the item row, including competing create requests."""
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from marketplace.models import Booking, Item, MockPayment

ACTIVE_STATUSES = (Booking.Status.PENDING, Booking.Status.CONFIRMED)


@transaction.atomic
def create_booking(*, renter, item_id, start_date, end_date):
    item = get_object_or_404(Item.objects.select_for_update(), pk=item_id)
    today = timezone.localdate()
    if start_date < today or end_date < start_date:
        raise ValidationError({'end_date': 'Choose dates from today onward, with end on or after start.'})
    if item.owner_id == renter.pk:
        raise ValidationError({'item': 'You cannot book your own item.'})
    if not item.availability:
        raise ValidationError({'item': 'This item is currently unavailable.'})
    # Dates are inclusive: a booking ending on a date blocks that whole date.
    if Booking.objects.filter(item=item, status__in=ACTIVE_STATUSES, start_date__lte=end_date, end_date__gte=start_date).exists():
        raise ValidationError({'start_date': 'This item is already booked for some of these dates.'})
    total = item.price_per_day * ((end_date - start_date).days + 1)
    if total > Decimal('99999999.99'):
        raise ValidationError({'end_date': 'The rental total is too large. Choose a shorter rental.'})
    booking = Booking.objects.create(item=item, renter=renter, start_date=start_date, end_date=end_date, total_price=total, status=Booking.Status.CONFIRMED)
    MockPayment.objects.create(booking=booking, amount=total, state=MockPayment.State.HELD)
    return booking


@transaction.atomic
def transition_booking(*, booking_id, user, operation):
    # Always lock item before booking, matching create_booking's lock order.
    reference = get_object_or_404(Booking, pk=booking_id)
    Item.objects.select_for_update().get(pk=reference.item_id)
    booking = Booking.objects.select_for_update().select_related('item').get(pk=booking_id)
    if user.pk not in (booking.renter_id, booking.item.owner_id):
        raise PermissionDenied('Only booking participants can access this booking.')
    if operation == 'complete' and user.pk != booking.item.owner_id:
        raise PermissionDenied('Only the item owner can confirm rental completion.')
    if booking.status not in ACTIVE_STATUSES:
        raise ValidationError({'detail': 'This booking is already completed or cancelled.'})
    if booking.dispute_open:
        raise ValidationError({'detail': 'An open dispute keeps the hold active. Resolve it before changing this booking.'})
    today = timezone.localdate()
    if operation == 'cancel':
        if today >= booking.start_date:
            raise ValidationError({'detail': 'Cancellation is only available before the rental start date.'})
        booking.status = Booking.Status.CANCELLED
        state = MockPayment.State.CANCELLED
    elif operation == 'complete':
        if today <= booking.end_date:
            raise ValidationError({'detail': 'Complete the rental after its end date.'})
        booking.status = Booking.Status.COMPLETED
        state = MockPayment.State.RELEASED
    elif operation == 'open_dispute':
        if today < booking.start_date:
            raise ValidationError({'detail': 'A dispute can be opened once the rental has started.'})
        booking.dispute_open = True
        state = MockPayment.State.HELD
    else:
        raise ValidationError({'detail': 'Unknown booking operation.'})
    payment = booking.payment
    payment.state = state
    payment.save(update_fields=['state', 'updated_at'])
    booking.save(update_fields=['status', 'dispute_open'])
    return booking
