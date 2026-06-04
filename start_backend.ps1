$env:PYTHONPATH="C:\Users\think\Desktop\软著\smart_library_fusion"
cd "C:\Users\think\Desktop\软著\smart_library_fusion"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 *> "C:\Users\think\Desktop\软著\smart_library_fusion\backend.log"
