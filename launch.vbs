Set oShell = CreateObject("WScript.Shell")
oShell.Run "cmd /c cd /d ""C:\Users\Edwin Olaez\digital-sentinel"" && call .sentinel_env\Scripts\activate && python app.py", 0, False
