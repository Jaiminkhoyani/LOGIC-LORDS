"""
LiveStock IQ — API Views (Django REST Framework)

Endpoints:
  AUTH
    POST /auth/register/          → Register farmer
    POST /auth/token/             → Get JWT tokens
    POST /auth/token/refresh/     → Refresh JWT

  FARM
    GET  /farm/                   → Get my farm
    PUT  /farm/                   → Update farm info
    GET  /farm/dashboard/         → Dashboard summary
    GET  /farm/analytics/         → Analytics data

  CATTLE
    GET  /cattle/                 → List all cattle (filter, search)
    POST /cattle/                 → Add new cattle
    GET  /cattle/{id}/            → Cattle detail + last alerts
    PUT  /cattle/{id}/            → Update cattle
    DEL  /cattle/{id}/            → Delete cattle
    POST /cattle/{id}/treat/      → Mark as treated
    GET  /cattle/{id}/history/    → Sensor history (MongoDB)
    GET  /cattle/{id}/events/     → Event log (MongoDB)

  SENSORS
    POST /sensors/push/           → Receive real-time sensor data (IoT/simulation)

  ALERTS
    GET  /alerts/                 → List all alerts (filter by type/status)
    POST /alerts/{id}/resolve/    → Resolve an alert

  VET RECORDS
    GET  /vet-records/            → List vet records
    POST /vet-records/            → Create vet record

  THRESHOLDS
    GET  /thresholds/             → Get thresholds
    PUT  /thresholds/             → Update thresholds

  MONGODB
    GET  /mongo/stats/            → MongoDB collection stats
    GET  /mongo/snapshots/        → Recent herd snapshots
"""

import random
from datetime import datetime, timedelta

from django.utils import timezone
from django.db.models import Avg, Count, Q
from django.contrib.auth.models import User

from rest_framework import viewsets, status, generics
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Farm, Cattle, SensorDevice, Alert, VetRecord, AlertThreshold, \
    FarmerProfile, Connection, CommunityPost, PostComment, PostLike
from .serializers import (
    FarmSerializer, CattleListSerializer, CattleDetailSerializer,
    AlertSerializer, VetRecordSerializer, AlertThresholdSerializer,
    SensorPushSerializer, DashboardSerializer, RegisterSerializer,
    FarmerProfileSerializer, ConnectionSerializer, CommunityPostSerializer,
    PostCommentSerializer, PostLikeSerializer,
)
from . import mongo_models as mongo


# ──────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────
def _compute_status(temp, activity, feeding, thresholds):
    """Re-evaluate cattle status based on current sensor values & thresholds."""
    if temp >= thresholds.high_temp:
        return 'fever'
    if (activity < thresholds.min_activity or
            feeding < thresholds.min_feeding or
            temp < thresholds.low_temp):
        return 'sick'
    return 'healthy'


def _maybe_create_alert(cattle, old_status, new_status):
    """Create a DB alert when cattle status worsens."""
    if new_status == old_status or new_status == 'healthy':
        return
    alert_map = {
        'fever': {
            'alert_type': 'critical', 'icon': '🔥',
            'title': f'High Fever Detected — {cattle.name}',
            'description': (
                f'Temperature {cattle.temperature}°C exceeds critical threshold. '
                f'Immediate veterinary attention required.'
            ),
        },
        'sick': {
            'alert_type': 'warning', 'icon': '⚠️',
            'title': f'Health Alert — {cattle.name}',
            'description': (
                f'Low vitals: Activity {cattle.activity}%, '
                f'Feeding {cattle.feeding}%. Possible illness.'
            ),
        },
        'estrus': {
            'alert_type': 'info', 'icon': '💜',
            'title': f'Estrus Detected — {cattle.name}',
            'description': 'High activity spike detected. Optimal breeding window: 6-18 hours.',
        },
    }
    data = alert_map.get(new_status)
    if data:
        Alert.objects.create(cattle=cattle, **data)


def _health_score(cattle_qs, thresholds):
    """Calculate a 0-100 health score for the herd."""
    total = cattle_qs.count()
    if total == 0:
        return 100.0
    healthy = cattle_qs.filter(status='healthy').count()
    return round((healthy / total) * 100, 1)


# ──────────────────────────────────────────────
#  AUTH VIEWS
# ──────────────────────────────────────────────
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        # Auto-create farm + thresholds
        farm = Farm.objects.create(owner=user, name=f"{user.first_name or user.username}'s Farm")
        AlertThreshold.objects.create(farm=farm)
        return Response(
            {'message': f'Welcome, {user.username}! Farm created.', 'user_id': user.id},
            status=status.HTTP_201_CREATED
        )


