
from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from authentication import views
from rest_framework import permissions

# Setup Swagger schema view
schema_view = get_schema_view(
    openapi.Info(
        title='API Documentation COFFEE BYTE',
        default_version='v2',
        description="API for managing COFFEE BYTE in the system",
    ),
    public=True,  # Set public to True for public access
    permission_classes=(permissions.AllowAny,),  # Allow public access
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("",include("authentication.urls")),
    path("menu/",include("inventory.urls")),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

]
