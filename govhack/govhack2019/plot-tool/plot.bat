@echo off
if not exist local.db (
   echo 'Needs local.db'
   exit
)

python plot.py