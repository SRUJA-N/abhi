$job = Start-Job -ScriptBlock {
    Set-Location -LiteralPath 'c:\Users\Abhinaya Sarsu\OneDrive\Desktop\project\event_management'
    & .\.venv\Scripts\python.exe -u manage.py runserver 127.0.0.1:8000 --noreload
}

while ($true) {
    Start-Sleep -Seconds 3600
}
