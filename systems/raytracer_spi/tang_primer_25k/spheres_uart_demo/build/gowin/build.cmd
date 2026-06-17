@echo off
set GW_SH=C:\Gowin\Gowin_V1.9.12.02_SP1_x64\IDE\bin\gw_sh.exe
if not exist "%GW_SH%" (
  echo Gowin shell not found: %GW_SH%
  exit /b 1
)
"%GW_SH%" create_project.tcl
"%GW_SH%" build.tcl
