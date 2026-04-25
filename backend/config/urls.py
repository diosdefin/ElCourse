from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView # Добавили импорт
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('platform_app.urls')),
    
    # Наши новые пути для авторизации
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'), # Это ВХОД
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), # Продление токена
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)