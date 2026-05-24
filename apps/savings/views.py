from decimal import Decimal

from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import filters, generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import MemberProfile, Role
from apps.accounts.permissions import CanPostSavings
from .models import SavingsLedger, SavingsEntryType
from .serializers import SavingsLedgerSerializer


class SavingsPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'


def _authorize_member_access(request, member: MemberProfile):
    if request.user.role in (Role.ADMIN, Role.COMMITTEE, Role.HEAD_OF_SCHOOL):
        return
    if member.user != request.user:
        raise PermissionDenied('You do not have permission to view this member savings data.')


class MemberSavingsBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, member_id):
        member = get_object_or_404(MemberProfile, id=member_id)
        _authorize_member_access(request, member)

        last_entry = SavingsLedger.objects.filter(member=member).order_by('-created_at').first()
        balance = last_entry.balance if last_entry else Decimal('0.00')

        return Response(
            {
                'member_id': member.id,
                'file_number': member.file_number,
                'full_name': member.full_name,
                'total_savings': f'{balance:.2f}',
                'suretyship_committed': '0.00',
                'available_balance': f'{balance:.2f}',
            }
        )


class MemberSavingsLedgerListView(generics.ListAPIView):
    serializer_class = SavingsLedgerSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = SavingsPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['details', 'entry_type']

    def get_queryset(self):
        member = get_object_or_404(MemberProfile, id=self.kwargs['member_id'])
        _authorize_member_access(self.request, member)

        queryset = SavingsLedger.objects.filter(member=member).order_by('-created_at')

        hijri_month = self.request.query_params.get('hijri_month')
        hijri_year = self.request.query_params.get('hijri_year')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if hijri_month is not None:
            try:
                queryset = queryset.filter(hijri_month=int(hijri_month))
            except ValueError:
                raise ValidationError('hijri_month must be an integer.')

        if hijri_year is not None:
            try:
                queryset = queryset.filter(hijri_year=int(hijri_year))
            except ValueError:
                raise ValidationError('hijri_year must be an integer.')

        if date_from:
            parsed_from = parse_date(date_from)
            if not parsed_from:
                raise ValidationError('date_from must be a valid YYYY-MM-DD date.')
            queryset = queryset.filter(gregorian_date__gte=parsed_from)

        if date_to:
            parsed_to = parse_date(date_to)
            if not parsed_to:
                raise ValidationError('date_to must be a valid YYYY-MM-DD date.')
            queryset = queryset.filter(gregorian_date__lte=parsed_to)

        return queryset

    def get(self, request, *args, **kwargs):
        if request.query_params.get('format') == 'csv':
            queryset = self.filter_queryset(self.get_queryset())
            return self._render_csv(queryset)
        return super().get(request, *args, **kwargs)

    def _render_csv(self, queryset):
        import csv

        field_names = [
            'created_at',
            'gregorian_date',
            'hijri_month',
            'hijri_year',
            'hijri_display',
            'entry_type',
            'details',
            'credit',
            'debit',
            'balance',
            'verified_by_name',
            'verified_by_role',
        ]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="savings_ledger_{self.kwargs["member_id"]}.csv"'

        writer = csv.writer(response)
        writer.writerow(field_names)

        for entry in queryset:
            writer.writerow([
                entry.created_at.isoformat(),
                entry.gregorian_date.isoformat(),
                entry.hijri_month,
                entry.hijri_year,
                entry.hijri_display,
                entry.entry_type,
                f'{entry.details}',
                f'{entry.credit:.2f}' if entry.credit is not None else '',
                f'{entry.debit:.2f}' if entry.debit is not None else '',
                f'{entry.balance:.2f}',
                entry.verified_by_name,
                entry.verified_by_role,
            ])

        return response


class PostSavingsView(APIView):
    permission_classes = [CanPostSavings]

    def post(self, request):
        member_id = request.data.get('member')
        amount = request.data.get('amount')
        hijri_month = request.data.get('hijri_month')
        hijri_year = request.data.get('hijri_year')
        hijri_display = request.data.get('hijri_display')
        details = request.data.get('details', 'Monthly savings deposit')

        if not member_id or not amount:
            raise ValidationError('Member ID and amount are required.')

        member = get_object_or_404(MemberProfile, id=member_id)

        try:
            amount_decimal = Decimal(str(amount))
        except Exception:
            raise ValidationError('Amount must be a valid number.')

        if amount_decimal <= 0:
            raise ValidationError('Amount must be greater than zero.')

        previous_entry = SavingsLedger.objects.filter(member=member).order_by('-created_at').first()
        previous_balance = previous_entry.balance if previous_entry else Decimal('0.00')
        new_balance = previous_balance + amount_decimal

        entry = SavingsLedger.objects.create(
            member=member,
            entry_type=SavingsEntryType.ORDINARY_SAVINGS,
            details=details,
            hijri_month=hijri_month or timezone.now().month,
            hijri_year=hijri_year or timezone.now().year,
            hijri_display=hijri_display or '',
            credit=amount_decimal,
            debit=None,
            balance=new_balance,
            verified_by_name=request.user.staff_id or str(request.user),
            verified_by_role=request.user.role,
        )

        serializer = SavingsLedgerSerializer(entry)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PostDuesView(APIView):
    permission_classes = [CanPostSavings]

    def post(self, request):
        amount = request.data.get('amount')
        hijri_month = request.data.get('hijri_month')
        hijri_year = request.data.get('hijri_year')
        hijri_display = request.data.get('hijri_display')
        member_ids = request.data.get('member_ids')
        details = request.data.get('description', 'Termly dues charge')

        if not amount:
            raise ValidationError('Amount is required.')

        try:
            amount_decimal = Decimal(str(amount))
        except Exception:
            raise ValidationError('Amount must be a valid number.')

        if amount_decimal <= 0:
            raise ValidationError('Amount must be greater than zero.')

        queryset = MemberProfile.objects.filter(membership_status='active')
        if member_ids:
            queryset = queryset.filter(id__in=member_ids)

        with transaction.atomic():
            entries = []
            for member in queryset:
                previous_entry = SavingsLedger.objects.filter(member=member).order_by('-created_at').first()
                previous_balance = previous_entry.balance if previous_entry else Decimal('0.00')
                new_balance = previous_balance - amount_decimal
                entry = SavingsLedger.objects.create(
                    member=member,
                    entry_type=SavingsEntryType.TERMLY_DUES,
                    details=details,
                    hijri_month=hijri_month or timezone.now().month,
                    hijri_year=hijri_year or timezone.now().year,
                    hijri_display=hijri_display or '',
                    debit=amount_decimal,
                    credit=None,
                    balance=new_balance,
                    verified_by_name=request.user.staff_id or str(request.user),
                    verified_by_role=request.user.role,
                )
                entries.append(entry)

        return Response(
            {
                'posted': len(entries),
                'description': details,
                'amount': f'{amount_decimal:.2f}',
            },
            status=status.HTTP_201_CREATED,
        )
