
# Verify Python installation
$pythonPath ="C:\Users\aamer\AppData\Local\Programs\Python\Python310\python.exe"

if(-not $PSBoundParameters.ContainsKey('workingDirOverride')) {
    $workingDirOverride = (Get-Location).Path
}

function Test-Admin {
    $currentUser = New-Object Security.Principal.WindowsPrincipal ([Security.Principal.WindowsIdentity]::GetCurrent())
    $currentUser.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
}

# If we are in a non-admin execution. Execute this script as admin
if ((Test-Admin) -eq $false)  {
    if ($shouldAssumeToBeElevated) {
        Write-Output "Elevating did not work :("

    } else {
        # add `-noexit` here for better debugging
        Start-Process powershell.exe -Verb RunAs -ArgumentList ("-noprofile -file `"$($myinvocation.MyCommand.Definition)`" -shouldAssumeToBeElevated -workingDirOverride `"$workingDirOverride`"")
    }
    exit
}

Set-Location "$workingDirOverride"
# END ELEVATE TO ADMIN

# Add actual commands to be executed in elevated mode here:
Write-Output "I get executed in an admin PowerShell"


# Get Python executable path
$pipPath = "$pythonPath"

# Install required libraries using pip
Start-Process -FilePath $pipPath -ArgumentList " -m pip install psutil" -Wait -NoNewWindow
Start-Process -FilePath $pipPath -ArgumentList " -m pip install pymongo" -Wait -NoNewWindow
Start-Process -FilePath $pipPath -ArgumentList " -m pip install pywin32" -Wait -NoNewWindow


$ServiceName="AamerServerMonitor"
try {
  # Attempt to get the service object
  $service = Get-Service $ServiceName -ErrorAction Stop

  # Service exists, proceed with deletion
  Write-Host "Service '$ServiceName' found."
C:\Windows\System32\sc stop "AamerServerMonitor"
C:\Windows\System32\sc delete "AamerServerMonitor"
Start-Process -FilePath $pipPath -ArgumentList " $PSScriptRoot/Service_Install.py install " -Wait -NoNewWindow
C:\Windows\System32\sc start "AamerServerMonitor"
}
catch {
  # Service not found or other error
 Start-Process -FilePath $pipPath -ArgumentList " $PSScriptRoot/Service_Install.py install " -Wait -NoNewWindow
C:\Windows\System32\sc start "AamerServerMonitor"
  } 

Pause