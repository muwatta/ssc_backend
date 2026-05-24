from django.urls import path

from .views import (
    MemberSavingsBalanceView,
    MemberSavingsLedgerListView,
    PostSavingsView,
    PostDuesView,
)

urlpatterns = [
    path('balance/<int:member_id>/', MemberSavingsBalanceView.as_view(), name='savings-balance'),
    path('ledger/<int:member_id>/', MemberSavingsLedgerListView.as_view(), name='savings-ledger'),
    path('post/', PostSavingsView.as_view(), name='savings-post'),
    path('dues/', PostDuesView.as_view(), name='savings-dues'),
]
