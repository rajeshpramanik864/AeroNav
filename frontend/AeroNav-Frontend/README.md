# AeroNav Final Connected Prototype

## Backend
```powershell
cd AeroNav-Backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
API docs: http://127.0.0.1:8000/docs

## Frontend
Open a second terminal:
```powershell
cd AeroNav-Frontend
npm install
npm run dev
```
Open the Vite URL shown in the terminal (normally http://localhost:5173/ or 5174 if 5173 is busy).

The frontend is connected to `http://127.0.0.1:8000` and polls telemetry, sensors, detections, path and analytics automatically.
