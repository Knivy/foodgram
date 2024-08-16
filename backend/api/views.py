"""Контроллеры."""

import io

# from reportlab.lib.pagesizes import letter  # type: ignore
# from reportlab.pdfgen import canvas  # type: ignore
from rest_framework.permissions import (AllowAny,  # type: ignore
                                        IsAuthenticated)
from rest_framework import filters, viewsets  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from rest_framework.decorators import action  # type: ignore
from rest_framework.response import Response  # type: ignore
from django.shortcuts import get_object_or_404  # type: ignore
from django.conf import settings  # type: ignore
from rest_framework.views import APIView  # type: ignore
from django.shortcuts import redirect  # type: ignore
from django.http import FileResponse  # type: ignore
from django_filters.rest_framework import DjangoFilterBackend  # type: ignore

from recipes.models import Tag, Recipe, Ingredient
from .serializers import (TagSerializer, RecipeWriteSerializer,
                          RecipeReadSerializer, IngredientSerializer,
                          UserReadSerializer, UserWriteSerializer,
                          PasswordSerializer, FavoriteSerializer,
                          SubscriptionSerializer, ShoppingSerializer,
                          AvatarSerializer)
from .permissions import AuthorOnly, ForbiddenPermission
from .filters import RecipeFilter


User = get_user_model()


class BaseReadOnlyViewset(viewsets.ReadOnlyModelViewSet):
    """Базовый вьюсет для чтения."""

    permission_classes = (AllowAny,)
    pagination_class = None


