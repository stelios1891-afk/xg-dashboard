' Runs the scanner .bat HIDDEN (no console flash). Used by Task Scheduler.
CreateObject("Wscript.Shell").Run """" & "C:\Users\User\Desktop\Betting Model\run_scanner.bat" & """", 0, False
