param(
    [string]$Python = "python",
    [string]$ISCCPath = "",
    [string]$DistPath = "",
    [string]$WorkPath = "",
    [string]$OutputPath = "",
    [switch]$SkipTests,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
if (-not $DistPath) { $DistPath = Join-Path $projectRoot "dist" }
if (-not $WorkPath) { $WorkPath = Join-Path $projectRoot "build" }
if (-not $OutputPath) { $OutputPath = Join-Path $projectRoot "artifacts" }
$DistPath = [IO.Path]::GetFullPath($DistPath)
$WorkPath = [IO.Path]::GetFullPath($WorkPath)
$OutputPath = [IO.Path]::GetFullPath($OutputPath)

Push-Location $projectRoot
try {
    if (-not $SkipTests) {
        & $Python -m unittest discover -s tests -v
        if ($LASTEXITCODE -ne 0) { throw "Tests failed." }
    }
    $appVersion = (& $Python -c "from version import __version__; print(__version__)").Trim()
    if ($LASTEXITCODE -ne 0) { throw "Cannot read application version." }
    & $Python -m PyInstaller --noconfirm --distpath $DistPath --workpath $WorkPath 3DUltimator.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

    New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
    $appDirectory = Join-Path $DistPath "3DUltimator"
    Copy-Item -LiteralPath (Join-Path $projectRoot "README.md") -Destination $appDirectory -Force
    Copy-Item -LiteralPath (Join-Path $projectRoot "AUTHORS.md") -Destination $appDirectory -Force
    Copy-Item -LiteralPath (Join-Path $projectRoot "examples") -Destination $appDirectory -Recurse -Force
    $portableName = "3DUltimator-$appVersion-windows-x64-portable.zip"
    & $Python -c "import shutil,sys; shutil.make_archive(sys.argv[1], 'zip', root_dir=sys.argv[2], base_dir='3DUltimator')" (Join-Path $OutputPath $portableName.Replace('.zip', '')) $DistPath
    if ($LASTEXITCODE -ne 0) { throw "Portable archive creation failed." }

    if (-not $SkipInstaller) {
        if (-not $ISCCPath) {
            $compilerCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
            if ($compilerCommand) { $ISCCPath = $compilerCommand.Source }
        }
        if (-not $ISCCPath) {
            foreach ($candidate in @(
                "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
                "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
                "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
                "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
            )) {
                if (Test-Path -LiteralPath $candidate) { $ISCCPath = $candidate; break }
            }
        }
        if (-not $ISCCPath -or -not (Test-Path -LiteralPath $ISCCPath)) {
            throw "Inno Setup compiler not found. Install Inno Setup 6.3+ or 7, pass -ISCCPath, or use -SkipInstaller."
        }
        & $ISCCPath "/DMyAppVersion=$appVersion" "/DAppSource=$appDirectory" "/O$OutputPath" (Join-Path $projectRoot "installer\3DUltimator.iss")
        if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed." }
    }

    $releaseFiles = Get-ChildItem -LiteralPath $OutputPath -File | Where-Object {
        $_.Name -eq $portableName -or $_.Name -eq "3DUltimator-Setup-$appVersion-windows-x64.exe"
    }
    $hashLines = foreach ($releaseFile in $releaseFiles) {
        $hashValue = Get-FileHash -LiteralPath $releaseFile.FullName -Algorithm SHA256
        "$($hashValue.Hash.ToLowerInvariant())  $($releaseFile.Name)"
    }
    $hashLines | Set-Content -LiteralPath (Join-Path $OutputPath "SHA256SUMS.txt") -Encoding ascii
    Write-Output "Release $appVersion ready in $OutputPath"
}
finally {
    Pop-Location
}