class TagViewSet(BaseReadOnlyViewset):
    """Вьюсет тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(BaseReadOnlyViewset):
    """Вьюсет ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    search_fields = ('^name',)


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет рецептов."""

    http_method_names = ('get', 'post', 'patch', 'delete')
    queryset = Recipe.objects.all()
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_class = RecipeFilter

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

    def get_serializer_class(self):
        """Выбор сериализатора."""
        if self.action in {'list', 'retrieve'}:
            return RecipeReadSerializer
        if self.action == 'favorite':
            return FavoriteSerializer
        if self.action == 'shopping_cart':
            return ShoppingSerializer
        return RecipeWriteSerializer

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request):
        """Добавление в избранное."""
        serializer = self.get_serializer()
        serializer.save()
        return Response(serializer.data)

    @favorite.mapping.delete
    def delete_favorite(self, request):
        """Удалить из избранного."""
        user = request.user
        favorite_recipes = user.favorites.filter(recipe=self.get_object())
        if favorite_recipes.exists():
            for recipe in favorite_recipes:
                recipe.delete()
            return Response(status=204)
        return Response(status=404)

    def convert_to_txt(self, recipes):
        """Конвертация в TXT."""
        if not recipes:
            return 'Нет рецептов в списке покупок.'
        ingredients = {}
        for recipe in recipes:
            for ingredient in recipe.ingredients.all():
                name = ingredient.name
                amount = ingredient.amount
                unit = ingredient.measurement_unit
                if name not in ingredients:
                    ingredients[name] = {}
                    ingredients[name][unit] = amount
                else:
                    if unit not in ingredients[name]:
                        ingredients[name][unit] = amount
                    elif unit == 'г' and 'кг' in ingredients[name]:
                        ingredients[name]['кг'] += amount / 1000
                    elif unit == 'кг' and 'г' in ingredients[name]:
                        ingredients[name]['г'] += amount * 1000
                    elif unit == 'л' and 'мл' in ingredients[name]:
                        ingredients[name]['мл'] += amount * 1000
                    elif unit == 'мл' and 'л' in ingredients[name]:
                        ingredients[name]['л'] += amount / 1000
                    else:
                        ingredients[name][unit] += amount
        if not ingredients:
            return 'Нет ингредиентов для покупки.'
        ingredients = dict(sorted(ingredients.items()))
        txt = ['Список покупок.\n\n']
        for name, units in ingredients.items():
            if len(units) == 1:
                unit, amount = next(iter(units.items()))
                txt.append(f'{name} ({unit}) — {amount}\n')
            else:
                txt.append(f'{name}:\n')
                for unit, amount in units.items():
                    txt.append(f'  {unit} — {amount}\n')
        return ''.join(txt)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        """Получение списка покупок в формате PDF."""
        user = request.user
        recipes = user.shopping_cart.all()
        txt = self.convert_to_txt(recipes)
        return FileResponse(txt, as_attachment=True,
                            filename='Список покупок.txt')
        # pdf_data = io.BytesIO()
        # pdf_in_memory = canvas.Canvas(pdf_data, pagesize=letter)
        # pdf_in_memory.drawString(100, 100, txt)
        # pdf_in_memory.save()
        # return FileResponse(pdf_data, as_attachment=True,
        #                     filename='Список покупок.pdf',
        #                     content_type='application/pdf')

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request):
        """Добавление рецепта в список покупок."""
        user = request.user
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request):
        """Удаление из списка покупок."""
        user = request.user
        shopping_cart = user.shopping_cart.filter(recipe=self.get_object())
        if shopping_cart.exists():
            for shopping_recipe in shopping_cart:
                shopping_recipe.delete()
            return Response(status=204)
        return Response(status=404)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(AllowAny,)
    )
    def get_link(self, request):
        """Получение короткой ссылки."""
        recipe_id = request.data.get('id')
        recipe = get_object_or_404(Recipe, id=recipe_id)
        return Response({
            'short-link':
            f'{settings.CURRENT_HOST}/s/{recipe.short_url}',
        })


class UserViewSet(viewsets.ModelViewSet):
    """Вьюсет пользователей."""

    http_method_names = ('get', 'post')
    queryset = User.objects.all()
    permission_classes = (AllowAny,)

    @action(
        detail=False,
        methods=('put',),
        permission_classes=(IsAuthenticated,),
        url_path='me/avatar',
        url_name='user_avatar',
    )
    def put_user_avatar(self, request):
        """Изменение аватара."""
        user = request.user
        serializer = self.get_serializer(user)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @put_user_avatar.mapping.delete
    def delete_user_avatar(self, request):
        """Удаление аватара."""
        user = request.user
        user.avatar.delete()
        return Response(status=204)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,)
    )
    def me(self, request):
        """Страница пользователя."""
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def set_password(self, request):
        """Установка пароля."""
        user = request.user
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def get_serializer_class(self):
        """Выбор сериализатора."""
        if self.action in {'me', 'list', 'retrieve'}:
            return UserReadSerializer
        if self.action == 'set_password':
            return PasswordSerializer
        if self.action == 'subscribe':
            return SubscriptionSerializer
        if self.action == 'put_user_avatar':
            return AvatarSerializer
        return UserWriteSerializer

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request):
        """Подписка."""
        user = request.user
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @subscribe.mapping.delete
    def delete_subscribe(self, request):
        """Удалить из подписок."""
        user = request.user
        subscriptions = user.subscriptions.filter(id=request.data['id'])
        if subscriptions.exists():
            for subscription in subscriptions:
                subscription.delete()
            return Response(status=204)
        return Response(status=404)


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет подписок."""

    sserializer_class = SubscriptionSerializer

    def get_permissions(self):
        """Разрешения."""
        if self.action == 'list':
            self.permission_classes = (AllowAny,)
        else:
            self.permission_classes = (ForbiddenPermission,)
        return super().get_permissions()

    def get_queryset(self):
        """Подписки."""
        user = self.request.user
        return user.subscriptions.all()


class ShortLinkViewset(viewsets.ViewSet):
    """Вьюсет коротких ссылок."""

    permission_classes = (AllowAny,)

    def retrieve(self, request, pk=None):
        """Получение рецепта по короткой ссылке."""
        recipe_id = int(pk, 23)
        recipe = get_object_or_404(Recipe, id=recipe_id)
        serializer = RecipeReadSerializer(recipe)
        return Response(serializer.data)


class ShortLinkView(APIView):
    """Класс коротких ссылок."""

    def get(self, request, pk):
        """Получение рецепта по короткой ссылке."""
        recipe_id = int(pk, 23)
        return redirect(f'{settings.CURRENT_HOST}/api/recipes/{recipe_id}/')
