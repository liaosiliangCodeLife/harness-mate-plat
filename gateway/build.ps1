# 构建 Windows / Linux 产物到 build/{platform}/{platform}-{version}-{timestamp}/
# 命名规则: platform-version-时间戳(到分钟)，例如 windows-v0.0.3-202607021430
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

$VersionFile = Join-Path $ProjectRoot "VERSION"
if (-not (Test-Path $VersionFile)) {
    Write-Error "未找到 VERSION 文件: $VersionFile"
}
$Version = (Get-Content $VersionFile -Raw).Trim()
if ($Version -eq "") {
    Write-Error "VERSION 文件内容为空"
}

$Timestamp = Get-Date -Format "yyyyMMddHHmm"
$LdFlags = "-s -w"

function New-PackageDir {
    param(
        [string]$Platform
    )
    $PackageName = "$Platform-$Version-$Timestamp"
    $PackageDir = Join-Path $ProjectRoot "build\$Platform\$PackageName"
    New-Item -ItemType Directory -Force -Path $PackageDir | Out-Null
    return $PackageDir
}

function Copy-RuntimeFiles {
    param(
        [string]$TargetDir,
        [string]$Platform
    )
    Copy-Item (Join-Path $ProjectRoot ".env.example") (Join-Path $TargetDir ".env.example") -Force
    Copy-Item (Join-Path $ProjectRoot "VERSION") (Join-Path $TargetDir "VERSION") -Force
    if ($Platform -eq "windows") {
        Copy-Item (Join-Path $ProjectRoot "build\windows\run.ps1") (Join-Path $TargetDir "run.ps1") -Force
        Copy-Item (Join-Path $ProjectRoot "build\windows\run.bat") (Join-Path $TargetDir "run.bat") -Force
    } else {
        Copy-Item (Join-Path $ProjectRoot "build\linux\run.sh") (Join-Path $TargetDir "run.sh") -Force
    }
}

if (-not (Get-Command go -ErrorAction SilentlyContinue)) {
    Write-Error "未找到 Go 工具链，请安装 Go 1.22+ 并加入 PATH"
}

Set-Location $ProjectRoot

# Windows amd64
$WindowsDir = New-PackageDir -Platform "windows"
$WindowsExe = Join-Path $WindowsDir "ws_gateway.exe"
$env:GOOS = "windows"
$env:GOARCH = "amd64"
go build -ldflags $LdFlags -o $WindowsExe .
Copy-RuntimeFiles -TargetDir $WindowsDir -Platform "windows"
Write-Host "Windows 构建完成: $WindowsDir"

# Linux amd64
$LinuxDir = New-PackageDir -Platform "linux"
$LinuxBin = Join-Path $LinuxDir "ws_gateway"
$env:GOOS = "linux"
$env:GOARCH = "amd64"
go build -ldflags $LdFlags -o $LinuxBin .
Copy-RuntimeFiles -TargetDir $LinuxDir -Platform "linux"
Write-Host "Linux 构建完成: $LinuxDir"

Remove-Item Env:GOOS -ErrorAction SilentlyContinue
Remove-Item Env:GOARCH -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "版本: $Version"
Write-Host "时间戳: $Timestamp"
Write-Host "产物目录:"
Write-Host "  build\windows\windows-$Version-$Timestamp"
Write-Host "  build\linux\linux-$Version-$Timestamp"
