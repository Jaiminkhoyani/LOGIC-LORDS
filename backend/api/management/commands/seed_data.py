"""
LiveStock IQ — Seed Data Command

Usage:
    python manage.py seed_data

Seeds:
  - 1 demo farmer (admin / admin123)
  - 1 farm (Green Valley Farm, Haryana, India)
  - 23 cattle with realistic data
  - Sensor devices for each cattle
  - Sample alerts
  - Sample vet records
  - Alert thresholds
  - MongoDB sensor readings (if MongoDB available)
"""

import random
from datetime import date, timedelta, datetime

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from api.models import Farm, Cattle, SensorDevice, Alert, VetRecord, AlertThreshold
from api import mongo_models as mongo


CATTLE_DATA = [
    ('C001', 'Ganga',        'HF Cross',     4, 420,  39.8, 22, 35, 'sick',    True,  '2025-11-03', 'Showing signs of respiratory distress'),
    ('C002', 'Yamuna',       'Sahiwal',       6, 385,  38.4, 78, 85, 'healthy', True,  '2026-01-18', 'All vitals normal'),
    ('C003', 'Kaveri',       'Gir',           3, 360,  38.9, 91, 72, 'estrus',  False, None,         'High activity spike — estrus detected'),
    ('C004', 'Godavari',     'HF Cross',      5, 440,  40.1, 18, 28, 'fever',   True,  '2025-09-22', 'High fever — requires immediate attention'),
    ('C005', 'Saraswati',    'Murrah',        7, 510,  38.5, 65, 80, 'healthy', True,  '2025-12-30', 'Stable vitals, good milk production'),
    ('C006', 'Narmada',      'Jersey Cross',  4, 390,  38.2, 70, 90, 'healthy', True,  '2026-02-05', 'Excellent feeder'),
    ('C007', 'Mahanadi',     'Sahiwal',       2, 320,  38.7, 88, 68, 'estrus',  False, None,         'First estrus cycle detected'),
    ('C008', 'Tapi',         'Gir',           8, 475,  38.3, 55, 77, 'healthy', True,  '2025-10-14', 'Slightly lower activity — monitor'),
    ('C009', 'Krishna',      'HF Cross',      5, 415,  39.2, 42, 60, 'sick',    True,  '2025-08-10', 'Mild infection suspected'),
    ('C010', 'Alaknanda',    'Sahiwal',       3, 345,  38.6, 72, 82, 'healthy', False, None,         'Growing well'),
    ('C011', 'Bhagirathi',   'Murrah',        6, 505,  38.1, 80, 91, 'healthy', True,  '2026-01-01', 'Top producer this month'),
    ('C012', 'Betwa',        'Jersey Cross',  4, 400,  38.4, 68, 79, 'healthy', True,  '2025-11-20', 'Normal vitals'),
    ('C013', 'Chambal',      'Gir',           9, 490,  38.0, 50, 70, 'healthy', True,  '2025-07-05', 'Senior cow, monitor regularly'),
    ('C014', 'Sone',         'HF Cross',      2, 310,  38.5, 84, 76, 'healthy', False, None,         'Young, energetic heifer'),
    ('C015', 'Tapti',        'Sahiwal',       5, 395,  38.3, 73, 83, 'healthy', True,  '2025-12-10', 'Healthy, good milk yield'),
    ('C016', 'Mandakini',    'Gir',           3, 330,  39.0, 38, 45, 'sick',    False, None,         'Reduced feeding — check for lameness'),
    ('C017', 'Pinakini',     'Jersey Cross',  7, 455,  38.1, 62, 78, 'healthy', True,  '2025-09-01', 'Stable'),
    ('C018', 'Periyar',      'Murrah',        4, 480,  38.7, 75, 87, 'healthy', True,  '2026-02-25', 'Good milker'),
    ('C019', 'Penna',        'HF Cross',      6, 430,  38.5, 69, 80, 'healthy', True,  '2025-10-30', 'Normal'),
    ('C020', 'Tungabhadra',  'Sahiwal',       3, 350,  38.2, 82, 74, 'healthy', False, None,         'Active and growing'),
    ('C021', 'Sharavathi',   'Gir',           5, 410,  38.6, 66, 85, 'healthy', True,  '2025-11-15', 'Steady producer'),
    ('C022', 'Kabini',       'HF Cross',      2, 300,  38.3, 86, 71, 'healthy', False, None,         'Young heifer, healthy'),
    ('C023', 'Kapila',       'Murrah',        8, 500,  38.0, 48, 65, 'healthy', True,  '2025-08-20', 'Senior — lower activity normal for age'),
]


