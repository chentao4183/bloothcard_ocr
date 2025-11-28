from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Rect:
    x: int
    y: int
    width: int
    height: int

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "Rect":
        return cls(
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            width=int(data.get("width", 0)),
            height=int(data.get("height", 0)),
        )

    def to_dict(self) -> Dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass
class OCRField:
    field_id: str
    name: str
    param_name: str
    enabled: bool = True
    default_value: str = ""
    recognition_area: Optional[Rect] = None
    sample_value: str = ""
    recognized_value: str = ""
    builtin: bool = False

    @classmethod
    def from_dict(cls, data: Dict) -> "OCRField":
        rect = data.get("recognition_area")
        return cls(
            field_id=data.get("field_id") or str(uuid.uuid4()),
            name=data.get("name", ""),
            param_name=data.get("param_name", ""),
            enabled=bool(data.get("enabled", True)),
            default_value=data.get("default_value", ""),
            recognition_area=Rect.from_dict(rect) if rect else None,
            sample_value=data.get("sample_value", ""),
            recognized_value=data.get("recognized_value", ""),
            builtin=bool(data.get("builtin", False)),
        )

    def to_dict(self) -> Dict:
        data = asdict(self)
        if self.recognition_area:
            data["recognition_area"] = self.recognition_area.to_dict()
        else:
            data["recognition_area"] = None
        return data


@dataclass
class ServiceVersionConfig:
    verify_url: str = ""
    bind_url: str = ""
    debug_url: str = ""  # 新增调试URL

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "ServiceVersionConfig":
        return cls(
            verify_url=data.get("verify_url", ""),
            bind_url=data.get("bind_url", ""),
            debug_url=data.get("debug_url", ""),
        )

    def to_dict(self) -> Dict[str, str]:
        return {"verify_url": self.verify_url, "bind_url": self.bind_url, "debug_url": self.debug_url}


@dataclass
class ServiceConfig:
    selected_version: str = "v1"
    versions: Dict[str, ServiceVersionConfig] = field(
        default_factory=lambda: {
            "v0": ServiceVersionConfig(
                verify_url="",
                bind_url="",
                debug_url="http://IP:62102/Interface/PersonnelBinding.aspx?",
            ),
            "v1": ServiceVersionConfig(
                verify_url="http://192.168.23.11:62102/Interface/Verify",
                bind_url="http://192.168.23.11:62102/Interface/Submit",
                debug_url="",
            ),
            "v2": ServiceVersionConfig(
                verify_url="http://10.10.5.116:62102/api/diagnosis/lk-application/getSingleApplicationDetail/",
                bind_url="http://192.168.23.11:62102/diagnosis/lk-application/bindSingleDiagnosis",
                debug_url="",
            ),
        }
    )
    enable_verification: bool = True
    popup_success: bool = True
    popup_failure: bool = True

    @classmethod
    def from_dict(cls, data: Dict) -> "ServiceConfig":
        versions_raw = data.get("versions", {})
        versions: Dict[str, ServiceVersionConfig] = {}
        for key, value in versions_raw.items():
            versions[key] = ServiceVersionConfig.from_dict(value or {})
        default_versions = cls().versions
        for key, value in default_versions.items():
            if key not in versions:
                versions[key] = value
        return cls(
            selected_version=data.get("selected_version", "v1"),
            versions=versions,
            enable_verification=bool(data.get("enable_verification", True)),
            popup_success=bool(data.get("popup_success", True)),
            popup_failure=bool(data.get("popup_failure", True)),
        )

    def to_dict(self) -> Dict:
        return {
            "selected_version": self.selected_version,
            "versions": {k: v.to_dict() for k, v in self.versions.items()},
            "enable_verification": self.enable_verification,
            "popup_success": self.popup_success,
            "popup_failure": self.popup_failure,
        }

    def get_selected_version(self) -> ServiceVersionConfig:
        return self.versions.get(self.selected_version) or next(iter(self.versions.values()))


