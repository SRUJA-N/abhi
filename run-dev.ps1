Set-Location -LiteralPath $PSScriptRoot
& .\.venv\Scripts\python.exe -u manage.py runserver 127.0.0.1:8000 --noreload