class Command(BaseCommand):
    help = 'Seed demo data for LiveStock IQ hackathon demo'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n🌱 Seeding LiveStock IQ demo data...\n'))

        # 1. Create superuser
        user, created = User.objects.get_or_create(username='admin')
        if created:
            user.set_password('admin123')
            user.first_name = 'Rajesh'
            user.last_name  = 'Kumar'
            user.email      = 'rajesh@greenvalleyfarm.com'
            user.is_staff   = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS('✅ Admin user created: admin / admin123'))
        else:
            self.stdout.write('   Admin user already exists.')

        # 2. Create Farm
        farm, _ = Farm.objects.get_or_create(
            owner=user,
            defaults={
                'name':     'Green Valley Farm',
                'location': 'Hisar',
                'state':    'Haryana',
                'country':  'India',
                'phone':    '+91-9876543210',
            }
        )
        self.stdout.write(self.style.SUCCESS(f'✅ Farm: {farm.name}'))

        # 3. Thresholds
        AlertThreshold.objects.get_or_create(
            farm=farm,
            defaults={'high_temp': 39.5, 'low_temp': 37.5, 'min_activity': 30, 'min_feeding': 40}
        )

        # 4. Cattle + Devices
        created_cattle = 0
        for row in CATTLE_DATA:
            (cid, name, breed, age, weight, temp, act, feed,
             stat, lact, last_calved, notes) = row

            calved_date = date.fromisoformat(last_calved) if last_calved else None

            cattle, c = Cattle.objects.get_or_create(
                cattle_id=cid,
                defaults={
                    'farm':        farm,
                    'name':        name,
                    'breed':       breed,
                    'sex':         'F',
                    'age_years':   age,
                    'weight_kg':   weight,
                    'lactating':   lact,
                    'last_calved': calved_date,
                    'temperature': temp,
                    'activity':    act,
                    'feeding':     feed,
                    'status':      stat,
                    'notes':       notes,
                }
            )
            if c:
                created_cattle += 1

            # Sensor device
            SensorDevice.objects.get_or_create(
                cattle=cattle,
                defaults={
                    'device_uid':      f'DEV-{cid}-2026',
                    'firmware_ver':    '2.4.1',
                    'battery_pct':     random.randint(70, 100),
                    'signal_strength': random.randint(75, 100),
                    'status':          'active',
                }
            )

        self.stdout.write(self.style.SUCCESS(f'✅ {created_cattle} cattle created ({len(CATTLE_DATA)} total)'))

        # 5. Alerts
        if Alert.objects.count() == 0:
            c004 = Cattle.objects.get(cattle_id='C004')
            c001 = Cattle.objects.get(cattle_id='C001')
            c003 = Cattle.objects.get(cattle_id='C003')
            c007 = Cattle.objects.get(cattle_id='C007')
            c009 = Cattle.objects.get(cattle_id='C009')
            c016 = Cattle.objects.get(cattle_id='C016')

            Alert.objects.bulk_create([
                Alert(cattle=c004, alert_type='critical', icon='🔥',
                      title='High Fever Detected — Godavari',
                      description='Temperature 40.1°C exceeds critical threshold (39.5°C). Immediate vet required.'),
                Alert(cattle=c001, alert_type='critical', icon='🤒',
                      title='Illness Suspected — Ganga',
                      description='Temp 39.8°C with low activity (22%) and poor feeding (35%). Likely respiratory infection.'),
                Alert(cattle=c003, alert_type='info', icon='💜',
                      title='Estrus Detected — Kaveri',
                      description='Activity spike of 91% sustained for 3+ hours. Breeding window: next 6–18 hours.'),
                Alert(cattle=c007, alert_type='info', icon='💜',
                      title='Estrus Detected — Mahanadi',
                      description='First estrus cycle detected. High activity pattern confirmed.'),
                Alert(cattle=c009, alert_type='warning', icon='⚠️',
                      title='Mild Illness — Krishna',
                      description='Elevated temperature (39.2°C) with reduced activity. Monitor closely.'),
                Alert(cattle=c016, alert_type='warning', icon='🌿',
                      title='Low Feeding Alert — Mandakini',
                      description='Feeding index 45% — below threshold. Check for lameness or dental issues.'),
            ])
            self.stdout.write(self.style.SUCCESS('✅ 6 sample alerts created'))

        # 6. Vet Records
        if VetRecord.objects.count() == 0:
            c001 = Cattle.objects.get(cattle_id='C001')
            c004 = Cattle.objects.get(cattle_id='C004')
            VetRecord.objects.bulk_create([
                VetRecord(cattle=c001, record_type='treatment', diagnosis='Bovine Respiratory Disease',
                          treatment='Antibiotic therapy + supportive care',
                          medicine='Oxytetracycline', dosage='10 mg/kg IM once daily × 3 days',
                          vet_name='Dr. Suresh Patel', cost=850,
                          follow_up_date=date.today() + timedelta(days=3)),
                VetRecord(cattle=c004, record_type='treatment', diagnosis='Bacterial fever (suspected Pasteurellosis)',
                          treatment='IV fluids + antipyretic + antibiotic',
                          medicine='Enrofloxacin + Meloxicam', dosage='5 mg/kg IV BD',
                          vet_name='Dr. Suresh Patel', cost=1200,
                          follow_up_date=date.today() + timedelta(days=2)),
                VetRecord(cattle=c001, record_type='vaccination', diagnosis='Annual FMD vaccination',
                          treatment='FMD polyvalent vaccine', medicine='Raksha Ovac',
                          dosage='2 mL SC', vet_name='Dr. Suresh Patel', cost=150),
            ])
            self.stdout.write(self.style.SUCCESS('✅ 3 vet records created'))

        # 7. MongoDB — seed sensor readings
        self.stdout.write('\n📡 Seeding MongoDB sensor readings...')
        try:
            mongo.setup_mongodb_indexes()
            col = mongo.get_collection('sensor_readings')
            if col.count_documents({}) == 0:
                docs = []
                now = datetime.utcnow()
                for cattle_row in CATTLE_DATA:
                    cid  = cattle_row[0]
                    temp = cattle_row[5]
                    act  = cattle_row[6]
                    feed = cattle_row[7]
                    for h in range(24):
                        docs.append(mongo.build_sensor_reading(
                            cattle_id   = cid,
                            temperature = round(temp + random.uniform(-0.4, 0.4), 2),
                            activity    = max(5, min(100, act + random.randint(-10, 10))),
                            feeding     = max(5, min(100, feed + random.randint(-8, 8))),
                            battery_pct = random.randint(75, 100),
                        ))
                        # Override timestamp to spread over 24h
                        docs[-1]['timestamp'] = now - timedelta(hours=23-h)

                col.insert_many(docs)
                inserted = len(docs)
                self.stdout.write(self.style.SUCCESS(f'✅ {inserted} MongoDB sensor readings inserted'))

                # Herd snapshots
                snap_col = mongo.get_collection('herd_snapshots')
                snaps = []
                for h in range(24):
                    snaps.append(mongo.build_herd_snapshot(
                        farm_id=farm.id,
                        hour=now - timedelta(hours=23-h),
                        avg_temp=round(random.uniform(38.1, 39.0), 2),
                        avg_activity=round(random.uniform(60, 82), 1),
                        avg_feeding=round(random.uniform(65, 88), 1),
                        healthy=18, sick=3, fever=1, estrus=1, total=23
                    ))
                snap_col.insert_many(snaps)
                self.stdout.write(self.style.SUCCESS(f'✅ 24 MongoDB herd snapshots inserted'))
            else:
                self.stdout.write('   MongoDB data already exists.')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️  MongoDB unavailable — skipping: {e}'))
            self.stdout.write('   Start MongoDB and re-run to seed time-series data.')

        self.stdout.write(self.style.SUCCESS('\n🏆 Seed complete! Run the server:\n'))
        self.stdout.write('    cd backend')
        self.stdout.write('    python manage.py runserver\n')
        self.stdout.write('    Admin → http://127.0.0.1:8000/admin/   (admin / admin123)')
        self.stdout.write('    API   → http://127.0.0.1:8000/api/v1/')
        self.stdout.write('    Docs  → http://127.0.0.1:8000/api/docs/\n')
