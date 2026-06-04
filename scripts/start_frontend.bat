@echo off
chcp 65001 >nul
cd /d "C:\Users\think\Desktop\软著\smart_library_fusion"
streamlit run dashboard/app.py --server.port 8501
