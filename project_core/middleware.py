import logging
import traceback


class LogExceptionsMiddleware:
    """
    Middleware to log full tracebacks to stdout in production so we can diagnose 500s.
    Remove once the underlying issue is fixed.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception:
            logging.error("Unhandled exception", exc_info=True)
            raise
