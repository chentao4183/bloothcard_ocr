param(
    [string] $Python = ".\\.venv\\Scripts\\python.exe",
    [string] $Name = "BLEBlueTool"
)

Write-Host "[build] 使用 Python: $Python"

if (-not (Test-Path $Python)) {
    Write-Host "[build] 未找到虚拟环境 Python,可尝试创建: python -m venv .venv" -ForegroundColor Yellow
}

# 确保安装构建依赖
& $Python -m pip install -U pip setuptools wheel | Out-Null
if (Test-Path "requirements-build.txt") {
    & $Python -m pip install -r requirements-build.txt | Out-Null
} else {
    & $Python -m pip install pyinstaller | Out-Null
}

$hidden = @(
    "winrt.windows.devices.bluetooth",
    "winrt.windows.devices.enumeration",
    "winrt.windows.devices.bluetooth.genericattributeprofile",
    "winrt.windows.foundation",
    "winrt.windows.storage.streams"
)

$hiddenArgs = $hidden | ForEach-Object { "--hidden-import", $_ }

$args = @(
    "-F",                  # 单文件
    "-w",                  # 无控制台窗口（GUI）
    "-n", $Name,
    "app/main.py"          # 直接以主程序作为入口，避免相对导入问题
) + $hiddenArgs

Write-Host "[build] 运行 PyInstaller..." -ForegroundColor Cyan
& $Python -m PyInstaller @args

Write-Host "[build] 完成。输出: dist/$Name.exe" -ForegroundColor Green

