from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/categories/', include('categories.urls')),
    path('api/entities/', include('entities.urls')),
    path('api/products/', include('products.urls')),
    path('api/articles/', include('articles.urls')),
    path('api/suggestions/', include('suggestions.urls')),
    path('api/reports/', include('reports.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)