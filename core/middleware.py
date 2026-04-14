import logging
from time import perf_counter

from django.conf import settings
from django.db import connection


logger = logging.getLogger(__name__)


class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = perf_counter()
        initial_query_count = len(getattr(connection, "queries", []))
        response = self.get_response(request)
        elapsed_ms = (perf_counter() - start) * 1000

        if elapsed_ms >= settings.SLOW_REQUEST_THRESHOLD_MS:
            executed_queries = getattr(connection, "queries", [])[initial_query_count:]
            db_time_ms = sum(
                float(query.get("time", 0) or 0) for query in executed_queries
            ) * 1000
            logger.warning(
                "Slow request %s %s status=%s total_ms=%.1f db_ms=%.1f queries=%s",
                request.method,
                request.path,
                getattr(response, "status_code", "unknown"),
                elapsed_ms,
                db_time_ms,
                len(executed_queries),
            )

        return response
