from django.contrib import admin

from marketplace.models import Booking, Item, MockPayment


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "category", "price_per_day", "location", "availability")
    list_filter = ("category", "availability")
    search_fields = ("title", "location", "owner__email")


class ReadOnlyRentalAdmin(admin.ModelAdmin):
    # Lifecycle writes must use the atomic booking services, never raw admin edits.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Booking)
class BookingAdmin(ReadOnlyRentalAdmin):
    list_display = ("item", "renter", "start_date", "end_date", "total_price", "status")
    list_filter = ("status",)


@admin.register(MockPayment)
class MockPaymentAdmin(ReadOnlyRentalAdmin):
    list_display = ('booking', 'amount', 'state', 'updated_at')
    list_filter = ('state',)
