param(
    [Parameter(Mandatory=$true)][string]$Version,
    [Parameter(Mandatory=$true)][string]$InputExecutable,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid installer version' }
$source = (Resolve-Path $InputExecutable).Path
$actual = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($source).ProductVersion
if ([version]$actual -ne [version]"$Version.0") { throw "EXE version $actual does not match installer $Version" }
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$destination = (Resolve-Path $OutputDirectory).Path
$compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($compiler) { $compiler = $compiler.Source }
else { $compiler = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe' }
if (-not (Test-Path $compiler)) { throw 'Inno Setup 6 is required to build the installer' }
$script = Join-Path $PSScriptRoot '..\pc\installer\CipherLink.iss'
& $compiler "/DAppVersion=$Version" "/DSourceExe=$source" "/DOutputDir=$destination" $script
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
$file = Join-Path $destination 'CipherLink-Windows-Setup.exe'
if (-not (Test-Path $file)) { throw 'Installer output is missing' }
$sum = (Get-FileHash $file -Algorithm SHA256).Hash.ToLower()
"$sum  CipherLink-Windows-Setup.exe" | Set-Content (Join-Path $destination 'CipherLink-Windows-Setup.exe.sha256') -Encoding ascii
