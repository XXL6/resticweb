Windows service bork wat do?
If Error 1053:
    Add python directory to the system PATH
    Also move (not sure if necessary)
        "pywintypes36.dll"

        From -> Python{pythonVersion}\Lib\site-packages\pywin32_system32
        
        To -> Python{pythonVersion}\Lib\site-packages\win32