@dataclass
class BackendConfig:
    submission_mode: str = "auto"  # auto or manual
    auto_delay_seconds: int = 5
    enable_startup: bool = False
    enable_float_input: bool = False
    enable_service: bool = True

    @classmethod
    def from_dict(cls, data: Dict) -> "BackendConfig":
        return cls(
            submission_mode=data.get("submission_mode", "auto"),
            auto_delay_seconds=int(data.get("auto_delay_seconds", 5)),
            enable_startup=bool(data.get("enable_startup", False)),
            enable_float_input=bool(data.get("enable_float_input", False)),
            enable_service=bool(data.get("enable_service", True)),
        )

    def to_dict(self) -> Dict:
        return {
            "submission_mode": self.submission_mode,
            "auto_delay_seconds": self.auto_delay_seconds,
            "enable_startup": self.enable_startup,
            "enable_float_input": self.enable_float_input,
            "enable_service": self.enable_service,
        }


@dataclass
class HidConfig:
    """HID监听配置"""
    enabled: bool = True
    device_keywords: List[str] = field(default_factory=lambda: ["Bluetooth", "Keyboard"])
    digit_length: int = 10
    require_enter: bool = False

    @classmethod
    def from_dict(cls, data: Dict) -> "HidConfig":
        keywords = data.get("device_keywords", [])
        if isinstance(keywords, str):
            keywords = [kw.strip() for kw in keywords.split(",") if kw.strip()]
        return cls(
            enabled=bool(data.get("enabled", True)),
            device_keywords=[kw for kw in keywords if kw],
            digit_length=int(data.get("digit_length", 10)),
            require_enter=bool(data.get("require_enter", True)),
        )

    def to_dict(self) -> Dict:
        return {
            "enabled": self.enabled,
            "device_keywords": list(self.device_keywords),
            "digit_length": self.digit_length,
            "require_enter": self.require_enter,
        }


@dataclass
class AppConfig:
    ocr_fields: List[OCRField] = field(default_factory=list)
    service: ServiceConfig = field(default_factory=ServiceConfig)
    backend: BackendConfig = field(default_factory=BackendConfig)
    hid: HidConfig = field(default_factory=HidConfig)

    @classmethod
    def default(cls) -> "AppConfig":
        fields = [
            OCRField(field_id=str(uuid.uuid4()), name="卡ID", param_name="RFID", builtin=True),
            OCRField(field_id=str(uuid.uuid4()), name="诊疗时间", param_name="Treatime", builtin=True),
            OCRField(field_id=str(uuid.uuid4()), name="唯一ID", param_name="Number1", sample_value="ID001"),
            OCRField(field_id=str(uuid.uuid4()), name="流水号", param_name="LSNumber2", sample_value="SN001"),
            OCRField(field_id=str(uuid.uuid4()), name="姓名", param_name="DJName", sample_value="张三"),
            OCRField(field_id=str(uuid.uuid4()), name="年龄", param_name="Age", sample_value="23"),
            OCRField(field_id=str(uuid.uuid4()), name="性别", param_name="Sex", sample_value="男"),
            OCRField(field_id=str(uuid.uuid4()), name="医生", param_name="docName", sample_value="王医生"),
            OCRField(field_id=str(uuid.uuid4()), name="护士", param_name="auxiliaryNurse", sample_value="李护士"),
            OCRField(field_id=str(uuid.uuid4()), name="诊疗间", param_name="examiningTable", sample_value="诊疗间2"),
            OCRField(field_id=str(uuid.uuid4()), name="阴阳性", param_name="infectivity", default_value="1"),
        ]
        return cls(ocr_fields=fields)

    @classmethod
    def from_dict(cls, data: Dict) -> "AppConfig":
        fields_raw = data.get("ocr_fields", [])
        fields = [OCRField.from_dict(item or {}) for item in fields_raw]
        return cls(
            ocr_fields=fields if fields else cls.default().ocr_fields,
            service=ServiceConfig.from_dict(data.get("service", {})),
            backend=BackendConfig.from_dict(data.get("backend", {})),
            hid=HidConfig.from_dict(data.get("hid", {})),
        )

    def to_dict(self) -> Dict:
        return {
            "ocr_fields": [field.to_dict() for field in self.ocr_fields],
            "service": self.service.to_dict(),
            "backend": self.backend.to_dict(),
            "hid": self.hid.to_dict(),
        }


class ConfigManager:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppConfig:
        if not self.path.exists():
            config = AppConfig.default()
            self.save(config)
            return config
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return AppConfig.from_dict(data)
        except Exception:
            config = AppConfig.default()
            self.save(config)
            return config

    def save(self, config: AppConfig) -> None:
        serialized = json.dumps(config.to_dict(), ensure_ascii=False, indent=2)
        self.path.write_text(serialized, encoding="utf-8")



