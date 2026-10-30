param(
    [Parameter(Mandatory=$true)][string]$Installer,
    [Parameter(Mandatory=$true)][string]$Version,
    [ValidateSet('hidden','visible')][string]$Mode = 'hidden'
)
$ErrorActionPreference = 'Stop'
$root = Join-Path $env:RUNNER_TEMP ('CipherLink shutdown ' + [guid]::NewGuid().ToString('N'))
$install = Join-Path $root 'app'
$ready = Join-Path $root 'ready.txt'
$log = Join-Path $root 'setup.log'
$fixture = $null
New-Item -ItemType Directory -Path $root -Force | Out-Null

function RunInstaller([string]$Extra) {
    $arguments = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /CLOSEAPPLICATIONS /DIR=`"$install`" /LOG=`"$log`" $Extra"
    $process = Start-Process -FilePath $Installer -ArgumentList $arguments -PassThru
    if (-not $process.WaitForExit(90000)) {
        & taskkill.exe /PID $process.Id /T /F 2>$null | Out-Null
        Write-Output "::error::AUTOCLOSE_BLOCKED mode=$Mode installer timed out"
        throw 'Installer timed out while an application held the installed EXE'
    }
    return $process.ExitCode
}

try {
    $initial = RunInstaller ''
    if ($initial -ne 0) { throw "Initial installation failed: $initial" }
    $target = Join-Path $install 'CipherLink.exe'
    # Make replacement mandatory, then hold precisely the installer's target file.
    # The fixture does not read user settings or perform any network request.
    [System.IO.File]::WriteAllText($target, 'Synthetic locked application file')
    $source = Join-Path $root 'ShutdownFixture.cs'
    @'
using System;
using System.IO;
using System.Windows.Forms;
class ShutdownFixture : Form {
    private FileStream locked;
    private string ready;
    private bool hidden;
    ShutdownFixture(string[] args) {
        Text = "CipherLink shutdown fixture";
        locked = new FileStream(args[0], FileMode.Open, FileAccess.Read, FileShare.Read);
        ready = args[1]; hidden = args[2] == "hidden";
        ShowInTaskbar = !hidden;
        Shown += delegate { if (hidden) Hide(); File.WriteAllText(ready, "ready"); };
    }
    protected override void WndProc(ref Message message) {
        // Reproduce a hung/refusing background application without hanging the CI.
        if (message.Msg == 0x0011) { message.Result = IntPtr.Zero; return; }
        if (message.Msg == 0x0010 || message.Msg == 0x0016) return;
        base.WndProc(ref message);
    }
    [STAThread] static void Main(string[] args) {
        Application.Run(new ShutdownFixture(args));
    }
}
'@ | Set-Content $source -Encoding utf8BOM
    $executable = Join-Path $root 'ShutdownFixture.exe'
    $compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
    & $compiler /nologo /target:winexe /r:System.Windows.Forms.dll /r:System.Drawing.dll "/out:$executable" $source
    if ($LASTEXITCODE -ne 0) { throw 'Shutdown fixture compilation failed' }
    $fixture = Start-Process $executable -ArgumentList "`"$target`" `"$ready`" $Mode" -PassThru
    $deadline = [DateTime]::UtcNow.AddSeconds(15)
    while (-not (Test-Path $ready) -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 100 }
    if (-not (Test-Path $ready)) { throw 'Shutdown fixture did not start' }
    $exit = RunInstaller ''
    $fixture.Refresh()
    if ($exit -ne 0 -or -not $fixture.HasExited) {
        Write-Output "::error::AUTOCLOSE_BLOCKED mode=$Mode exit=$exit processStillRunning=$(-not $fixture.HasExited)"
        if (Test-Path $log) {
            Get-Content $log | Select-String -Pattern 'RestartManager|Restart Manager|could not|unable|error|reboot' | Select-Object -Last 12 | ForEach-Object { Write-Output $_.Line }
        }
        throw 'The installer did not close the running application'
    }
    $actual = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($target).ProductVersion
    if ([version]$actual -ne [version]"$Version.0") { throw 'The locked EXE was not replaced by the requested version' }
    Write-Output "PASS: mode=$Mode, process stopped and executable replaced with $Version"
} finally {
    if ($fixture) {
        $fixture.Refresh()
        if (-not $fixture.HasExited) { Stop-Process -Id $fixture.Id -Force -ErrorAction SilentlyContinue }
    }
    $uninstall = Join-Path $install 'unins000.exe'
    if (Test-Path $uninstall) {
        Start-Process $uninstall -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' -Wait | Out-Null
    }
    Remove-Item $root -Recurse -Force -ErrorAction SilentlyContinue
}
