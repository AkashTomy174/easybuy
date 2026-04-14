import logging
from time import perf_counter

from django.conf import settings
from django.db import connection


logger = logging.getLogger(__name__)


class PublicHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        public_host = (getattr(settings, "PUBLIC_HOST", "") or "").strip()
        if public_host:
            current_host = (request.META.get("HTTP_HOST") or "").strip()
            current_hostname = current_host.split(":", 1)[0].lower()
            if current_hostname in {"", "127.0.0.1", "0.0.0.0", "localhost", "::1"}:
                request.META["HTTP_HOST"] = public_host
                request.META["SERVER_NAME"] = public_host.split(":", 1)[0]
                if ":" in public_host:
                    request.META["SERVER_PORT"] = public_host.rsplit(":", 1)[1]

        return self.get_response(request)


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
