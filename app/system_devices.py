from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List

POWERSHELL_SCRIPT = r"""
function Export-AsJson($items) {
    if ($items -eq $null) {
        return "[]"
    }
    return ($items | ConvertTo-Json -Depth 4)
}

try {
    $bluetoothDevices = Get-BluetoothDevice
    if ($bluetoothDevices) {
        $simplified = $bluetoothDevices | Select-Object Name, Address, Connected, Paired
        Export-AsJson $simplified
        exit 0
    }
} catch {
    # ignore and fallback
}

$pnpDevices = Get-PnpDevice -Class Bluetooth | Select-Object InstanceId, FriendlyName, Status
Export-AsJson $pnpDevices
"""


@dataclass
class ConnectedDevice:
    id: str
    name: str
    address: str
    is_connected: bool
    is_paired: bool


def _run_powershell() -> List[Dict[str, Any]]:
    print(f"[DEBUG] 执行 PowerShell 脚本: {POWERSHELL_SCRIPT[:100]}...")
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", POWERSHELL_SCRIPT],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",  # 处理非UTF-8字符
    )
    print(f"[DEBUG] PowerShell 返回码: {completed.returncode}")
    print(f"[DEBUG] PowerShell stdout: {completed.stdout[:200]}...")
    print(f"[DEBUG] PowerShell stderr: {completed.stderr[:200]}...")
    
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"powershell 调用失败 (返回码: {completed.returncode})")
    data = completed.stdout.strip()
    if not data:
        print("[DEBUG] PowerShell 输出为空")
        return []
    try:
        result = json.loads(data)
        print(f"[DEBUG] JSON 解析成功，类型: {type(result)}")
        if isinstance(result, dict):
            return [result]
        if isinstance(result, list):
            return result
        return []
    except json.JSONDecodeError as exc:
        print(f"[DEBUG] JSON 解析失败: {exc}")
        print(f"[DEBUG] 原始数据: {data[:500]}...")
        raise RuntimeError(f"解析 powershell 输出失败: {exc}") from exc


def list_connected_bluetooth_devices() -> List[ConnectedDevice]:
    try:
        raw_devices = _run_powershell()
        print(f"[DEBUG] PowerShell returned {len(raw_devices)} raw devices")
        for i, device in enumerate(raw_devices):
            print(f"[DEBUG] Device {i}: {device}")
    except Exception as e:
        print(f"[DEBUG] PowerShell execution failed: {e}")
        return []

    devices: List[ConnectedDevice] = []
    for item in raw_devices:
        instance_id = item.get("InstanceId") or item.get("Address") or "unknown"
        name = item.get("Name") or item.get("FriendlyName") or "未知设备"
        address = item.get("Address") or _extract_address(instance_id) or instance_id
        is_connected = _bool_value(item.get("Connected")) or _status_connected(item.get("Status"))
        is_paired = _bool_value(item.get("Paired")) or True
        devices.append(
            ConnectedDevice(
                id=instance_id,
                name=name,
                address=address,
                is_connected=is_connected,
                is_paired=is_paired,
            )
        )
        print(f"[DEBUG] Added device: {name} ({address}) - connected: {is_connected}, paired: {is_paired}")
    devices.sort(key=lambda d: (not d.is_connected, d.name))
    print(f"[DEBUG] Final device list: {len(devices)} devices")
    return devices


def _extract_address(instance_id: str) -> str:
    match = re.search(r"DEV_([0-9A-F]{12})", instance_id, re.IGNORECASE)
    if match:
        raw = match.group(1)
        parts = [raw[i : i + 2] for i in range(0, len(raw), 2)]
        return ":".join(parts)
    return ""


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "connected", "ok"}
    return False


def _status_connected(value: Any) -> bool:
    if value is None:
        return False
    return str(value).strip().upper() == "OK"
