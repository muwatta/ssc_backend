from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.accounts.models import MemberProfile


class SavingsEntryType(models.TextChoices):
    ORDINARY_SAVINGS = 'ordinary_savings', 'Ordinary Savings'
    TERMLY_DUES = 'termly_dues', 'Termly Dues'
    PROFIT_SHARE = 'profit_share', 'Profit Share'
    ADJUSTMENT = 'adjustment', 'Adjustment'
    LEGACY_IMPORT = 'legacy_import', 'Legacy Import'


class SavingsLedger(models.Model):
    member = models.ForeignKey(
        MemberProfile,
        on_delete=models.CASCADE,
        related_name='ledger_entries',
    )
    entry_type = models.CharField(
        max_length=20,
        choices=SavingsEntryType.choices,
        default=SavingsEntryType.ORDINARY_SAVINGS,
    )
    details = models.TextField(blank=True, default='')
    hijri_month = models.PositiveSmallIntegerField()
    hijri_year = models.PositiveIntegerField()
    hijri_display = models.CharField(max_length=32)
    gregorian_date = models.DateField(default=timezone.now)
    debit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    credit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    verified_by_name = models.CharField(max_length=100, blank=True, default='')
    verified_by_role = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ssc_savings_ledger'
        ordering = ['-gregorian_date', '-id']

    def __str__(self):
        return f"{self.member.file_number} — {self.entry_type} — {self.hijri_display}"
