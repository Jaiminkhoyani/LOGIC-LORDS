"""
LiveStock IQ — Root URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# ---- Swagger / ReDoc API Docs ----
schema_view = get_schema_view(
    openapi.Info(
        title="LiveStock IQ API",
        default_version='v1',
        description=(
            "🐄 **LiveStock IQ** — Smart Cattle Health Monitor API\n\n"
            "Dual Database Architecture:\n"
            "- **SQLite** → Relational data (farms, cattle, alerts, users)\n"
            "- **MongoDB** → Time-series sensor readings\n\n"
            "Built for Hackathon 2026 🏆"
        ),
        contact=openapi.Contact(email="admin@livestockiq.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Admin Panel
    path('admin/', admin.site.urls),

    # API Routes
    path('api/v1/', include('api.urls')),

    # API Documentation
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='redoc'),
    path('api/schema.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),

    # Serve frontend (catch-all)
    path('', TemplateView.as_view(template_name='index.html'), name='frontend'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
