import asyncio
import binascii
from typing import Callable, List, Optional

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData


class BleManager:
    def __init__(self) -> None:
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._client: Optional[BleakClient] = None
        self._on_log: Optional[Callable[[str], None]] = None
        self._on_devices_updated: Optional[Callable[[List[BLEDevice]], None]] = None
        self._on_device_event: Optional[Callable[[str, Optional[BLEDevice]], None]] = None
        self._on_card_data: Optional[Callable[[dict], None]] = None
        self._scanned_devices: List[BLEDevice] = []
        self._scan_task: Optional[asyncio.Task] = None

    def set_callbacks(
        self,
        on_log: Optional[Callable[[str], None]] = None,
        on_devices_updated: Optional[Callable[[List[BLEDevice]], None]] = None,
        on_device_event: Optional[Callable[[str, Optional[BLEDevice]], None]] = None,
        on_card_data: Optional[Callable[[dict], None]] = None,
    ) -> None:
        self._on_log = on_log
        self._on_devices_updated = on_devices_updated
        self._on_device_event = on_device_event
        self._on_card_data = on_card_data

    def assign_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def log(self, message: str) -> None:
        if self._on_log:
            self._on_log(message)

    async def scan(self, timeout: float = 5.0) -> List[BLEDevice]:
        self.log("开始扫描BLE设备...")

        def detection_callback(device: BLEDevice, adv: AdvertisementData) -> None:
            # 更新缓存列表（基于地址或UUID去重）
            if not any(d.address == device.address for d in self._scanned_devices):
                self._scanned_devices.append(device)
                if self._on_devices_updated:
                    self._on_devices_updated(list(self._scanned_devices))

        scanner = BleakScanner(detection_callback=detection_callback)
        await scanner.start()
        try:
            await asyncio.sleep(timeout)
        finally:
            await scanner.stop()

        # 兼容一次性获取
        devices = await BleakScanner.discover(timeout=0.1)
        for d in devices:
            if not any(x.address == d.address for x in self._scanned_devices):
                self._scanned_devices.append(d)
        if self._on_devices_updated:
            self._on_devices_updated(list(self._scanned_devices))
        self.log(f"扫描完成，共发现 {len(self._scanned_devices)} 个设备。")
        return list(self._scanned_devices)

    async def connect(self, device: BLEDevice) -> None:
        if self._client and self._client.is_connected:
            await self.disconnect()
        self.log(f"正在连接: {device.name or '未知设备'} ({device.address}) ...")
        self._client = BleakClient(device)
        await self._client.connect()
        if self._on_device_event:
            self._on_device_event("connected", device)
        self.log("连接成功。发现服务与特征...")
        await self._discover_and_subscribe()

    async def _discover_and_subscribe(self) -> None:
        assert self._client is not None
        # bleak 版本兼容：优先使用属性 services，若为空再尝试调用 get_services()
        services = getattr(self._client, "services", None)
        try:
            has_any = services is not None and any(True for _ in services)  # type: ignore
        except Exception:
            has_any = False
        if not has_any:
            get_services = getattr(self._client, "get_services", None)
            if callable(get_services):
                services = await get_services()
        notify_count = 0

        # 订阅所有支持 notify 的特征
        for service in services:
            self.log(f"发现服务: {service.uuid}")
            for char in service.characteristics:
                self.log(f"  特征: {char.uuid} | 属性: {','.join(char.properties)}")
                if "notify" in char.properties:
                    try:
                        await self._client.start_notify(char.uuid, self._notification_handler)
                        notify_count += 1
                        self.log(f"已订阅 Notify 特征: {char.uuid}")
                    except Exception as e:  # noqa: BLEAK-START-NOTIFY
                        self.log(f"订阅 {char.uuid} 失败: {e}")

        if notify_count == 0:
            self.log("未找到支持 Notify 的特征，可能无法接收数据。")
        else:
            self.log(f"已订阅 {notify_count} 个 Notify 特征，等待数据...")

    def _notification_handler(self, _: int, data: bytearray) -> None:
        hex_str = binascii.hexlify(bytes(data)).decode("ascii").upper()
        try:
            ascii_str = bytes(data).decode("utf-8", errors="ignore")
            ascii_printable = ''.join(c if 32 <= ord(c) <= 126 else '.' for c in ascii_str)
        except Exception:
            ascii_printable = ""
        # 解析 8H10D：
        # - 8H: 8位十六进制（通常对应4字节ID）；
        # - 10D: 将该ID转十进制并补零为10位（大小端都尝试）。
        import re
        raw = bytes(data)

        eight_hex_from_ascii = re.findall(r"\b([0-9A-Fa-f]{8})\b", ascii_printable)
        # 提取10位数，对于超过10位的数字，只取后10位
        ten_dec_from_ascii = re.findall(r"\b(\d{10})\b", ascii_printable)
        # 也提取超过10位的数字，后续处理时截取后10位
        long_dec_from_ascii = re.findall(r"\b(\d{11,})\b", ascii_printable)

        candidates = []  # (8H, 10D, source)

        # 从 ASCII 直接提取 8H/10D
        for h in eight_hex_from_ascii:
            try:
                val = int(h, 16)
                candidates.append((h.upper(), f"{val:010d}", "ascii-8H"))
            except Exception:
                pass
        for d in ten_dec_from_ascii:
            try:
                val = int(d)
                h = f"{val & 0xFFFFFFFF:08X}"  # 反推 8H，限制为32位
                candidates.append((h, f"{val:010d}", "ascii-10D"))
            except Exception:
                pass
        # 处理超过10位的数字，截取后10位
        for d in long_dec_from_ascii:
            try:
                # 截取后10位
                if len(d) > 10:
                    d = d[-10:]
                val = int(d)
                h = f"{val & 0xFFFFFFFF:08X}"  # 反推 8H，限制为32位
                candidates.append((h, f"{val:010d}", "ascii-10D-long"))
            except Exception:
                pass

        # 从原始字节中滑窗取4字节推断 8H10D（常见卡号长度）
        for i in range(0, max(0, len(raw) - 3)):
            chunk = raw[i:i+4]
            if len(chunk) < 4:
                continue
            try:
                v_be = int.from_bytes(chunk, "big")
                v_le = int.from_bytes(chunk, "little")
                candidates.append((f"{v_be:08X}", f"{v_be:010d}", "raw4-be"))
                candidates.append((f"{v_le:08X}", f"{v_le:010d}", "raw4-le"))
            except Exception:
                pass

        # 一些设备以5字节传输（低频ID设备常见），也尝试前5字节
        if len(raw) >= 5:
            chunk5 = raw[:5]
            try:
                v_be5 = int.from_bytes(chunk5, "big")
                v_le5 = int.from_bytes(chunk5, "little")
                # 只保留低32位映射到8H，10D保留完整值
                candidates.append((f"{(v_be5 & 0xFFFFFFFF):08X}", f"{v_be5:010d}", "raw5-be"))
                candidates.append((f"{(v_le5 & 0xFFFFFFFF):08X}", f"{v_le5:010d}", "raw5-le"))
            except Exception:
                pass

        # 去重并输出
        uniq = []
        for h, d, src in candidates:
            key = (h, d)
            if key not in [(x[0], x[1]) for x in uniq]:
                uniq.append((h, d, src))

        if uniq:
            pretty = ", ".join([f"8H={h},10D={d}({src})" for h, d, src in uniq[:6]])
            self.log(f"[通知] {pretty}")
            if self._on_card_data:
                best = uniq[0]
                self._on_card_data(
                    {
                        "hex": best[0],
                        "dec": best[1],
                        "source": best[2],
                        "raw_hex": hex_str,
                        "ascii": ascii_printable,
                    }
                )
        else:
            self.log(f"[通知] HEX: {hex_str} | ASCII: {ascii_printable}")

    async def disconnect(self) -> None:
        if self._client:
            try:
                self.log("断开连接...")
                await self._client.disconnect()
            finally:
                self._client = None
                self.log("已断开。")
                if self._on_device_event:
                    self._on_device_event("disconnected", None)

    def get_scanned_devices(self) -> List[BLEDevice]:
        return list(self._scanned_devices)




