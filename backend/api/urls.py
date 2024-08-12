"""Адреса API."""

from django.urls import include, path  # type: ignore
from rest_framework import routers  # type: ignore
from .views import (TagViewSet, RecipeViewSet, IngredientViewSet, UserViewSet,
                    SubscriptionViewSet)

app_name: str = 'api'

router_v1 = routers.DefaultRouter()
router_v1.register('tags', TagViewSet, basename='tags')
router_v1.register('recipes', RecipeViewSet, basename='recipes')
router_v1.register('ingredients', IngredientViewSet, basename='ingredients')
router_v1.register('users', UserViewSet, basename='users')
router_v1.register('subscriptions', SubscriptionViewSet,
                   basename='subscriptions')

urlpatterns: list[path] = [
    path('', include(router_v1.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
