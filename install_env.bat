@echo off
echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install flask requests feishu-open-api-sdk

echo Setting up local baidupcs-py (No C++ required)...
python setup_libs.py

echo.
echo Setup Complete. You can now run the integration:
echo python run_integration.py
pause
