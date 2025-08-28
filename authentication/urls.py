from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from . import views

# Main URL patterns with auto store detection
urlpatterns = [
    # =============== API DOCUMENTATION ===============
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # =============== AUTHENTICATION ===============
    path('auth/login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/register-store/', views.register_store, name='register_store'),
    path('auth/activate-license/', views.activate_license, name='activate_license'),
    
    # =============== USER PROFILE ===============
    path('profile/', views.MyProfileView.as_view(), name='my_profile'),
    path('profile/change-pin/', views.change_pin, name='change_pin'),
    path('profile/store-role/', views.my_store_role, name='my_store_role'),
    
    # =============== STORE MANAGEMENT (Auto-detected) ===============
    path('stores/', views.StoreListView.as_view(), name='store_list'),
    path('store/', views.MyStoreDetailView.as_view(), name='my_store_detail'),
    path('store/dashboard/', views.DashboardView.as_view(), name='store_dashboard'),
    path('store/status/', views.check_store_status, name='store_status'),
    
    # =============== BRANCH MANAGEMENT (Auto-detected store) ===============
    path('branches/', views.BranchListCreateView.as_view(), name='branch_list_create'),
    path('branches/<uuid:branch_id>/', views.BranchDetailView.as_view(), name='branch_detail'),
    
    # =============== USER MANAGEMENT (Auto-detected store) ===============
    path('users/', views.StoreUserListCreateView.as_view(), name='store_user_list_create'),
    path('users/<uuid:user_id>/', views.StoreUserDetailView.as_view(), name='store_user_detail'),
    path('users/<uuid:user_id>/permissions/', views.update_user_permissions, name='update_user_permissions'),
    
    # =============== BRANCH USER MANAGEMENT ===============
    path('branches/<uuid:branch_id>/users/', views.BranchUserListCreateView.as_view(), name='branch_user_list_create'),
    path('branches/<uuid:branch_id>/users/<uuid:user_id>/', views.BranchUserDetailView.as_view(), name='branch_user_detail'),
    
    # =============== POS DEVICE MANAGEMENT ===============
    path('devices/', views.POSDeviceListCreateView.as_view(), name='pos_device_list_create'),
    path('devices/<uuid:device_id>/', views.POSDeviceDetailView.as_view(), name='pos_device_detail'),
    
    # =============== PERMISSIONS ===============
    path('permissions/', views.PermissionListView.as_view(), name='permission_list'),
    path('permissions/role/<str:role>/', views.get_role_permissions, name='role_permissions'),
    
    # =============== SYSTEM ===============
    path('health/', views.health_check, name='health_check'),
]

# Optional: Keep the old explicit store_code URLs for backward compatibility
legacy_urlpatterns = [
    # Legacy URLs with explicit store_code (for backward compatibility)
    path('legacy/stores/<str:store_code>/', views.MyStoreDetailView.as_view(), name='legacy_store_detail'),
    path('legacy/stores/<str:store_code>/branches/', views.BranchListCreateView.as_view(), name='legacy_branch_list'),
    path('legacy/stores/<str:store_code>/users/', views.StoreUserListCreateView.as_view(), name='legacy_store_users'),
]

# Uncomment the next line if you want to include legacy URLs
# urlpatterns += legacy_urlpatterns