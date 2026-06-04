@echo off
chcp 65001 >nul
echo ==========================================
echo  智慧校园图书借阅信息管理系统 V2.0
echo  融合版启动脚本
echo ==========================================
echo.
echo [1] 启动 FastAPI 后端 + Vue 前端 (http://127.0.0.1:8080)
start cmd /k "set DB_PASSWORD=123456 && uvicorn app.main:app --host 0.0.0.0 --port 8080"
echo.
echo [2] 启动 Streamlit 大屏 (http://localhost:8501)
timeout /t 3 >nul
start cmd /k "streamlit run dashboard/app.py --server.port 8501"
echo.
echo 服务启动中，请稍候...
echo 后端文档: http://127.0.0.1:8080/docs
echo Vue 前端: http://127.0.0.1:8080
echo Streamlit 大屏: http://localhost:8501
pause
