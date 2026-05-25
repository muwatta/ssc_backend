"""SSC Cooperative — Loans Serializers"""

from rest_framework import serializers
from decimal import Decimal
from .models import LoanApplication, LoanRepaymentLedger, LoanStatus
from .services import MAX_REPAYMENT_MONTHS, calculate_max_borrowable, check_loan_eligibility


class LoanApplicationSerializer(serializers.ModelSerializer):
    applicant_file_number = serializers.CharField(source="applicant.file_number", read_only=True)
    applicant_name        = serializers.CharField(source="applicant.full_name", read_only=True)

    class Meta:
        model  = LoanApplication
        fields = [
            "id", "applicant", "applicant_file_number", "applicant_name",
            "home_address", "phone_numbers", "school_branch", "designation",
            "date_joined_cooperative", "monthly_contribution", "total_amount_saved", "monthly_salary",
            "date_of_last_loan", "amount_outstanding_prev",
            "amount_applied", "purpose",
            "proposed_monthly_repayment", "proposed_duration_months",
            "repayment_start_hijri_month", "repayment_start_hijri_year",
            "repayment_end_hijri_month", "repayment_end_hijri_year",
            "status", "amount_approved", "outstanding_balance",
            "committee_decision_note",
            "application_hijri_month", "application_hijri_year", "application_hijri_display",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "applicant", "applicant_file_number", "applicant_name",
            "school_branch", "designation", "date_joined_cooperative",
            "monthly_contribution", "total_amount_saved",
            "status", "amount_approved", "outstanding_balance",
            "application_hijri_month", "application_hijri_year", "application_hijri_display",
            "created_at", "updated_at",
        ]


class SubmitLoanSerializer(serializers.Serializer):
    amount_applied             = serializers.DecimalField(max_digits=12, decimal_places=2)
    purpose                    = serializers.CharField()
    monthly_salary             = serializers.DecimalField(max_digits=12, decimal_places=2)
    home_address               = serializers.CharField()
    phone_numbers              = serializers.CharField(max_length=100)
    proposed_monthly_repayment = serializers.DecimalField(max_digits=12, decimal_places=2)
    proposed_duration_months   = serializers.IntegerField(min_value=1, max_value=MAX_REPAYMENT_MONTHS)
    date_of_last_loan          = serializers.DateField(required=False, allow_null=True)
    amount_outstanding_prev    = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    repayment_start_hijri_month = serializers.IntegerField(min_value=1, max_value=12)
    repayment_start_hijri_year  = serializers.IntegerField(min_value=1400)

    def validate_amount_applied(self, value):
        if value <= Decimal("0.00"):
            raise serializers.ValidationError("Loan amount must be greater than zero.")
        return value

    def validate_proposed_monthly_repayment(self, value):
        if value <= Decimal("0.00"):
            raise serializers.ValidationError("Monthly repayment must be greater than zero.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        if request:
            try:
                profile = request.user.member_profile
            except Exception:
                raise serializers.ValidationError("No member profile found.")

            eligibility = check_loan_eligibility(profile)
            if not eligibility["eligible"]:
                raise serializers.ValidationError({"eligibility": eligibility["reasons"]})

            max_amount = calculate_max_borrowable(profile)
            if attrs["amount_applied"] > max_amount:
                raise serializers.ValidationError({
                    "amount_applied": f"Maximum borrowable is ₦{max_amount} (75% of available balance)."
                })

        return attrs


class CommitteeDecisionSerializer(serializers.Serializer):
    decision       = serializers.ChoiceField(choices=["approve", "reject"])
    amount_approved = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    note           = serializers.CharField(allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["decision"] == "approve" and not attrs.get("amount_approved"):
            raise serializers.ValidationError({"amount_approved": "Required when approving."})
        return attrs


class PostRepaymentSerializer(serializers.Serializer):
    amount      = serializers.DecimalField(max_digits=12, decimal_places=2)
    hijri_month = serializers.IntegerField(min_value=1, max_value=12)
    hijri_year  = serializers.IntegerField(min_value=1400)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value


class LoanRepaymentLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LoanRepaymentLedger
        fields = [
            "id", "loan", "hijri_month", "hijri_year", "hijri_display",
            "amount", "balance_before", "balance_after",
            "verified_by_name", "verified_by_role", "created_at",
        ]
        read_only_fields = fields


class LoanEligibilitySerializer(serializers.Serializer):
    eligible          = serializers.BooleanField()
    reasons           = serializers.ListField(child=serializers.CharField())
    max_borrowable    = serializers.DecimalField(max_digits=14, decimal_places=2)
    consecutive_months = serializers.IntegerField()
