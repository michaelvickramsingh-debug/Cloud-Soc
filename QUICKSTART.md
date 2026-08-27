# Quick Start Guide

## One-Click Startup

The simplest way to run CloudGuard:

```bash
python startup.py
```

This single command will:
1. ✅ Kill any old processes
2. ✅ Start backend (Flask) on http://127.0.0.1:5001
3. ✅ Start frontend (React) on http://127.0.0.1:3000
4. ✅ Automatically open the dashboard in your browser
5. ✅ Display service status

## Manual Startup (if needed)

### Terminal 1: Backend
```bash
cd backend
pip install -r requirements.txt  # First time only
python app.py
```

Backend runs at: **http://127.0.0.1:5001/api**

### Terminal 2: Frontend
```bash
cd frontend
npm install  # First time only
npm run dev
```

Frontend runs at: **http://127.0.0.1:3000**

## Stopping Services

Press `Ctrl+C` in the terminal where you ran `python startup.py`

Or manually kill processes:
```bash
killall python node npm
```

## Logs

Monitor services in real-time:
```bash
# Backend logs
tail -f /tmp/cloudguard_backend.log

# Frontend logs
tail -f /tmp/cloudguard_frontend.log
```

## Troubleshooting

### Port Already in Use
If port 5001 or 3000 is in use:
```bash
# Find what's using the port
lsof -i :5001
lsof -i :3000

# Kill the process
kill -9 <PID>
```

### Dependencies Missing
```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### API Connection Issues
The frontend is configured to call `http://127.0.0.1:5001/api`

If you change ports, update: `frontend/src/utils/api.js`
