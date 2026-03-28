# LiveStock IQ — Full Project Documentation

## Project File Structure

```
hackthon/
├── index.html                       ← Frontend (Mobile App UI)
├── styles.css                       ← Premium Dark-mode CSS
├── app.js                           ← Frontend JS (API-connected)

└── backend/
    ├── manage.py                    ← Django entry point
    ├── requirements.txt             ← Python dependencies
    ├── .env                         ← Environment config
    ├── setup_and_run.bat            ← One-click Windows setup
    ├── db_livestock.sqlite3         ← SQLite DB (auto-created)

    ├── livestock_project/           ← Django project package
    │   ├── settings.py              ← Dual DB config (SQLite + MongoDB)
    │   ├── urls.py                  ← Root URL config + Swagger docs
    │   └── wsgi.py

    └── api/                         ← Main Django app
        ├── models.py                ← SQLite ORM models (6 tables)
        ├── mongo_models.py          ← MongoDB schemas + helpers
        ├── serializers.py           ← DRF serializers
        ├── views.py                 ← All API views
        ├── urls.py                  ← 20+ API routes
        ├── admin.py                 ← Admin panel
        └── management/commands/
            └── seed_data.py         ← Seeds SQLite + MongoDB
```

---

## Database Architecture

### SQLite (Relational) — Django ORM

| Table | Purpose |
|-------|---------|
| api_farm | Farm and farmer details |
| api_cattle | Individual cattle + live sensor snapshot |
| api_sensordevice | IoT wearable device registry |
| api_alert | Health alerts (critical / warning / info) |
| api_vetrecord | Veterinary treatments and records |
| api_alertthreshold | Per-farm configurable thresholds |

### MongoDB (Time-Series) — PyMongo

| Collection | Purpose |
|------------|---------|
| sensor_readings | High-frequency raw sensor data (TTL: 90 days) |
| herd_snapshots | Hourly farm-level aggregated snapshots (TTL: 1 year) |
| event_log | Anomaly events log (fever, estrus, sensor reconnect) |

---

## REST API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/register/ | Register new farmer |
| POST | /api/v1/auth/token/ | Get JWT access token |
| POST | /api/v1/auth/token/refresh/ | Refresh JWT token |

### Farm and Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/farm/ | Get farm info |
| PUT | /api/v1/farm/ | Update farm info |
| GET | /api/v1/farm/dashboard/ | Full dashboard summary |
| GET | /api/v1/farm/analytics/ | Chart data for analytics page |

### Cattle
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/cattle/ | List all cattle (filter, search, paginate) |
| POST | /api/v1/cattle/ | Add new cattle |
| GET | /api/v1/cattle/{id}/ | Cattle detail + alerts + vet records |
| PUT | /api/v1/cattle/{id}/ | Update cattle |
| DELETE | /api/v1/cattle/{id}/ | Remove cattle |
| POST | /api/v1/cattle/{id}/treat/ | Mark cattle as treated |
| GET | /api/v1/cattle/{id}/history/ | Sensor history from MongoDB |
| GET | /api/v1/cattle/{id}/events/ | Event log from MongoDB |

### Sensors (IoT)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/sensors/push/ | Receive live sensor data → MongoDB + SQLite |
| POST | /api/v1/sensors/simulate/ | Simulate one sensor tick for all cattle |

### Alerts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/alerts/ | List alerts (filter by type/resolved status) |
| POST | /api/v1/alerts/{id}/resolve/ | Resolve an alert |

### Vet Records
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/vet-records/ | List vet records |
| POST | /api/v1/vet-records/ | Create new vet record |

### Thresholds
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/thresholds/ | Get alert thresholds |
| PUT | /api/v1/thresholds/ | Update thresholds |

### MongoDB
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/mongo/stats/ | MongoDB collection stats |
| GET | /api/v1/mongo/snapshots/ | Recent 24h herd snapshots |

---

## How to Run

### Prerequisites
- Python 3.10+
- MongoDB Community Edition (optional — app works without it)

### Option A: One-Click Windows Setup

```
cd hackthon\backend
setup_and_run.bat
```

### Option B: Manual Steps

```bash
cd hackthon/backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Migrate SQLite database
python manage.py makemigrations
python manage.py migrate

# Seed all demo data (23 cattle, alerts, vet records, MongoDB readings)
python manage.py seed_data

# Start server
python manage.py runserver
```

### URLs After Starting

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000/ | Frontend App |
| http://127.0.0.1:8000/admin/ | Django Admin (admin / admin123) |
| http://127.0.0.1:8000/api/v1/ | REST API Root |
| http://127.0.0.1:8000/api/docs/ | Swagger UI |
| http://127.0.0.1:8000/api/redoc/ | ReDoc |

---

## Health Detection Logic

```
Temperature >= 39.5C   →  FEVER    (Critical Alert in SQL + MongoDB event)
Activity < 30% or
Feeding < 40%          →  SICK     (Warning Alert)
Activity spike > 85%
(female cattle)        →  ESTRUS   (Info Alert for breeding)
All vitals normal      →  HEALTHY
```

## Sensor Data Flow

```
Frontend timer (every 10 sec)
        |
        v
POST /api/v1/sensors/push/  (one call per cattle)
        |
        v
Django SensorPushView
    ├── Detect anomaly type
    ├── Write to MongoDB:  sensor_readings collection
    ├── Write to MongoDB:  event_log (if anomaly)
    ├── Update SQLite:     cattle.temperature/activity/feeding/status
    └── Create SQL Alert:  if status worsened
```

---

## Python Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Django | 4.2.10 | Web framework |
| djangorestframework | 3.15.1 | REST API |
| django-cors-headers | 4.3.1 | CORS for frontend |
| pymongo | 4.6.2 | MongoDB driver |
| djangorestframework-simplejwt | 5.3.1 | JWT auth |
| django-filter | 23.5 | API filtering |
| drf-yasg | 1.21.7 | Swagger/OpenAPI docs |
| python-dotenv | 1.0.1 | Environment config |

---

Built for Hackathon 2026
