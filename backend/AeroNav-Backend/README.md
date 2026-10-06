# AeroNav Backend

FastAPI backend for the AeroNav GPS-denied autonomous drone frontend.

## 1. Create and activate a virtual environment (Windows PowerShell)

```powershell
cd C:\Users\HP\Downloads\AeroNav-Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 2. Install dependencies

```powershell
pip install -r requirements.txt
```

## 3. Start the API

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API: http://localhost:8000
Docs: http://localhost:8000/docs

## Main endpoints

- GET `/api/health`
- GET `/api/telemetry`
- POST `/api/mission`
- POST `/api/simulation/failure`
- GET `/api/sensors`
- GET `/api/detections`
- GET `/api/path`
- GET `/api/analytics`

Example:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

Start a mission:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/mission -ContentType 'application/json' -Body '{"action":"start"}'
```

This backend is a hackathon simulation backend. It is ready to be connected to the AeroNav React frontend and can later be replaced/extended with real OpenCV, EKF, MAVLink/flight-controller and ground-tracking data.
