"""Контроллеры."""

from rest_framework.permissions import (AllowAny,  # type: ignore
                                        IsAuthenticated)
from rest_framework import viewsets  # type: ignore

from recipes.models import Tag, Recipe
from .serializers import TagSerializer, RecipeSerializer
from .permissions import AuthorOnly, ForbiddenPermission


class TagViewSet(viewsets.ModelViewSet):
    """Вьюсет тегов."""

    http_method_names = ('get',)
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    permission_classes = (AllowAny,)


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет рецептов."""

    http_method_names = ('get', 'post', 'patch', 'delete')
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer

    def get_permissions(self):
        """Разрешения."""
        if self.action in {'list', 'retrieve'}:
            self.permission_classes = (AllowAny,)
        elif self.action == 'create':
            self.permission_classes = (IsAuthenticated,)
        elif self.action in {'partial_update', 'destroy'}:
            self.permission_classes = (AuthorOnly,)
        else:
            self.permission_classes = (ForbiddenPermission,)
        return super().get_permissions()
