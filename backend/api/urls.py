"""
LiveStock IQ — API URL Routes
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    RegisterView, FarmView, DashboardView, AnalyticsView,
    CattleViewSet, SensorPushView, BulkSimulateView,
    AlertListView, AlertResolveView,
    VetRecordViewSet, ThresholdView,
    MongoStatsView, MongoSnapshotsView,
    FarmerProfileView, CommunityProfilesView, ConnectionViewSet,
    CommunityPostViewSet, PostCommentViewSet,
)

# ── ViewSet Router ──
router = DefaultRouter()
router.register(r'cattle',         CattleViewSet,      basename='cattle')
router.register(r'vet-records',    VetRecordViewSet,   basename='vet-records')
router.register(r'connections',    ConnectionViewSet,  basename='connections')
router.register(r'posts',          CommunityPostViewSet, basename='posts')
router.register(r'comments',       PostCommentViewSet, basename='comments')

urlpatterns = [

    # ── Authentication ──
    path('auth/register/',      RegisterView.as_view(),      name='auth-register'),
    path('auth/token/',         TokenObtainPairView.as_view(), name='token-obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(),  name='token-refresh'),

    # ── Farm ──
    path('farm/',               FarmView.as_view(),           name='farm'),
    path('farm/dashboard/',     DashboardView.as_view(),      name='dashboard'),
    path('farm/analytics/',     AnalyticsView.as_view(),      name='analytics'),

    # ── Cattle + Vet Records (router) ──
    path('', include(router.urls)),

    # ── Sensors ──
    path('sensors/push/',       SensorPushView.as_view(),    name='sensor-push'),
    path('sensors/simulate/',   BulkSimulateView.as_view(),  name='sensor-simulate'),

    # ── Alerts ──
    path('alerts/',                     AlertListView.as_view(),            name='alerts-list'),
    path('alerts/<int:pk>/resolve/',    AlertResolveView.as_view(),         name='alert-resolve'),

    # ── Thresholds ──
    path('thresholds/', ThresholdView.as_view(), name='thresholds'),

    # ── MongoDB ──
    path('mongo/stats/',     MongoStatsView.as_view(),     name='mongo-stats'),
    path('mongo/snapshots/', MongoSnapshotsView.as_view(), name='mongo-snapshots'),

    # ── Community ──
    path('community/profiles/',                FarmerProfileView.as_view(),    name='farmer-profile'),
    path('community/profiles/<int:farm_id>/',  FarmerProfileView.as_view(),    name='farmer-profile-detail'),
    path('community/all-farmers/',             CommunityProfilesView.as_view(), name='all-farmers'),
]
