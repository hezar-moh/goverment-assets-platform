# Purpose: Web views for reviewing pending access requests — list, approve, reject, and clear old records.

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from .decorators import login_required_custom, role_required
from .models import PendingAccess


@login_required_custom
@role_required('SUPER_ADMIN', 'MINISTRY_ADMIN')
def pending_access_list_view(request):
    """Show pending (and approved/rejected) access requests. Answers: who tried to log in but was blocked?"""
    status_filter = request.GET.get('status', 'PENDING')

    qs = PendingAccess.objects.all()
    if status_filter:
        qs = qs.filter(status=status_filter)

    requests_list = list(qs[:200])

    # Count by status for the summary cards
    total_pending  = PendingAccess.objects.filter(status='PENDING').count()
    total_approved = PendingAccess.objects.filter(status='APPROVED').count()
    total_rejected = PendingAccess.objects.filter(status='REJECTED').count()

    return render(request, 'authentication/pending_access_list.html', {
        'requests':       requests_list,
        'status_filter':  status_filter,
        'total_pending':  total_pending,
        'total_approved': total_approved,
        'total_rejected': total_rejected,
        'page_title':     'Pending Access Requests',
    })


@login_required_custom
@role_required('SUPER_ADMIN', 'MINISTRY_ADMIN')
def pending_access_review_view(request, request_id):
    """Approve or reject a pending request. Approving does NOT auto-create the user — that is a separate intentional step."""
    pending = get_object_or_404(PendingAccess, id=request_id)
    reviewer = request.user

    if request.method == 'POST':
        action       = request.POST.get('action', '')
        review_notes = request.POST.get('review_notes', '').strip()

        if action not in ['APPROVE', 'REJECT']:
            messages.error(request, "Invalid action.")
            return redirect('pending_access_list')

        pending.status          = 'APPROVED' if action == 'APPROVE' else 'REJECTED'
        pending.reviewed_by_id  = reviewer.id
        pending.reviewed_by_name = reviewer.get_full_name() or reviewer.username
        pending.reviewed_at     = timezone.now()
        pending.review_notes    = review_notes
        pending.save()

        action_word = "approved" if action == 'APPROVE' else "rejected"
        messages.success(
            request,
            f"Access request from '{pending.username}' has been {action_word}."
        )

        if action == 'APPROVE':
            messages.info(
                request,
                f"Remember to create a user account for '{pending.username}' "
                f"in User Management."
            )

        return redirect('pending_access_list')

    return render(request, 'authentication/pending_access_review.html', {
        'pending':    pending,
        'page_title': f'Review: {pending.username}',
    })


@login_required_custom
@role_required('SUPER_ADMIN')
def pending_access_clear_view(request):
    """Delete rejected requests older than 30 days (POST only)."""
    if request.method != 'POST':
        return redirect('pending_access_list')

    from datetime import timedelta
    cutoff = timezone.now() - timedelta(days=30)

    deleted_count, _ = PendingAccess.objects.filter(
        status='REJECTED',
        attempted_at__lt=cutoff
    ).delete()

    messages.success(
        request,
        f"Cleared {deleted_count} rejected requests older than 30 days."
    )
    return redirect('pending_access_list')