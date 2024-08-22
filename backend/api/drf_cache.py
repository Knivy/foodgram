"""Redis."""

from django.core.cache import cache  # type: ignore
from django.conf import settings  # type: ignore


class CacheResponseMixin:
    """
    Миксин для кэширования DRF API с помощью Redis.
    """

    cache_timeout = settings.CACHE_TIMEOUT

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
