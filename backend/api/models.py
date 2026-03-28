"""
LiveStock IQ — SQL Models (Django ORM → SQLite)

Tables:
  Farm          → Farmer/farm details
  Cattle        → Individual cattle records
  SensorDevice  → Wearable IoT device registry
  Alert         → Health alerts & notifications
  VetRecord     → Veterinary treatments & records
  AlertThreshold → Per-farm custom alert thresholds
"""

from django.db import models
from django.contrib.auth.models import User


# ===================== FARM =====================
class Farm(models.Model):
    owner       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='farm')
    name        = models.CharField(max_length=200, default='My Farm')
    location    = models.CharField(max_length=300, blank=True)
    state       = models.CharField(max_length=100, blank=True)
    country     = models.CharField(max_length=100, default='India')
    phone       = models.CharField(max_length=20, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.owner.username})"

    class Meta:
        verbose_name_plural = 'Farms'


# ===================== CATTLE =====================
class Cattle(models.Model):
    BREED_CHOICES = [
        ('HF Cross',      'HF Cross'),
        ('Sahiwal',       'Sahiwal'),
        ('Gir',           'Gir'),
        ('Jersey Cross',  'Jersey Cross'),
        ('Murrah',        'Murrah'),
        ('Tharparkar',    'Tharparkar'),
        ('Red Sindhi',    'Red Sindhi'),
        ('Other',         'Other'),
    ]
    STATUS_CHOICES = [
        ('healthy', 'Healthy'),
        ('sick',    'Sick'),
        ('fever',   'Fever'),
        ('estrus',  'Estrus'),
    ]
    SEX_CHOICES = [('F', 'Female'), ('M', 'Male')]

    farm            = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='cattle')
    cattle_id       = models.CharField(max_length=20, unique=True)  # e.g. C001
    name            = models.CharField(max_length=100)
    breed           = models.CharField(max_length=50, choices=BREED_CHOICES)
    sex             = models.CharField(max_length=1, choices=SEX_CHOICES, default='F')
    age_years       = models.FloatField(default=1.0)
    weight_kg       = models.FloatField(default=300.0)
    lactating       = models.BooleanField(default=False)
    last_calved     = models.DateField(null=True, blank=True)

    # Live sensor snapshot (updated by simulation/sensor)
    temperature     = models.FloatField(default=38.5)
    activity        = models.IntegerField(default=70)   # 0-100 %
    feeding         = models.IntegerField(default=75)   # 0-100 %
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='healthy')
    notes           = models.TextField(blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.cattle_id} — {self.name} ({self.farm.name})"

    class Meta:
        ordering = ['cattle_id']
        verbose_name_plural = 'Cattle'


# ===================== SENSOR DEVICE =====================
class SensorDevice(models.Model):
    DEVICE_STATUS = [
        ('active',    'Active'),
        ('inactive',  'Inactive'),
        ('low_batt',  'Low Battery'),
        ('fault',     'Fault'),
    ]

    cattle          = models.OneToOneField(Cattle, on_delete=models.CASCADE, related_name='device')
    device_uid      = models.CharField(max_length=50, unique=True)      # e.g. DEV-C001-2026
    firmware_ver    = models.CharField(max_length=20, default='2.4.1')
    battery_pct     = models.IntegerField(default=100)
    last_ping       = models.DateTimeField(auto_now=True)
    status          = models.CharField(max_length=20, choices=DEVICE_STATUS, default='active')
    signal_strength = models.IntegerField(default=85)  # %

    def __str__(self):
        return f"{self.device_uid} → {self.cattle.name}"

    class Meta:
        verbose_name_plural = 'Sensor Devices'


# ===================== ALERT =====================
class Alert(models.Model):
    TYPE_CHOICES = [
        ('critical', 'Critical'),
        ('warning',  'Warning'),
        ('info',     'Info'),
    ]

    cattle          = models.ForeignKey(Cattle, on_delete=models.CASCADE, related_name='alerts')
    alert_type      = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title           = models.CharField(max_length=300)
    description     = models.TextField()
    icon            = models.CharField(max_length=10, default='⚠️')
    is_resolved     = models.BooleanField(default=False)
    resolved_at     = models.DateTimeField(null=True, blank=True)
    resolved_by     = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.alert_type.upper()}] {self.title}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Alerts'


