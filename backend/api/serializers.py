"""
LiveStock IQ — DRF Serializers (SQL Models)
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Farm, Cattle, SensorDevice, Alert, VetRecord, AlertThreshold


# ===================== USER =====================
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class RegisterSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model  = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password2']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


# ===================== ALERT THRESHOLD =====================
class AlertThresholdSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AlertThreshold
        fields = '__all__'
        read_only_fields = ['farm', 'updated_at']


# ===================== FARM =====================
class FarmSerializer(serializers.ModelSerializer):
    owner     = UserSerializer(read_only=True)
    threshold = AlertThresholdSerializer(read_only=True)

    class Meta:
        model  = Farm
        fields = ['id', 'owner', 'name', 'location', 'state', 'country',
                  'phone', 'threshold', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


# ===================== SENSOR DEVICE =====================
class SensorDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SensorDevice
        fields = ['id', 'device_uid', 'firmware_ver', 'battery_pct',
                  'last_ping', 'status', 'signal_strength']
        read_only_fields = ['id', 'last_ping']


# ===================== CATTLE (LIST) =====================
class CattleListSerializer(serializers.ModelSerializer):
    device = SensorDeviceSerializer(read_only=True)

    class Meta:
        model  = Cattle
        fields = ['id', 'cattle_id', 'name', 'breed', 'sex', 'age_years',
                  'weight_kg', 'lactating', 'temperature', 'activity',
                  'feeding', 'status', 'device', 'updated_at']
        read_only_fields = ['id', 'updated_at']


# ===================== CATTLE (DETAIL) =====================
class CattleDetailSerializer(serializers.ModelSerializer):
    device      = SensorDeviceSerializer(read_only=True)
    alerts      = serializers.SerializerMethodField()
    vet_records = serializers.SerializerMethodField()

    class Meta:
        model  = Cattle
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_alerts(self, obj):
        qs = obj.alerts.filter(is_resolved=False).order_by('-created_at')[:5]
        return AlertSerializer(qs, many=True).data

    def get_vet_records(self, obj):
        qs = obj.vet_records.order_by('-created_at')[:5]
        return VetRecordSerializer(qs, many=True).data


# ===================== ALERT =====================
class AlertSerializer(serializers.ModelSerializer):
    cattle_name = serializers.CharField(source='cattle.name', read_only=True)
    cattle_cid  = serializers.CharField(source='cattle.cattle_id', read_only=True)

    class Meta:
        model  = Alert
        fields = ['id', 'cattle', 'cattle_name', 'cattle_cid', 'alert_type',
                  'title', 'description', 'icon', 'is_resolved',
                  'resolved_at', 'created_at']
        read_only_fields = ['id', 'created_at']


# ===================== VET RECORD =====================
class VetRecordSerializer(serializers.ModelSerializer):
    cattle_name = serializers.CharField(source='cattle.name', read_only=True)

    class Meta:
        model  = VetRecord
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


# ===================== SENSOR PUSH (from device) =====================
class SensorPushSerializer(serializers.Serializer):
    """Incoming sensor data payload from IoT device / simulation."""
    cattle_id   = serializers.CharField(max_length=20)
    temperature = serializers.FloatField(min_value=35.0, max_value=43.0)
    activity    = serializers.IntegerField(min_value=0, max_value=100)
    feeding     = serializers.IntegerField(min_value=0, max_value=100)
    battery_pct = serializers.IntegerField(min_value=0, max_value=100, required=False, default=100)
    signal      = serializers.IntegerField(min_value=0, max_value=100, required=False, default=85)


# ===================== DASHBOARD SUMMARY =====================
class DashboardSerializer(serializers.Serializer):
    """Read-only summary for the dashboard page."""
    total_cattle     = serializers.IntegerField()
    healthy          = serializers.IntegerField()
    sick             = serializers.IntegerField()
    fever            = serializers.IntegerField()
    estrus           = serializers.IntegerField()
    critical_alerts  = serializers.IntegerField()
    unresolved_alerts = serializers.IntegerField()
    avg_temperature  = serializers.FloatField()
    avg_activity     = serializers.FloatField()
    avg_feeding      = serializers.FloatField()
    health_score     = serializers.FloatField()
    farm             = FarmSerializer()


# ===================== FARMER PROFILE (COMMUNITY) =====================
class FarmerProfileSerializer(serializers.ModelSerializer):
    farm_name   = serializers.CharField(source='farm.name', read_only=True)
    farm_id     = serializers.IntegerField(source='farm.id', read_only=True)
    location    = serializers.CharField(source='farm.location', read_only=True)

    class Meta:
        model  = FarmerProfile
        fields = ['id', 'farm_id', 'farm_name', 'bio', 'expertise', 'experience_years',
                  'profile_image', 'followers_count', 'following_count', 'is_verified',
                  'location', 'created_at', 'updated_at']
        read_only_fields = ['id', 'followers_count', 'following_count', 'created_at', 'updated_at']


# ===================== CONNECTION SERIALIZER =====================
class ConnectionSerializer(serializers.ModelSerializer):
    from_farm_name  = serializers.CharField(source='from_farm.name', read_only=True)
    to_farm_name    = serializers.CharField(source='to_farm.name', read_only=True)
    from_farm_location = serializers.CharField(source='from_farm.location', read_only=True)
    to_farm_location = serializers.CharField(source='to_farm.location', read_only=True)

    class Meta:
        model  = Connection
        fields = ['id', 'from_farm', 'from_farm_name', 'from_farm_location',
                  'to_farm', 'to_farm_name', 'to_farm_location', 'status', 'message',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


# ===================== POST COMMENT SERIALIZER =====================
class PostCommentSerializer(serializers.ModelSerializer):
    farm_name       = serializers.CharField(source='farm.name', read_only=True)
    farm_id         = serializers.IntegerField(source='farm.id', read_only=True)

    class Meta:
        model  = PostComment
        fields = ['id', 'post', 'farm_id', 'farm_name', 'content', 'likes_count',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'likes_count', 'created_at', 'updated_at']


# ===================== COMMUNITY POST SERIALIZER =====================
class CommunityPostSerializer(serializers.ModelSerializer):
    farm_name       = serializers.CharField(source='farm.name', read_only=True)
    farm_id         = serializers.IntegerField(source='farm.id', read_only=True)
    farm_location   = serializers.CharField(source='farm.location', read_only=True)
    comments        = PostCommentSerializer(many=True, read_only=True)

    class Meta:
        model  = CommunityPost
        fields = ['id', 'farm_id', 'farm_name', 'farm_location', 'category', 'title',
                  'content', 'image_url', 'likes_count', 'comments_count', 'views_count',
                  'comments', 'created_at', 'updated_at']
        read_only_fields = ['id', 'likes_count', 'comments_count', 'views_count',
                           'created_at', 'updated_at']


# ===================== POST LIKE SERIALIZER =====================
class PostLikeSerializer(serializers.ModelSerializer):
    farm_name   = serializers.CharField(source='farm.name', read_only=True)

    class Meta:
        model  = PostLike
        fields = ['id', 'post', 'farm_name', 'created_at']
        read_only_fields = ['id', 'created_at']
