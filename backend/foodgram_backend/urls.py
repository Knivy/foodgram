"""Адреса проекта."""

from django.contrib import admin  # type: ignore
from django.urls import include, path  # type: ignore
from django.conf import settings  # type: ignore
from django.conf.urls.static import static  # type: ignore

urlpatterns: list[path] = [
    path('api/', include('api.urls')),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
