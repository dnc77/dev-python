@echo off
if exist ..\plot-tool\local.db (
   del ..\plot-tool\local.db
)

python datagather.py
move /Y local.db ..\plot-tool\local.db
echo "Database local.db created"