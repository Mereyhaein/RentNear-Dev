from django.db import migrations


def backfill(apps, schema_editor):
    Booking = apps.get_model('marketplace', 'Booking')
    Payment = apps.get_model('marketplace', 'MockPayment')
    alias = schema_editor.connection.alias
    for booking in Booking.objects.using(alias).all().iterator():
        state = 'cancelled' if booking.status == 'cancelled' else 'released' if booking.status == 'completed' else 'held'
        Payment.objects.using(alias).get_or_create(booking_id=booking.pk, defaults={'amount': booking.total_price, 'state': state})


class Migration(migrations.Migration):
    dependencies = [('marketplace', '0003_booking_dispute_open_alter_booking_item_and_more')]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
