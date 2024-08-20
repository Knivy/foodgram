from django.core.cache import cache  # type: ignore
from django.conf import settings  # type: ignore


class CacheResponseMixin:
    """
    Миксин для кэширования DRF API с помощью Redis.
    """

    cache_timeout = settings.CACHE_TIMEOUT

    # def finalize_response(self, request, response, *args, **kwargs):
    #     """
    #     Переопределеление finalize_response для кэширования ответа.
    #     """
    #     if not self.cache_timeout:
    #         return super().finalize_response(request, response,
    #                                          *args, **kwargs)

    #     key = f'drf:{self.cache_timeout}:{request.method}:{request.path_info}'
    #     cache.set(key, response.data, self.cache_timeout)

    #     return super().finalize_response(request, response,
    #                                      *args, **kwargs)

    # def get_cached_response(self, request):
    #     """
    #     Получение кэшированного ответа.
    #     """
    #     key = f'drf:{self.cache_timeout}:{request.method}:{request.path_info}'
    #     cached_response = cache.get(key)

    #     if cached_response is not None:
    #         return Response(cached_response)

    #     return None

    def get_queryset(self):
        """Переопределение get_queryset."""
        if self.cache_timeout:
            key = (f'drf:{self.cache_timeout}:{self.request.method}:'
                   f'{self.request.path_info}')
            cached_queryset = cache.get(key)
            if cached_queryset is not None:
                return cached_queryset
            queryset = super().get_queryset()
            cache.set(key, queryset, self.cache_timeout)
            return queryset
        return super().get_queryset()
