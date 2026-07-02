# Purpose: Shared pagination helper used by all list views across the project.

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def paginate_queryset(queryset, request, per_page=20):
    """Split a queryset into pages. Reads ?page=N from the URL. Returns (page, paginator)."""
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page', 1)

    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, show first page
        page = paginator.page(1)
    except EmptyPage:
        # If page is out of range, show last page
        page = paginator.page(paginator.num_pages)

    return page, paginator