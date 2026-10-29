param(
    [Parameter(Mandatory=$true)][string]$PreviousInstaller,
    [Parameter(Mandatory=$true)][string]$CurrentInstaller,
    [Parameter(Mandatory=$true)][string]$CurrentVersion
)
$ErrorActionPreference = 'Stop'
$install = Join-Path $env:RUNNER_TEMP 'CipherLink installer test'
$uninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{E20AD5AC-9435-4B4D-A688-3759D01B5DBE}_is1'
$runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$dataFolder = Join-Path $env:USERPROFILE '.gametodo'
New-Item -ItemType Directory -Path $dataFolder -Force | Out-Null
$sentinel = Join-Path $dataFolder 'installer-test-preserve.txt'
$sentinelValue = [guid]::NewGuid().ToString()
Set-Content $sentinel $sentinelValue
function RunSetup([string]$File, [string[]]$Arguments) {
    $p = Start-Process -FilePath $File -ArgumentList $Arguments -Wait -PassThru
    if ($p.ExitCode -ne 0) { throw "Installer exit code $($p.ExitCode)" }
}
function CheckData {
    if ((Get-Content $sentinel -Raw).Trim() -ne $sentinelValue) { throw 'User data changed' }
}
RunSetup $PreviousInstaller @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',"/DIR=`"$install`"")
if (-not (Test-Path "$install\CipherLink.exe")) { throw 'Initial installation failed' }
if (-not (Test-Path $uninstallKey)) { throw 'Windows uninstall registration missing' }
CheckData
New-Item $runKey -Force | Out-Null
Set-ItemProperty $runKey CipherLink ('"' + "$install\CipherLink.exe" + '"')
# No /DIR: the upgrade must discover the preceding installation itself.
RunSetup $CurrentInstaller @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-')
if ((Get-ItemProperty $uninstallKey).DisplayVersion -ne $CurrentVersion) { throw 'Upgrade version not registered' }
$actual = [System.Diagnostics.FileVersionInfo]::GetVersionInfo("$install\CipherLink.exe").ProductVersion
if ([version]$actual -ne [version]"$CurrentVersion.0") { throw 'Upgrade did not replace the old EXE' }
CheckData
# An older setup must be rejected rather than downgrade the installed version.
$p = Start-Process $PreviousInstaller -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-' -Wait -PassThru
if ($p.ExitCode -eq 0) { throw 'Older installer unexpectedly succeeded' }
if ([System.Diagnostics.FileVersionInfo]::GetVersionInfo("$install\CipherLink.exe").ProductVersion -ne "$CurrentVersion.0") { throw 'Downgrade changed the EXE' }
# First uninstall preserves a startup command pointing to another portable copy.
$portable = '"C:\Other\CipherLink.exe"'
Set-ItemProperty $runKey CipherLink $portable
RunSetup "$install\unins000.exe" @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
if (Test-Path "$install\CipherLink.exe") { throw 'EXE remained after uninstall' }
if (Test-Path $uninstallKey) { throw 'Uninstall registration remained' }
if ((Get-ItemProperty $runKey).CipherLink -ne $portable) { throw 'Other portable startup command was removed' }
CheckData
# Reinstall migrates that owned portable path. Uninstall then removes only its own path.
RunSetup $CurrentInstaller @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',"/DIR=`"$install`"")
if ((Get-ItemProperty $runKey).CipherLink -ne ('"' + "$install\CipherLink.exe" + '"')) { throw 'Portable startup registration was not migrated' }
RunSetup "$install\unins000.exe" @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
if ($null -ne (Get-ItemProperty $runKey -Name CipherLink -ErrorAction SilentlyContinue)) { throw 'Owned startup registration remained' }
CheckData
Remove-Item $sentinel
Write-Output 'PASS: install, discover existing path, upgrade, reject downgrade, uninstall, preserve user data and foreign startup entry'
