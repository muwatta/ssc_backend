from rest_framework import serializers

from .models import SavingsLedger


class SavingsLedgerSerializer(serializers.ModelSerializer):
    member_id = serializers.IntegerField(source='member.id', read_only=True)
    member_file_number = serializers.CharField(
        source='member.file_number', read_only=True
    )
    member_name = serializers.CharField(source='member.full_name', read_only=True)

    class Meta:
        model = SavingsLedger
        fields = [
            'id',
            'member_id',
            'member_file_number',
            'member_name',
            'entry_type',
            'details',
            'hijri_month',
            'hijri_year',
            'hijri_display',
            'gregorian_date',
            'debit',
            'credit',
            'balance',
            'verified_by_name',
            'verified_by_role',
            'created_at',
        ]
