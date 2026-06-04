@echo off
chcp 65001 >nul
cd /d "C:\Users\think\Desktop\软著\smart_library_fusion"
set DB_PASSWORD=123456
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --log-level info
