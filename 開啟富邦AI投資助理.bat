@echo off
chcp 65001 >nul
title 富邦證券 AI 投資助理工作台 (Fubon Neo API)
echo ========================================================
echo   富邦證券 AI 投資助理 (Fubon Neo API v2.2.9)
echo   Model Context Protocol (MCP) Server & 視覺化工作台
echo ========================================================
echo.
echo 正在啟動富邦 AI 投資助理伺服器與 Web 工作台...
python run_gui.py
pause