# ===================== VET RECORD =====================
class VetRecord(models.Model):
    RECORD_TYPE = [
        ('treatment',   'Treatment'),
        ('vaccination', 'Vaccination'),
        ('checkup',     'Checkup'),
        ('surgery',     'Surgery'),
    ]

    cattle          = models.ForeignKey(Cattle, on_delete=models.CASCADE, related_name='vet_records')
    record_type     = models.CharField(max_length=30, choices=RECORD_TYPE)
    diagnosis       = models.CharField(max_length=300)
    treatment       = models.TextField()
    medicine        = models.CharField(max_length=200, blank=True)
    dosage          = models.CharField(max_length=100, blank=True)
    vet_name        = models.CharField(max_length=200, blank=True)
    cost            = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    follow_up_date  = models.DateField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.record_type} — {self.cattle.name} on {self.created_at.date()}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Vet Records'


# ===================== ALERT THRESHOLDS =====================
class AlertThreshold(models.Model):
    farm                = models.OneToOneField(Farm, on_delete=models.CASCADE, related_name='threshold')
    high_temp           = models.FloatField(default=39.5)
    low_temp            = models.FloatField(default=37.5)
    min_activity        = models.IntegerField(default=30)
    min_feeding         = models.IntegerField(default=40)
    push_notifications  = models.BooleanField(default=True)
    sms_alerts          = models.BooleanField(default=False)
    email_reports       = models.BooleanField(default=True)
    updated_at          = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Thresholds for {self.farm.name}"

    class Meta:
        verbose_name_plural = 'Alert Thresholds'


# ===================== FARMER PROFILE (COMMUNITY) =====================
class FarmerProfile(models.Model):
    farm            = models.OneToOneField(Farm, on_delete=models.CASCADE, related_name='profile')
    bio             = models.TextField(blank=True, max_length=500)
    expertise       = models.CharField(max_length=300, blank=True)  # e.g., "Dairy farming, cattle breeding"
    experience_years = models.IntegerField(default=0)
    profile_image   = models.CharField(max_length=500, blank=True)  # URL to image
    followers_count = models.IntegerField(default=0)
    following_count = models.IntegerField(default=0)
    is_verified     = models.BooleanField(default=False)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.farm.name}"

    class Meta:
        verbose_name_plural = 'Farmer Profiles'


# ===================== CONNECTION (FARMER CONNECTIONS) =====================
class Connection(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('accepted',  'Accepted'),
        ('blocked',   'Blocked'),
    ]

    from_farm       = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='connections_sent')
    to_farm         = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='connections_received')
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message         = models.TextField(blank=True, max_length=500)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.from_farm.name} → {self.to_farm.name} ({self.status})"

    class Meta:
        unique_together = ['from_farm', 'to_farm']
        verbose_name_plural = 'Connections'
        ordering = ['-created_at']


# ===================== COMMUNITY POST =====================
class CommunityPost(models.Model):
    POST_CATEGORY = [
        ('advice',      'Advice'),
        ('question',    'Question'),
        ('experience',  'Experience'),
        ('success',     'Success Story'),
        ('warning',     'Warning'),
        ('general',     'General'),
    ]

    farm            = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='community_posts')
    category        = models.CharField(max_length=30, choices=POST_CATEGORY, default='general')
    title           = models.CharField(max_length=300)
    content         = models.TextField()
    image_url       = models.CharField(max_length=500, blank=True)
    likes_count     = models.IntegerField(default=0)
    comments_count  = models.IntegerField(default=0)
    views_count     = models.IntegerField(default=0)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} by {self.farm.name}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Community Posts'


# ===================== POST COMMENT =====================
class PostComment(models.Model):
    post            = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='comments')
    farm            = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='post_comments')
    content         = models.TextField()
    likes_count     = models.IntegerField(default=0)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment by {self.farm.name} on {self.post.title}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Post Comments'


# ===================== POST LIKE =====================
class PostLike(models.Model):
    post            = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='post_likes')
    farm            = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='liked_posts')
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.farm.name} liked {self.post.title}"

    class Meta:
        unique_together = ['post', 'farm']
        verbose_name_plural = 'Post Likes'
