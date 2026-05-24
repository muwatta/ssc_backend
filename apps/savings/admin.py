from django.contrib import admin

from .models import SavingsLedger


@admin.register(SavingsLedger)
class SavingsLedgerAdmin(admin.ModelAdmin):
    list_display = [
        'member',
        'entry_type',
        'hijri_display',
        'gregorian_date',
        'credit',
        'debit',
        'balance',
        'verified_by_name',
        'verified_by_role',
    ]
    search_fields = ['member__file_number', 'member__full_name', 'details']
    list_filter = ['entry_type', 'hijri_year', 'hijri_month']
    readonly_fields = ['created_at']
