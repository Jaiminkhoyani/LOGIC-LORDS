@echo off
echo ============================================
echo  LiveStock IQ — Backend Setup Script
echo ============================================
echo.

:: Step 1: Create virtual environment
echo [1/5] Creating Python virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

:: Step 2: Install dependencies
echo [2/5] Installing Python dependencies...
pip install -r requirements.txt

:: Step 3: Run migrations
echo [3/5] Running Django migrations (SQLite)...
python manage.py makemigrations
python manage.py migrate

:: Step 4: Seed demo data
echo [4/5] Seeding demo data (SQLite + MongoDB)...
python manage.py seed_data

:: Step 5: Start server
echo [5/5] Starting Django development server...
echo.
echo  App     → http://127.0.0.1:8000/
echo  Admin   → http://127.0.0.1:8000/admin/      (admin / admin123)
echo  API     → http://127.0.0.1:8000/api/v1/
echo  Swagger → http://127.0.0.1:8000/api/docs/
echo.
python manage.py runserver

pause