# ──────────────────────────────────────────────
#  FARM VIEWS
# ──────────────────────────────────────────────
class FarmView(APIView):
    def _get_farm(self, request):
        try:
            return request.user.farm
        except Farm.DoesNotExist:
            return None

    def get(self, request):
        farm = self._get_farm(request)
        if not farm:
            return Response({'error': 'No farm found. Please register first.'}, status=404)
        return Response(FarmSerializer(farm).data)

    def put(self, request):
        farm = self._get_farm(request)
        if not farm:
            return Response({'error': 'Farm not found.'}, status=404)
        s = FarmSerializer(farm, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


class DashboardView(APIView):
    """GET /farm/dashboard/ — aggregated dashboard stats."""

    def get(self, request):
        # Use demo farm (farm_id=1) when no auth for hackathon demo
        if request.user.is_authenticated:
            try:
                farm = request.user.farm
            except Farm.DoesNotExist:
                farm = Farm.objects.first()
        else:
            farm = Farm.objects.first()

        if not farm:
            return Response({'error': 'No farm data. Run: python manage.py seed_data'}, status=404)

        cattle_qs = farm.cattle.all()
        status_counts = cattle_qs.values('status').annotate(count=Count('id'))
        counts = {row['status']: row['count'] for row in status_counts}

        averages = cattle_qs.aggregate(
            avg_temp=Avg('temperature'),
            avg_act=Avg('activity'),
            avg_feed=Avg('feeding'),
        )

        try:
            thresholds = farm.threshold
        except AlertThreshold.DoesNotExist:
            thresholds = AlertThreshold(farm=farm)

        data = {
            'total_cattle':      cattle_qs.count(),
            'healthy':           counts.get('healthy', 0),
            'sick':              counts.get('sick', 0),
            'fever':             counts.get('fever', 0),
            'estrus':            counts.get('estrus', 0),
            'critical_alerts':   Alert.objects.filter(cattle__farm=farm, alert_type='critical', is_resolved=False).count(),
            'unresolved_alerts': Alert.objects.filter(cattle__farm=farm, is_resolved=False).count(),
            'avg_temperature':   round(averages['avg_temp'] or 38.5, 2),
            'avg_activity':      round(averages['avg_act'] or 70, 1),
            'avg_feeding':       round(averages['avg_feed'] or 75, 1),
            'health_score':      _health_score(cattle_qs, thresholds),
            'farm':              farm,
        }
        return Response(DashboardSerializer(data).data)


class AnalyticsView(APIView):
    """GET /farm/analytics/ — chart data for analytics page."""

    def get(self, request):
        farm = Farm.objects.first()
        if not farm:
            return Response({'error': 'No farm data.'}, status=404)

        # 24-hour hourly buckets (mocked from DB averages)
        labels = [f"{h:02d}:00" for h in range(0, 24, 2)]
        cattle = farm.cattle.all()
        base_t = [round(random.uniform(38.0, 39.2), 1) for _ in labels]
        base_a = [random.randint(40, 90) for _ in labels]
        base_f = [random.randint(45, 92) for _ in labels]

        # Weekly breakdown
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        weekly = {
            'labels': days,
            'healthy': [random.randint(17, 21) for _ in days],
            'sick':    [random.randint(1,  5)  for _ in days],
            'estrus':  [random.randint(0,  3)  for _ in days],
        }

        # Alert distribution
        alert_dist = {
            'Fever':         Alert.objects.filter(cattle__farm=farm, alert_type='critical').count() or 5,
            'Low Activity':  Alert.objects.filter(cattle__farm=farm, description__icontains='activity').count() or 4,
            'Poor Feeding':  Alert.objects.filter(cattle__farm=farm, description__icontains='feeding').count() or 3,
            'Estrus':        Alert.objects.filter(cattle__farm=farm, alert_type='info').count() or 2,
        }

        return Response({
            'hourly': {
                'labels':      labels,
                'temperature': base_t,
                'activity':    base_a,
                'feeding':     base_f,
            },
            'weekly':     weekly,
            'alert_dist': alert_dist,
            'most_common_issues': [
                {'label': '🌡️ Fever',         'pct': 70},
                {'label': '😴 Low Activity',  'pct': 55},
                {'label': '🌿 Poor Feeding',  'pct': 40},
                {'label': '💜 Estrus',        'pct': 25},
            ],
        })


# ──────────────────────────────────────────────
#  CATTLE VIEWS
# ──────────────────────────────────────────────
class CattleViewSet(viewsets.ModelViewSet):
    queryset = Cattle.objects.select_related('farm', 'device').all()
    filterset_fields = ['status', 'breed', 'lactating', 'sex']
    search_fields    = ['name', 'cattle_id', 'breed']
    ordering_fields  = ['cattle_id', 'name', 'temperature', 'activity', 'status']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CattleDetailSerializer
        return CattleListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Filter by farm if authenticated
        if self.request.user.is_authenticated:
            try:
                farm = self.request.user.farm
                return qs.filter(farm=farm)
            except Farm.DoesNotExist:
                pass
        return qs

    @action(detail=True, methods=['post'], url_path='treat')
    def treat(self, request, pk=None):
        """POST /cattle/{id}/treat/ — Mark cattle as treated."""
        cattle = self.get_object()
        old_status = cattle.status
        cattle.status      = 'healthy'
        cattle.temperature = round(random.uniform(38.0, 38.9), 1)
        cattle.activity    = random.randint(60, 85)
        cattle.feeding     = random.randint(65, 90)
        cattle.notes       = 'Treatment administered. Monitoring recovery.'
        cattle.save()

        # Resolve pending alerts
        Alert.objects.filter(cattle=cattle, is_resolved=False).update(
            is_resolved=True,
            resolved_at=timezone.now(),
        )

        # Log MongoDB event
        try:
            mongo.insert_event(mongo.build_event(
                cattle.cattle_id, 'treatment_applied',
                f'Cattle marked as treated. Status changed from {old_status} to healthy.'
            ))
        except Exception:
            pass

        return Response({'message': f'{cattle.name} marked as treated.', 'status': 'healthy'})

    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        """GET /cattle/{id}/history/ — Sensor history from MongoDB."""
        cattle = self.get_object()
        hours  = int(request.query_params.get('hours', 24))
        try:
            readings = mongo.get_readings_for_cattle(cattle.cattle_id, hours)
            # If MongoDB empty, return synthetic data
            if not readings:
                readings = _synthetic_history(cattle)
        except Exception as e:
            readings = _synthetic_history(cattle)
        return Response({'cattle_id': cattle.cattle_id, 'hours': hours, 'readings': readings})

    @action(detail=True, methods=['get'], url_path='events')
    def events(self, request, pk=None):
        """GET /cattle/{id}/events/ — Event log from MongoDB."""
        cattle = self.get_object()
        try:
            events = mongo.get_events_for_cattle(cattle.cattle_id)
        except Exception:
            events = _synthetic_events(cattle)
        return Response({'cattle_id': cattle.cattle_id, 'events': events})


def _synthetic_history(cattle):
    """Generate synthetic 12-point history when MongoDB is empty."""
    base = cattle.temperature
    now  = datetime.utcnow()
    return [
        {
            'cattle_id':   cattle.cattle_id,
            'timestamp':   (now - timedelta(hours=12-i)).isoformat(),
            'temperature': round(base + random.uniform(-0.4, 0.4), 2),
            'activity':    cattle.activity + random.randint(-10, 10),
            'feeding':     cattle.feeding  + random.randint(-8,  8),
            'battery_pct': 95,
            'signal_strength': 85,
            'anomaly':     None,
        }
        for i in range(12)
    ]


def _synthetic_events(cattle):
    events = []
    if cattle.status in ('sick', 'fever'):
        events.append({'event_type': 'alert_generated', 'description': f'Status changed to {cattle.status}',
                        'timestamp': datetime.utcnow().isoformat()})
    events.append({'event_type': 'sensor_sync', 'description': 'Sensor data synced',
                    'timestamp': (datetime.utcnow() - timedelta(hours=1)).isoformat()})
    return events


# ──────────────────────────────────────────────
#  SENSOR PUSH VIEW
# ──────────────────────────────────────────────
class SensorPushView(APIView):
    """
    POST /sensors/push/
    Receive live sensor data from IoT device or simulation.
    Writes to MongoDB time-series and updates SQLite cattle snapshot.
    """

    def post(self, request):
        s = SensorPushSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        # Find cattle
        try:
            cattle = Cattle.objects.select_related('farm__threshold').get(cattle_id=d['cattle_id'])
        except Cattle.DoesNotExist:
            return Response({'error': f"Cattle {d['cattle_id']} not found."}, status=404)

        try:
            thresholds = cattle.farm.threshold
        except AlertThreshold.DoesNotExist:
            thresholds = AlertThreshold()

        # Detect anomaly
        anomaly = None
        if d['temperature'] >= thresholds.high_temp:
            anomaly = 'fever'
        elif d['activity'] < thresholds.min_activity:
            anomaly = 'low_activity'
        elif d['feeding'] < thresholds.min_feeding:
            anomaly = 'poor_feeding'

        # ── Write to MongoDB (time-series) ──
        mongo_id = None
        try:
            doc = mongo.build_sensor_reading(
                cattle_id   = d['cattle_id'],
                temperature = d['temperature'],
                activity    = d['activity'],
                feeding     = d['feeding'],
                battery_pct = d.get('battery_pct', 100),
                signal      = d.get('signal', 85),
                anomaly     = anomaly,
            )
            mongo_id = mongo.insert_sensor_reading(doc)

            if anomaly:
                mongo.insert_event(mongo.build_event(
                    d['cattle_id'], anomaly,
                    f"Anomaly detected: {anomaly} (temp={d['temperature']}, act={d['activity']}, feed={d['feeding']})",
                    value=d['temperature'] if 'fever' in anomaly else d['activity'],
                ))
        except Exception as e:
            mongo_id = f"mongo_unavailable: {str(e)}"

        # ── Update SQLite snapshot ──
        old_status = cattle.status
        cattle.temperature = d['temperature']
        cattle.activity    = d['activity']
        cattle.feeding     = d['feeding']
        new_status         = _compute_status(d['temperature'], d['activity'], d['feeding'], thresholds)

        # Preserve estrus if currently estrus (high activity spike)
        if cattle.status == 'estrus' and d['activity'] > 80:
            new_status = 'estrus'

        cattle.status = new_status
        cattle.save(update_fields=['temperature', 'activity', 'feeding', 'status', 'updated_at'])

        # Update device ping
        try:
            dev = cattle.device
            dev.battery_pct = d.get('battery_pct', dev.battery_pct)
            dev.save(update_fields=['battery_pct', 'last_ping'])
        except SensorDevice.DoesNotExist:
            pass

        # Create SQL alert if status worsened
        _maybe_create_alert(cattle, old_status, new_status)

        return Response({
            'success':    True,
            'cattle_id':  d['cattle_id'],
            'new_status': new_status,
            'anomaly':    anomaly,
            'mongo_id':   mongo_id,
        }, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────
#  BULK SIMULATE (Dev / Demo endpoint)
# ──────────────────────────────────────────────
class BulkSimulateView(APIView):
    """POST /sensors/simulate/ — Simulate one tick for all cattle."""

    def post(self, request):
        results = []
        farm = Farm.objects.first()
        if not farm:
            return Response({'error': 'No farm. Run seed_data.'}, status=404)

        try:
            thresholds = farm.threshold
        except AlertThreshold.DoesNotExist:
            thresholds = AlertThreshold()

        for cattle in farm.cattle.all():
            # Drift
            new_temp  = round(cattle.temperature + random.uniform(-0.3, 0.3), 1)
            new_act   = max(5, min(100, cattle.activity + random.randint(-8, 8)))
            new_feed  = max(5, min(100, cattle.feeding  + random.randint(-5, 5)))
            new_temp  = max(37.0, min(41.5, new_temp))

            old_status = cattle.status
            new_status = _compute_status(new_temp, new_act, new_feed, thresholds)

            # Occasional estrus spike
            if random.random() < 0.01 and cattle.sex == 'F':
                new_act   = random.randint(85, 98)
                new_status = 'estrus'

            cattle.temperature = new_temp
            cattle.activity    = new_act
            cattle.feeding     = new_feed
            cattle.status      = new_status
            cattle.save(update_fields=['temperature', 'activity', 'feeding', 'status', 'updated_at'])

            _maybe_create_alert(cattle, old_status, new_status)

            # MongoDB write
            try:
                anomaly = 'fever' if new_temp >= thresholds.high_temp else (
                    'low_activity' if new_act < thresholds.min_activity else None)
                mongo.insert_sensor_reading(mongo.build_sensor_reading(
                    cattle.cattle_id, new_temp, new_act, new_feed, anomaly=anomaly))
            except Exception:
                pass

            results.append({'id': cattle.cattle_id, 'status': new_status, 'temp': new_temp})

        return Response({'simulated': len(results), 'results': results})


# ──────────────────────────────────────────────
#  ALERTS VIEWS
# ──────────────────────────────────────────────
class AlertListView(generics.ListAPIView):
    serializer_class   = AlertSerializer
    filterset_fields   = ['alert_type', 'is_resolved']
    search_fields      = ['title', 'description']
    ordering_fields    = ['created_at', 'alert_type']

    def get_queryset(self):
        return Alert.objects.select_related('cattle').all()


class AlertResolveView(APIView):
    """POST /alerts/{id}/resolve/"""

    def post(self, request, pk):
        try:
            alert = Alert.objects.get(pk=pk)
        except Alert.DoesNotExist:
            return Response({'error': 'Alert not found.'}, status=404)
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        if request.user.is_authenticated:
            alert.resolved_by = request.user
        alert.save()
        return Response({'message': 'Alert resolved.', 'id': alert.id})


# ──────────────────────────────────────────────
#  VET RECORDS VIEWS
# ──────────────────────────────────────────────
class VetRecordViewSet(viewsets.ModelViewSet):
    queryset         = VetRecord.objects.select_related('cattle').all()
    serializer_class = VetRecordSerializer
    filterset_fields = ['record_type', 'cattle']
    search_fields    = ['diagnosis', 'treatment', 'vet_name']
    ordering_fields  = ['created_at']


# ──────────────────────────────────────────────
#  THRESHOLD VIEWS
# ──────────────────────────────────────────────
class ThresholdView(APIView):
    def get(self, request):
        farm = Farm.objects.first()
        try:
            t = farm.threshold
        except (AttributeError, AlertThreshold.DoesNotExist):
            return Response({'error': 'No threshold found.'}, status=404)
        return Response(AlertThresholdSerializer(t).data)

    def put(self, request):
        farm = Farm.objects.first()
        try:
            t = farm.threshold
        except (AttributeError, AlertThreshold.DoesNotExist):
            return Response({'error': 'No threshold found.'}, status=404)
        s = AlertThresholdSerializer(t, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


# ──────────────────────────────────────────────
#  MONGODB STATS VIEWS
# ──────────────────────────────────────────────
class MongoStatsView(APIView):
    """GET /mongo/stats/ — MongoDB collection statistics."""

    def get(self, request):
        farm = Farm.objects.first()
        try:
            stats = mongo.get_mongo_stats(farm.id if farm else 1)
        except Exception as e:
            return Response({'error': str(e), 'hint': 'Is MongoDB running?'}, status=503)
        return Response(stats)


class MongoSnapshotsView(APIView):
    """GET /mongo/snapshots/ — Last 24h herd snapshots from MongoDB."""

    def get(self, request):
        farm  = Farm.objects.first()
        hours = int(request.query_params.get('hours', 24))
        try:
            snaps = mongo.get_herd_snapshots(farm.id if farm else 1, hours)
            if not snaps:
                snaps = _synthetic_snapshots()
        except Exception as e:
            snaps = _synthetic_snapshots()
        return Response({'count': len(snaps), 'snapshots': snaps})


def _synthetic_snapshots():
    """Fake snapshots when MongoDB unavailable."""
    now = datetime.utcnow()
    return [
        {
            'farm_id':      1,
            'hour':         (now - timedelta(hours=i)).replace(minute=0, second=0, microsecond=0).isoformat(),
            'avg_temp':     round(random.uniform(38.1, 39.0), 2),
            'avg_activity': round(random.uniform(55, 85), 1),
            'avg_feeding':  round(random.uniform(60, 90), 1),
            'counts':       {'healthy': 18, 'sick': 3, 'fever': 1, 'estrus': 1, 'total': 23},
        }
        for i in range(24)
    ]


# ─────────────────────────────────────────────
#  COMMUNITY ENDPOINTS
# ─────────────────────────────────────────────


class FarmerProfileView(APIView):
    """GET /community/profile/{farm_id}/ — Get farmer profile."""

    def get(self, request, farm_id):
        try:
            profile = FarmerProfile.objects.get(farm_id=farm_id)
            serializer = FarmerProfileSerializer(profile)
            return Response(serializer.data)
        except FarmerProfile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, farm_id):
        """Update my farmer profile."""
        try:
            profile = FarmerProfile.objects.get(farm_id=farm_id)
            serializer = FarmerProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except FarmerProfile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)


class CommunityProfilesView(generics.ListAPIView):
    """GET /community/profiles/ — List all farmer profiles."""
    queryset = FarmerProfile.objects.all()
    serializer_class = FarmerProfileSerializer

    def get_queryset(self):
        qs = FarmerProfile.objects.all()
        search = self.request.query_params.get('search', '')
        expertise = self.request.query_params.get('expertise', '')
        
        if search:
            qs = qs.filter(
                Q(farm__name__icontains=search) |
                Q(bio__icontains=search) |
                Q(expertise__icontains=search)
            )
        if expertise:
            qs = qs.filter(expertise__icontains=expertise)
        
        return qs.order_by('-followers_count')


class ConnectionViewSet(viewsets.ModelViewSet):
    """CRUD for farmer connections."""
    serializer_class = ConnectionSerializer
    permission_classes = []

    def get_queryset(self):
        farm = Farm.objects.first()
        if not farm:
            return Connection.objects.none()
        return Connection.objects.filter(
            Q(from_farm=farm) | Q(to_farm=farm)
        ).order_by('-created_at')

    @action(detail=False, methods=['post'])
    def send_request(self, request):
        """Send connection request to another farmer."""
        to_farm_id = request.data.get('to_farm_id')
        message = request.data.get('message', '')
        from_farm = Farm.objects.first()

        if not from_farm or not to_farm_id:
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            to_farm = Farm.objects.get(id=to_farm_id)
            conn, created = Connection.objects.get_or_create(
                from_farm=from_farm,
                to_farm=to_farm,
                defaults={'message': message, 'status': 'pending'}
            )
            serializer = ConnectionSerializer(conn)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Farm.DoesNotExist:
            return Response({'error': 'Farm not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def accept_request(self, request):
        """Accept a connection request."""
        connection_id = request.data.get('connection_id')
        try:
            conn = Connection.objects.get(id=connection_id)
            conn.status = 'accepted'
            conn.save()
            serializer = ConnectionSerializer(conn)
            return Response(serializer.data)
        except Connection.DoesNotExist:
            return Response({'error': 'Connection not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def reject_request(self, request):
        """Reject a connection request."""
        connection_id = request.data.get('connection_id')
        try:
            conn = Connection.objects.get(id=connection_id)
            conn.delete()
            return Response({'message': 'Connection rejected'})
        except Connection.DoesNotExist:
            return Response({'error': 'Connection not found'}, status=status.HTTP_404_NOT_FOUND)


class CommunityPostViewSet(viewsets.ModelViewSet):
    """CRUD for community posts."""
    serializer_class = CommunityPostSerializer
    permission_classes = []

    def get_queryset(self):
        qs = CommunityPost.objects.all().order_by('-created_at')
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs

    def perform_create(self, serializer):
        farm = Farm.objects.first()
        if farm:
            serializer.save(farm=farm)

    @action(detail=False, methods=['post'])
    def search_posts(self, request):
        """Search posts by title/content."""
        query = request.data.get('query', '')
        if query:
            posts = CommunityPost.objects.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query)
            ).order_by('-created_at')
            serializer = CommunityPostSerializer(posts, many=True)
            return Response(serializer.data)
        return Response([])

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        """Like a post."""
        post = self.get_object()
        farm = Farm.objects.first()
        if farm:
            like, created = PostLike.objects.get_or_create(post=post, farm=farm)
            if created:
                post.likes_count += 1
                post.save()
                return Response({'message': 'Post liked', 'likes_count': post.likes_count})
            else:
                like.delete()
                post.likes_count -= 1
                post.save()
                return Response({'message': 'Post unliked', 'likes_count': post.likes_count})
        return Response({'error': 'Farm not found'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """Add comment to post."""
        post = self.get_object()
        farm = Farm.objects.first()
        content = request.data.get('content', '')

        if not farm or not content:
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        comment = PostComment.objects.create(post=post, farm=farm, content=content)
        post.comments_count += 1
        post.save()
        serializer = PostCommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PostCommentViewSet(viewsets.ModelViewSet):
    """CRUD for post comments."""
    serializer_class = PostCommentSerializer
    permission_classes = []

    def get_queryset(self):
        post_id = self.request.query_params.get('post_id')
        if post_id:
            return PostComment.objects.filter(post_id=post_id).order_by('-created_at')
        return PostComment.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        farm = Farm.objects.first()
        if farm:
            serializer.save(farm=farm)
