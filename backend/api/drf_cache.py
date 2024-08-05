from django.core.cache import cache
from rest_framework.response import Response
from django.conf import settings  # type: ignore


class CacheResponseMixin:
    """
    A mixin to cache DRF API responses using Redis.
    """

    cache_timeout = settings.CACHE_TIMEOUT

    def finalize_response(self, request, response, *args, **kwargs):
        """
        Override the finalize_response method to cache the response.
        """
        if not self.cache_timeout:
            return super().finalize_response(request, response, *args, **kwargs)

        key = f'drf:{self.cache_timeout}:{request.method}:{request.path_info}'
        cache.set(key, response.data, self.cache_timeout)

        return response

    def get_cached_response(self, request):
        """
        Get the cached response for the given request.
        """
        key = f'drf:{self.cache_timeout}:{request.method}:{request.path_info}'
        cached_response = cache.get(key)

        if cached_response is not None:
            return Response(cached_response)

        return None
