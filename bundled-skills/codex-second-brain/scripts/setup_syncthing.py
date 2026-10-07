#!/usr/bin/env python3
"""Codex-invoked, local-only Syncthing bootstrap for codex-second-brain.

This helper is not a user-facing one-click installer. Codex runs preflight,
collects any missing Vault path in the conversation, then invokes apply.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import plistlib
import platform
import re
import shlex
import shutil
import socket
import ssl
import subprocess
import tarfile
import tempfile
import uuid
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse
from urllib.error import HTTPError
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
    urlopen,
)


PACK_ROOT = Path(__file__).resolve().parents[3]
LOCK_FILE = PACK_ROOT / "sources.lock.json"
DEVICE_CONFIG_RELATIVE = Path("second-brain") / "config.json"
SYNC_ONBOARDING_RELATIVE = Path("second-brain") / "sync-onboarding.json"
IGNORE_RULES = ("/.git", "/.claudian", "/.obsidian/workspace*")
IGNORE_START = "// codex-second-brain-syncthing-managed:start"
IGNORE_END = "// codex-second-brain-syncthing-managed:end"
FOLDER_ID = "codex-second-brain-vault"
FOLDER_LABEL = "第二大脑"
NETWORK_FALSE_FIELDS = (
    "globalAnnounceEnabled",
    "localAnnounceEnabled",
    "relaysEnabled",
    "natEnabled",
    "startBrowser",
)
SYNCTHING_ENVIRONMENT_KEYS = (
    "STGUIADDRESS",
    "STPAUSED",
    "STUNPAUSED",
    "STHOMEDIR",
    "STCONFDIR",
    "STDATADIR",
)
LOCAL_GUI_ADDRESS = "127.0.0.1:8384"
PAIRED_LISTENERS = (
    "tcp://127.0.0.1:22000",
    "dynamic+https://relays.syncthing.net/endpoint",
)
PAIRED_NETWORK_OPTIONS = {
    "globalAnnounceEnabled": "true",
    "localAnnounceEnabled": "false",
    "relaysEnabled": "true",
    "natEnabled": "false",
    "startBrowser": "false",
    "announceLANAddresses": "false",
}
SUPPORTED_MIN_VERSION = (2, 1, 5)
USER_AGENT = "codex-lazy-pack/0.10.0 Syncthing bootstrap"
_SNAPSHOT_UNSET = object()
_PROGRESS: dict[str, Any] = {"phase": "idle", "completed": [], "backupPath": None}


class SetupError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class StartupEntry:
    kind: str
    name: str
    executable: str
    arguments: str
    home: str | None
    enabled: bool = True
    source_path: str | None = None
    environment: dict[str, str] | None = None


def emit(payload: dict[str, Any], exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def run(args: list[str], *, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    encoding = "mbcs" if platform.system().lower() == "windows" else "utf-8"
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding=encoding,
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SetupError("command-failed", f"无法执行本机检查命令：{Path(args[0]).name}") from exc


def platform_key() -> str:
    system = platform.system().lower()
    if system == "windows":
        os_name = "windows"
    elif system == "darwin":
        os_name = "macos"
    elif system == "linux":
        os_name = "linux"
    else:
        raise SetupError("unsupported-platform", f"当前系统不在支持范围内：{system}")

    machine = platform.machine().lower()
    if machine in {"amd64", "x86_64", "x64"}:
        arch = "amd64"
    elif machine in {"arm64", "aarch64"}:
        arch = "arm64"
    else:
        raise SetupError("unsupported-architecture", f"当前架构不在支持范围内：{machine}")
    return f"{os_name}-{arch}"


def load_lock(lock_path: Path) -> tuple[str, dict[str, Any]]:
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
        package_version = data["package"]["version"]
        syncthing = data["runtimeDependencies"]["syncthing"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SetupError("lock-invalid", "无法读取懒人包版本锁或 Syncthing 锁定项。") from exc
    if not isinstance(syncthing, dict):
        raise SetupError("lock-invalid", "Syncthing 锁定项格式无效。")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", str(syncthing.get("version", ""))):
        raise SetupError("lock-invalid", "锁定的 Syncthing 版本格式无效。")
    return package_version, syncthing


def codex_home_from(value: str | None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    explicit = os.environ.get("CODEX_HOME")
    if explicit:
        return Path(explicit).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def normalize_path(value: str | Path) -> str:
    raw = os.path.expandvars(os.path.expanduser(str(value)))
    return os.path.normcase(os.path.abspath(os.path.normpath(raw)))


def same_path(left: str | Path, right: str | Path) -> bool:
    return normalize_path(left) == normalize_path(right)


def is_within_path(path: str | Path, root: str | Path) -> bool:
    candidate = Path(os.path.expandvars(os.path.expanduser(str(path)))).resolve()
    parent = Path(os.path.expandvars(os.path.expanduser(str(root)))).resolve()
    try:
        common = os.path.normcase(os.path.commonpath([str(candidate), str(parent)]))
    except ValueError:
        return False
    return common == os.path.normcase(str(parent))


def is_inside_git_repository(path: str | Path) -> bool:
    resolved = Path(path).resolve()
    for directory in (resolved, *resolved.parents):
        if (directory / ".git").exists():
            return True
    return False


def read_device_config(
    codex_home: Path, supplied_vault: str | None, *, role: str = "primary", allow_missing_vault: bool = False
) -> tuple[dict[str, Any], dict[str, Any], Path, Path, bytes | None]:
    config_path = codex_home / DEVICE_CONFIG_RELATIVE
    if (config_path.parent.is_symlink() or config_path.is_symlink()):
        raise SetupError("device-config-conflict", "第二大脑设备配置目录或文件是符号链接，未修改。")
    if config_path.exists() and not config_path.is_file():
        raise SetupError("device-config-conflict", "第二大脑设备配置路径不是普通文件，未修改。")

    original: dict[str, Any] = {}
    source_snapshot: bytes | None = None
    if config_path.exists():
        try:
            source_snapshot = config_path.read_bytes()
            loaded = json.loads(source_snapshot.decode("utf-8"))
        except (OSError, ValueError) as exc:
            raise SetupError("device-config-invalid", "第二大脑设备配置无法解析，未修改。") from exc
        if not isinstance(loaded, dict):
            raise SetupError("device-config-invalid", "第二大脑设备配置格式不是 JSON 对象，未修改。")
        original = loaded
        if original.get("schemaVersion") != 2:
            raise SetupError("device-config-schema", "设备配置不是 Schema 2；安装阶段不执行迁移。")

    configured_vault = original.get("vaultPath")
    if configured_vault and not isinstance(configured_vault, str):
        raise SetupError("vault-path-invalid", "设备配置中的 Vault 路径格式无效。")
    chosen = supplied_vault or configured_vault
    if not chosen:
        raise SetupError("vault-path-required", "设备配置缺少 Vault 路径，需要在对话中询问一次。")

    expanded_vault = Path(os.path.expandvars(os.path.expanduser(chosen)))
    if not expanded_vault.is_absolute():
        raise SetupError("vault-path-invalid", "Vault 路径必须是绝对路径；未修改设备配置。")
    if expanded_vault.is_symlink():
        raise SetupError("vault-path-conflict", "Vault 根目录是符号链接，未修改设备配置。")
    vault_path = expanded_vault.resolve()
    if vault_path.exists() and not vault_path.is_dir():
        raise SetupError("vault-path-missing", "Vault 路径不存在或不是目录；没有创建目录。")
    if not vault_path.exists():
        if not allow_missing_vault or role != "server":
            raise SetupError("vault-path-missing", "Vault 路径不存在；只有经用户确认的服务器接收目录可以在 apply 阶段创建。")
        if vault_path == vault_path.parent or not vault_path.parent.is_dir() or vault_path.parent.is_symlink():
            raise SetupError("server-vault-parent-invalid", "服务器 Vault 的父目录不存在、不是普通目录或为符号链接；未创建目录。")
    if supplied_vault and configured_vault and not same_path(supplied_vault, configured_vault):
        raise SetupError("vault-path-conflict", "输入路径与设备配置中的 Vault 路径不一致，未覆盖配置。")

    updated = dict(original)
    updated.setdefault("schemaVersion", 2)
    if not isinstance(updated.get("deviceId"), str) or not updated.get("deviceId", "").strip():
        updated["deviceId"] = str(uuid.uuid4())
    if not isinstance(updated.get("deviceLabel"), str) or not updated.get("deviceLabel", "").strip():
        updated["deviceLabel"] = socket.gethostname()
    updated["vaultPath"] = str(vault_path)
    updated.setdefault("syncMode", "syncthing")
    updated.setdefault("backupMode", "github-manual")
    expected_backup_role = role == "primary"
    existing_backup_role = original.get("gitBackupDevice")
    if type(existing_backup_role) is bool and existing_backup_role != expected_backup_role:
        raise SetupError("backup-role-conflict", "现有设备配置的 GitHub 备份角色与本次确认的 primary/server 角色冲突；未修改。")
    updated["gitBackupDevice"] = expected_backup_role
    updated.setdefault("writePolicy", "tiered")
    updated.setdefault("weeklyAutomationId", None)
    if updated.get("syncMode") != "syncthing":
        raise SetupError("sync-mode-conflict", "现有设备配置的同步方式不是 Syncthing，未修改。")
    if updated.get("backupMode") != "github-manual":
        raise SetupError("backup-mode-conflict", "现有 GitHub 备份策略不是手动模式，未修改。")
    return original, updated, vault_path, config_path, source_snapshot


def default_profile_dirs() -> list[Path]:
    home = Path.home()
    system = platform.system().lower()
    candidates: list[Path]
    if system == "windows":
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local"))
        roaming = Path(os.environ.get("APPDATA", home / "AppData/Roaming"))
        candidates = [
            local / "Syncthing",
            home / ".syncthing",
            home / ".config" / "syncthing",
            roaming / "Syncthing",
        ]
    elif system == "darwin":
        candidates = [
            home / "Library/Application Support/Syncthing",
            Path(os.environ.get("XDG_STATE_HOME", home / ".local/state")) / "syncthing",
            home / ".config/syncthing",
            home / ".syncthing",
        ]
    else:
        candidates = [
            Path(os.environ.get("XDG_STATE_HOME", home / ".local/state")) / "syncthing",
            home / ".local/state/syncthing",
            home / ".config/syncthing",
            home / ".syncthing",
        ]
    unique: list[Path] = []
    for path in candidates:
        if not any(same_path(path, prior) for prior in unique):
            unique.append(path)
    return unique


def parse_home_arg(arguments: str | Iterable[str]) -> str | None:
    if isinstance(arguments, str):
        values = re.findall(r'(?:--home(?:=|\s+))(?:"([^"]+)"|([^\s"]+))', arguments)
        if len(values) > 1:
            raise SetupError("profile-ambiguous", "Syncthing 启动参数包含多个配置目录，未修改。")
        return (values[0][0] or values[0][1]) if values else None
    args = list(arguments)
    homes: list[str] = []
    for index, item in enumerate(args):
        if item.startswith("--home="):
            homes.append(item.split("=", 1)[1])
        if item == "--home" and index + 1 < len(args):
            homes.append(args[index + 1])
    if len(homes) > 1:
        raise SetupError("profile-ambiguous", "Syncthing 启动参数包含多个配置目录，未修改。")
    return homes[0] if homes else None


def discover_running() -> list[StartupEntry]:
    entries: list[StartupEntry] = []
    system = platform.system().lower()
    if system == "windows":
        powershell = shutil.which("powershell.exe") or shutil.which("pwsh")
        if not powershell:
            raise SetupError("process-query-unavailable", "无法查询 Windows 运行进程；为避免误判为空，停止相关配置。")
        script = (
            "Get-CimInstance Win32_Process -Filter \"name='syncthing.exe'\" "
            "| Select-Object ExecutablePath,CommandLine | ConvertTo-Json -Compress"
        )
        result = run([powershell, "-NoProfile", "-NonInteractive", "-Command", script])
        if result.returncode != 0 or result.stderr.strip():
            raise SetupError("process-query-failed", "无法查询 Windows Syncthing 运行进程；停止相关配置。")
        if result.returncode == 0 and result.stdout.strip():
            try:
                rows = json.loads(result.stdout)
                if isinstance(rows, dict):
                    rows = [rows]
                for row in rows:
                    command = row.get("CommandLine") or ""
                    exe = row.get("ExecutablePath") or "syncthing.exe"
                    raw = command.strip()
                    if raw.startswith('"'):
                        closing_quote = raw.find('"', 1)
                        if closing_quote < 0:
                            raise SetupError("process-query-failed", "无法安全识别当前 Syncthing 进程参数。")
                        image = raw[1:closing_quote]
                        raw_arguments = raw[closing_quote + 1 :].strip()
                    else:
                        image = exe
                        if raw[: len(exe)].casefold() != exe.casefold():
                            raise SetupError("process-query-failed", "无法安全识别当前 Syncthing 进程路径。")
                        raw_arguments = raw[len(exe) :].strip()
                    if not same_path(image, exe):
                        raise SetupError("process-query-failed", "进程命令与 Syncthing 可执行路径不一致。")
                    entries.append(
                        StartupEntry("process", "running", exe, raw_arguments, parse_home_arg(raw_arguments))
                    )
            except (ValueError, TypeError):
                raise SetupError("process-query-failed", "无法安全识别当前 Syncthing 进程。")
    else:
        ps = shutil.which("ps")
        if not ps:
            raise SetupError("process-query-unavailable", "找不到 ps，无法确认 Syncthing 进程状态；停止相关配置。")
        result = run([ps, "-axo", "pid=,command="])
        if result.returncode != 0 or result.stderr.strip():
            raise SetupError("process-query-failed", "无法查询 Syncthing 运行进程；停止相关配置。")
        for line in result.stdout.splitlines():
            if "syncthing" not in line.lower() or "setup_syncthing.py" in line:
                continue
            try:
                process_fields = shlex.split(line.strip())
            except ValueError as exc:
                raise SetupError("process-query-failed", "Syncthing 进程命令行无法安全解析；停止相关配置。") from exc
            if len(process_fields) < 2 or not process_fields[0].isdigit():
                raise SetupError("process-query-failed", "无法从 ps 输出安全识别 Syncthing 进程 PID 和命令。")
            argv = process_fields[1:]
            if not argv:
                raise SetupError("process-query-failed", "Syncthing 进程命令行缺少可执行文件；停止相关配置。")
            entries.append(
                StartupEntry("process", "running", argv[0], shlex.join(argv[1:]), parse_home_arg(argv[1:]))
            )
    return entries


def parse_schtasks_csv(output: str) -> list[tuple[str, list[str]]]:
    rows = list(csv.reader(io.StringIO(output)))
    if not rows:
        raise SetupError("startup-query-failed", "Windows Task Scheduler 返回了空任务清单。")
    headers = [value.strip().casefold().replace(" ", "") for value in rows[0]]
    task_index = next(
        (index for index, value in enumerate(headers) if value in {"taskname", "任务名", "任务名称"}),
        None,
    )
    if task_index is None:
        raise SetupError("startup-query-failed", "无法在 Windows 任务清单中识别任务名称列。")
    result: list[tuple[str, list[str]]] = []
    for row in rows[1:]:
        if task_index >= len(row):
            continue
        task_name = row[task_index].strip()
        if task_name:
            result.append((task_name, row))
    return result


def _xml_local(element: ET.Element, name: str) -> ET.Element | None:
    return next((child for child in list(element) if isinstance(child.tag, str) and child.tag.rsplit("}", 1)[-1] == name), None)


def _xml_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1] if isinstance(element.tag, str) else ""


def _xml_text(element: ET.Element, name: str, default: str = "") -> str:
    child = _xml_local(element, name)
    return child.text.strip() if child is not None and child.text else default


def _find_home(executable: str, arguments: str) -> str | None:
    return parse_home_arg(arguments) or None


def current_windows_user_ids() -> set[str]:
    whoami = shutil.which("whoami.exe") or shutil.which("whoami")
    if not whoami:
        raise SetupError("startup-principal-unverified", "无法读取当前 Windows 用户身份，不能复用登录任务。")
    result = run([whoami, "/user", "/fo", "csv", "/nh"], timeout=10)
    if result.returncode != 0 or result.stderr.strip():
        raise SetupError("startup-principal-unverified", "无法验证当前 Windows 用户 SID，不能复用登录任务。")
    rows = list(csv.reader(io.StringIO(result.stdout)))
    if len(rows) != 1 or len(rows[0]) < 2 or not rows[0][0].strip() or not rows[0][1].strip():
        raise SetupError("startup-principal-unverified", "whoami 未返回可识别的当前用户和 SID。")
    return {value.strip().casefold() for value in rows[0][:2] if value.strip()}


def validate_syncthing_environment(values: dict[str, str]) -> None:
    """Reject inherited settings that could redirect the profile or override persisted pause state."""
    for key in ("STHOMEDIR", "STCONFDIR", "STDATADIR"):
        if values.get(key, "").strip():
            raise SetupError(
                "unsafe-environment-override",
                f"Syncthing 环境变量 {key} 会改变配置或数据目录；未启动或改写启动项。",
            )
    gui_address = values.get("STGUIADDRESS")
    if gui_address is not None and gui_address.strip() != LOCAL_GUI_ADDRESS:
        raise SetupError(
            "unsafe-environment-override",
            "Syncthing 环境变量 STGUIADDRESS 与本机 GUI 地址冲突；未启动或改写启动项。",
        )
    for key in ("STUNPAUSED", "STPAUSED"):
        value = values.get(key)
        if value is None:
            continue
        normalized = value.strip().casefold()
        if normalized:
            raise SetupError(
                "unsafe-environment-override",
                f"Syncthing 环境变量 {key} 会覆盖配置中保存的同步暂停状态；未启动或改写启动项。",
            )


def _relevant_environment(source: dict[str, str]) -> dict[str, str]:
    return {key: str(source[key]) for key in SYNCTHING_ENVIRONMENT_KEYS if key in source}


def _windows_registry_environment() -> list[dict[str, str]]:
    try:
        import winreg
    except ImportError:
        # Allows cross-platform unit tests to simulate the Windows branch.
        return []
    locations = (
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        (winreg.HKEY_CURRENT_USER, r"Environment"),
    )
    snapshots: list[dict[str, str]] = []
    for hive, subkey in locations:
        values: dict[str, str] = {}
        try:
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key_handle:
                index = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key_handle, index)
                    except OSError as exc:
                        if getattr(exc, "winerror", None) == 259:
                            break
                        raise SetupError(
                            "environment-query-failed",
                            "无法完整枚举 Windows Syncthing 环境变量。",
                        ) from exc
                    index += 1
                    if name.upper() in SYNCTHING_ENVIRONMENT_KEYS:
                        if not isinstance(value, str):
                            raise SetupError(
                                "environment-query-failed",
                                f"Windows 注册表中的 {name} 格式无法安全验证。",
                            )
                        values[name.upper()] = value
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise SetupError("environment-query-failed", "无法只读检查 Windows Syncthing 环境变量。") from exc
        snapshots.append(values)
    return snapshots


def _systemd_manager_environment(entries: list[StartupEntry]) -> list[dict[str, str]]:
    systemctl = shutil.which("systemctl")
    if not systemctl:
        if any(entry.kind == "systemd-user" for entry in entries):
            raise SetupError("environment-query-failed", "已有 systemd 服务，但无法读取其用户环境。")
        return []
    result = run([systemctl, "--user", "show-environment"], timeout=10)
    if result.returncode != 0 or result.stderr.strip():
        if any(entry.kind == "systemd-user" for entry in entries):
            raise SetupError("environment-query-failed", "无法验证 systemd 用户服务的有效环境变量。")
        return []
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator and key in SYNCTHING_ENVIRONMENT_KEYS:
            values[key] = value
    return [values]


def assert_safe_syncthing_environment(entries: list[StartupEntry]) -> None:
    snapshots = [_relevant_environment(dict(os.environ))]
    system = platform.system().lower()
    if system == "windows":
        snapshots.extend(_windows_registry_environment())
    elif system == "darwin":
        launchctl = shutil.which("launchctl")
        if not launchctl:
            raise SetupError("environment-query-failed", "无法检查 macOS 登录启动环境。")
        values: dict[str, str] = {}
        for key in SYNCTHING_ENVIRONMENT_KEYS:
            result = run([launchctl, "getenv", key], timeout=10)
            if result.returncode != 0 or result.stderr.strip():
                raise SetupError("environment-query-failed", f"无法读取 launchd 环境变量 {key}。")
            if result.stdout.rstrip("\r\n"):
                values[key] = result.stdout.rstrip("\r\n")
        snapshots.append(values)
    elif system == "linux":
        snapshots.extend(_systemd_manager_environment(entries))

    for entry in entries:
        if entry.environment is not None:
            snapshots.append(_relevant_environment(entry.environment))
    for values in snapshots:
        validate_syncthing_environment(values)


def _systemd_service_environment(content: str, name: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in content.splitlines():
        match = re.match(r"^\s*Environment\s*=\s*(.*?)\s*$", line)
        if match:
            try:
                assignments = shlex.split(match.group(1))
            except ValueError as exc:
                raise SetupError("startup-entry-invalid", f"systemd 环境变量无法解析：{name}") from exc
            for assignment in assignments:
                key, separator, value = assignment.partition("=")
                if separator and key in SYNCTHING_ENVIRONMENT_KEYS:
                    values[key] = value
        if re.match(r"^\s*EnvironmentFile\s*=", line):
            raise SetupError(
                "startup-environment-ambiguous",
                f"systemd 服务引用了无法安全展开的 EnvironmentFile：{name}；未修改。",
            )
    return values


def _systemd_exec_start(content: str, name: str) -> str:
    directives = re.findall(r"(?m)^\s*(Exec[A-Za-z]*)\s*=\s*(.*?)\s*$", content)
    commands = [value for key, value in directives if key == "ExecStart"]
    if len(directives) != 1 or len(commands) != 1 or not commands[0]:
        raise SetupError("startup-entry-invalid", f"systemd 服务的 ExecStart 缺失或不唯一：{name}")
    return commands[0]


def _launch_agent_command(data: dict[str, Any], name: str) -> tuple[str, str]:
    argv = data.get("ProgramArguments")
    program = data.get("Program")
    if program is not None and (not isinstance(program, str) or not program.strip()):
        raise SetupError("startup-entry-invalid", f"LaunchAgent 的 Program 无法验证：{name}")
    if argv is not None:
        if not isinstance(argv, list) or not argv or any(not isinstance(value, str) for value in argv):
            raise SetupError("startup-entry-invalid", f"LaunchAgent 的 ProgramArguments 无法验证：{name}")
        if not argv[0].strip():
            raise SetupError("startup-entry-invalid", f"LaunchAgent 缺少可识别的启动程序：{name}")
        if program is not None and not same_path(program, argv[0]):
            raise SetupError("startup-entry-invalid", f"LaunchAgent 的 Program 与 ProgramArguments 不一致：{name}")
        executable = argv[0]
        arguments = shlex.join(argv[1:])
    elif program is not None:
        executable = program
        arguments = ""
    else:
        raise SetupError("startup-entry-invalid", f"LaunchAgent 缺少可识别的启动命令：{name}")
    return executable, arguments


def discover_startup_entries() -> list[StartupEntry]:
    system = platform.system().lower()
    entries: list[StartupEntry] = []
    if system == "windows":
        schtasks = shutil.which("schtasks.exe")
        if not schtasks:
            raise SetupError("startup-query-failed", "找不到 Windows Task Scheduler 命令，无法确认已有启动项。")
        listing = run([schtasks, "/Query", "/FO", "CSV", "/V"], timeout=45)
        if listing.returncode != 0:
            raise SetupError("startup-query-failed", "无法读取当前用户可见的 Windows 登录任务。")
        for task_name, row in parse_schtasks_csv(listing.stdout):
            combined = " ".join(row)
            if "syncthing" not in combined.lower():
                continue
            detail = run([schtasks, "/Query", "/TN", task_name, "/XML"], timeout=20)
            if detail.returncode != 0:
                raise SetupError("startup-entry-unreadable", f"无法安全检查 Syncthing 启动任务：{task_name}")
            task_xml = detail.stdout.lstrip("\ufeff")
            task_xml = re.sub(r"^\s*<\?xml[^?]*\?>", "", task_xml, count=1, flags=re.IGNORECASE)
            try:
                root = ET.fromstring(task_xml)
            except (ET.ParseError, ValueError) as exc:
                raise SetupError("startup-entry-invalid", f"Syncthing 启动任务 XML 无法解析：{task_name}") from exc
            action_nodes = [node for node in root.iter() if _xml_name(node) == "Actions"]
            actions = list(action_nodes[0]) if len(action_nodes) == 1 else []
            if len(action_nodes) != 1 or len(actions) != 1 or _xml_name(actions[0]) != "Exec":
                raise SetupError(
                    "startup-action-ambiguous",
                    f"Syncthing 登录任务包含缺失、多个或无法解释的动作：{task_name}",
                )
            exec_node = actions[0]
            exe = _xml_text(exec_node, "Command")
            args = _xml_text(exec_node, "Arguments")
            trigger_nodes = [node for node in root.iter() if _xml_name(node) == "Triggers"]
            triggers = list(trigger_nodes[0]) if len(trigger_nodes) == 1 else []
            if (
                len(trigger_nodes) != 1
                or len(triggers) != 1
                or _xml_name(triggers[0]) != "LogonTrigger"
                or _xml_text(triggers[0], "Enabled", "true").lower() != "true"
            ):
                raise SetupError("startup-trigger-conflict", f"Syncthing 任务不是唯一的启用登录触发器：{task_name}")
            principals = [node for node in root.iter() if _xml_name(node) == "Principal"]
            if len(principals) != 1:
                raise SetupError("startup-principal-conflict", f"Syncthing 任务运行用户不唯一：{task_name}")
            principal = principals[0]
            user_id = _xml_text(principal, "UserId").casefold()
            current_user_ids = current_windows_user_ids()
            if (
                not user_id
                or user_id not in current_user_ids
                or _xml_text(principal, "LogonType").casefold() != "interactivetoken"
                or _xml_text(principal, "RunLevel", "LeastPrivilege").casefold() != "leastprivilege"
            ):
                raise SetupError("startup-principal-conflict", f"Syncthing 任务不属于当前用户的最低权限交互登录：{task_name}")
            trigger_user = _xml_text(triggers[0], "UserId").casefold()
            if trigger_user and trigger_user not in current_user_ids:
                raise SetupError("startup-principal-conflict", f"Syncthing 登录触发器指定了其他用户：{task_name}")
            settings = next((node for node in root.iter() if _xml_name(node) == "Settings"), None)
            enabled_text = _xml_text(settings, "Enabled", "true").lower() if settings is not None else "true"
            entries.append(
                StartupEntry("windows-task", task_name, exe, args, _find_home(exe, args), enabled_text != "false")
            )
        startup_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming")) / "Microsoft/Windows/Start Menu/Programs/Startup"
        if startup_dir.exists() and any("syncthing" in item.name.lower() for item in startup_dir.iterdir()):
            raise SetupError("startup-entry-ambiguous", "Windows 启动文件夹存在 Syncthing 快捷方式，无法验证其目标。")
    elif system == "darwin":
        agent_dir = Path.home() / "Library/LaunchAgents"
        if agent_dir.exists():
            for path in agent_dir.glob("*.plist"):
                try:
                    data = plistlib.loads(path.read_bytes())
                except (OSError, plistlib.InvalidFileException):
                    if "syncthing" in path.name.lower():
                        raise SetupError("startup-entry-invalid", f"LaunchAgent 无法解析：{path.name}")
                    continue
                if not isinstance(data, dict):
                    if "syncthing" in path.name.lower():
                        raise SetupError("startup-entry-invalid", f"LaunchAgent 结构无法识别：{path.name}")
                    continue
                try:
                    exe, args = _launch_agent_command(data, path.name)
                except SetupError:
                    if "syncthing" in path.name.lower() or "syncthing" in repr(data).lower():
                        raise
                    continue
                if "syncthing" not in (str(exe) + " " + args + " " + path.name).lower():
                    continue
                environment = data.get("EnvironmentVariables", {})
                if not isinstance(environment, dict) or any(
                    not isinstance(value, str) for value in environment.values()
                ):
                    raise SetupError("startup-entry-invalid", f"LaunchAgent 环境变量无法验证：{path.name}")
                entries.append(
                    StartupEntry(
                        "launch-agent",
                        str(data.get("Label", path.stem)),
                        str(exe),
                        args,
                        _find_home(str(exe), args),
                        not bool(data.get("Disabled", False)),
                        str(path),
                        {str(key): value for key, value in environment.items()},
                    )
                )
    else:
        user_units = Path.home() / ".config/systemd/user"
        if user_units.exists():
            for path in user_units.rglob("*.service"):
                try:
                    content = path.read_text(encoding="utf-8")
                except OSError:
                    continue
                if "syncthing" not in (content + path.name).lower():
                    continue
                command = _systemd_exec_start(content, path.name)
                try:
                    argv = shlex.split(command)
                except ValueError as exc:
                    raise SetupError("startup-entry-invalid", f"systemd 用户服务参数无法解析：{path.name}") from exc
                environment = _systemd_service_environment(content, path.name)
                entries.append(
                    StartupEntry(
                        "systemd-user",
                        path.name,
                        argv[0] if argv else "",
                        shlex.join(argv[1:]),
                        parse_home_arg(argv[1:]),
                        True,
                        str(path),
                        environment,
                    )
                )
        auto_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "autostart"
        if auto_dir.exists():
            for path in auto_dir.glob("*.desktop"):
                try:
                    content = path.read_text(encoding="utf-8")
                except OSError:
                    continue
                if "syncthing" not in (content + path.name).lower():
                    continue
                match = re.search(r"(?m)^Exec=(.+)$", content)
                if not match:
                    raise SetupError("startup-entry-invalid", f"XDG 自启动文件无法识别命令：{path.name}")
                try:
                    argv = shlex.split(match.group(1).strip().replace("%%", "%"))
                except ValueError as exc:
                    raise SetupError("startup-entry-invalid", f"XDG 自启动参数无法解析：{path.name}") from exc
                hidden = re.search(r"(?mi)^Hidden\s*=\s*(true|1)\s*$", content)
                entries.append(
                    StartupEntry(
                        "xdg-autostart",
                        path.name,
                        argv[0] if argv else "",
                        shlex.join(argv[1:]),
                        parse_home_arg(argv[1:]),
                        not bool(hidden),
                        str(path),
                    )
                )
        systemctl = shutil.which("systemctl")
        manager_available = False
        if systemctl:
            manager_probe = run([systemctl, "--user", "show-environment"], timeout=10)
            manager_available = manager_probe.returncode == 0 and not manager_probe.stderr.strip()
            if manager_available:
                result = run([systemctl, "--user", "list-unit-files", "--no-legend"], timeout=10)
                if result.returncode != 0 or result.stderr.strip():
                    raise SetupError("startup-query-failed", "无法完整读取 systemd 用户登录服务清单。")
            else:
                result = None
        else:
            result = None
        if manager_available and result is not None:
            for line in result.stdout.splitlines():
                unit = line.split()[0] if line.split() else ""
                if "syncthing" not in unit.lower() or unit.endswith(".wants"):
                    continue
                detail = run([systemctl, "--user", "cat", unit], timeout=10)
                if detail.returncode != 0:
                    raise SetupError("startup-entry-unreadable", f"无法安全读取 systemd 用户服务：{unit}")
                command = _systemd_exec_start(detail.stdout, unit)
                try:
                    argv = shlex.split(command)
                except ValueError as exc:
                    raise SetupError("startup-entry-invalid", f"systemd 用户服务参数无法解析：{unit}") from exc
                environment = _systemd_service_environment(detail.stdout, unit)
                enabled = run([systemctl, "--user", "is-enabled", unit], timeout=10).returncode == 0
                entries.append(
                    StartupEntry(
                        "systemd-user",
                        unit,
                        argv[0] if argv else "",
                        " ".join(argv[1:]),
                        parse_home_arg(argv[1:]),
                        enabled,
                        None,
                        environment,
                    )
                )
    unique: dict[tuple[str, str, str | None], StartupEntry] = {}
    for entry in entries:
        unique[(entry.kind, entry.name, entry.home)] = entry
    return list(unique.values())


def executable_candidates(startup: list[StartupEntry]) -> list[Path]:
    candidates: list[Path] = []
    for entry in startup:
        if entry.executable:
            candidates.append(Path(entry.executable).expanduser())
    located = shutil.which("syncthing") or shutil.which("syncthing.exe")
    if located:
        candidates.append(Path(located))
    home = Path.home()
    if platform.system().lower() == "windows":
        program_dirs = [Path(value) for value in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")) if value]
        candidates.extend(
            [
                Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local")) / "Programs/Syncthing/syncthing.exe",
                Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local")) / "Syncthing/syncthing.exe",
                *(directory / "Syncthing/syncthing.exe" for directory in program_dirs),
            ]
        )
    else:
        candidates.extend(
            [
                home / ".local/bin/syncthing",
                Path("/usr/bin/syncthing"),
                Path("/usr/local/bin/syncthing"),
                Path("/opt/homebrew/bin/syncthing"),
                Path("/Applications/Syncthing.app/Contents/MacOS/syncthing"),
            ]
        )
    unique: list[Path] = []
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if resolved.exists() and resolved.is_file() and not any(same_path(resolved, item) for item in unique):
            unique.append(resolved)
    return unique


def inspect_xml(path: Path) -> ET.Element:
    try:
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
        tree = ET.parse(path, parser=parser)
        root = tree.getroot()
    except (OSError, ET.ParseError) as exc:
        raise SetupError("syncthing-config-invalid", "Syncthing config.xml 无法解析，未修改。") from exc
    if _xml_name(root) != "configuration":
        raise SetupError("syncthing-config-invalid", "Syncthing config.xml 根节点不匹配，未修改。")
    return root


def device_and_folder_state(root: ET.Element, vault: Path) -> dict[str, Any]:
    devices = [item for item in list(root) if _xml_name(item) == "device"]
    if len(devices) != 1 or not devices[0].get("id"):
        raise SetupError("remote-device-conflict", "无法无歧义识别唯一的本机设备；未改动 Syncthing。")
    local_id = devices[0].get("id", "")
    folders = [item for item in list(root) if _xml_name(item) == "folder"]
    for folder in folders:
        paused_nodes = [node for node in list(folder) if _xml_name(node) == "paused"]
        if len(paused_nodes) > 1 or (folder.get("paused") is not None and paused_nodes):
            raise SetupError("folder-paused-ambiguous", "Syncthing 文件夹暂停状态有重复或冲突字段，未修改配置。")
        folder_path = folder.get("path", "").strip()
        expanded_path = Path(os.path.expandvars(os.path.expanduser(folder_path))) if folder_path else Path()
        if not folder_path or not expanded_path.is_absolute():
            raise SetupError("folder-path-ambiguous", "Syncthing 文件夹路径缺失或不是绝对路径，未修改配置。")
    matching = [folder for folder in folders if folder.get("path") and same_path(folder.get("path", ""), vault)]
    if len(matching) > 1:
        raise SetupError("vault-folder-conflict", "Syncthing 中有多个文件夹指向该 Vault；未改动配置。")
    if any(
        device.get("id") != local_id
        for folder in folders
        for device in list(folder)
        if _xml_name(device) == "device"
    ):
        raise SetupError("remote-device-conflict", "Syncthing 文件夹已关联远端设备；未改动配置。")
    active_other = [
        folder.get("id", "(无 ID)")
        for folder in folders
        if not same_path(folder.get("path", ""), vault)
        and _xml_text(folder, "paused", folder.get("paused", "false")).lower() != "true"
    ]
    if active_other:
        raise SetupError("active-folder-conflict", "Syncthing 中存在目标 Vault 之外的活动文件夹；未改动配置。")
    return {
        "localDeviceId": local_id,
        "remoteDeviceCount": max(0, len(devices) - 1),
        "folders": folders,
        "targetFolder": matching[0] if matching else None,
        "activeOtherFolderIds": active_other,
    }


def set_child_text(parent: ET.Element, name: str, value: str) -> bool:
    child = _xml_local(parent, name)
    if child is None:
        child = ET.SubElement(parent, name)
        child.text = value
        return True
    if (child.text or "").strip() != value:
        child.text = value
        return True
    return False


def folder_paused(folder: ET.Element) -> bool:
    return _xml_text(folder, "paused", folder.get("paused", "false")).lower() == "true"


def patch_config(root: ET.Element, vault: Path, *, fresh: bool = False) -> dict[str, Any]:
    fresh_removed = False
    if fresh:
        devices = [item for item in list(root) if _xml_name(item) == "device"]
        if len(devices) != 1 or not devices[0].get("id"):
            raise SetupError("local-device-unresolved", "新 Syncthing 配置中无法识别本机设备 ID。")
        # syncthing generate may create its stock Sync folder. This isolated,
        # newly generated profile has no user folders to preserve.
        for folder in [item for item in list(root) if _xml_name(item) == "folder"]:
            root.remove(folder)
            fresh_removed = True
    state = device_and_folder_state(root, vault)
    changed = fresh_removed

    options_nodes = [node for node in list(root) if _xml_name(node) == "options"]
    gui_nodes = [node for node in list(root) if _xml_name(node) == "gui"]
    if len(options_nodes) > 1 or len(gui_nodes) > 1:
        raise SetupError("config-structure-ambiguous", "Syncthing 配置有重复的 options 或 GUI 节点，未修改。")
    options = options_nodes[0] if options_nodes else None
    if options is None:
        options = ET.SubElement(root, "options")
        changed = True
    for field in NETWORK_FALSE_FIELDS:
        if sum(1 for node in list(options) if _xml_name(node) == field) > 1:
            raise SetupError("network-option-ambiguous", f"Syncthing 网络选项 {field} 重复，未修改。")
        changed = set_child_text(options, field, "false") or changed

    listen_nodes = [node for node in list(options) if _xml_name(node) == "listenAddress"]
    current_listeners = [node.text.strip() for node in listen_nodes if node.text and node.text.strip()]
    if current_listeners != ["tcp://127.0.0.1:22000"]:
        insert_at = min((list(options).index(node) for node in listen_nodes), default=len(options))
        for node in listen_nodes:
            options.remove(node)
        replacement = ET.Element("listenAddress")
        replacement.text = "tcp://127.0.0.1:22000"
        options.insert(insert_at, replacement)
        changed = True

    gui = gui_nodes[0] if gui_nodes else None
    if gui is None:
        gui = ET.SubElement(root, "gui")
        changed = True
    gui_addresses = [node for node in list(gui) if _xml_name(node) == "address"]
    if len(gui_addresses) > 1:
        raise SetupError("gui-address-ambiguous", "Syncthing GUI 有重复的 address 字段，未修改配置。")
    changed = set_child_text(gui, "address", "127.0.0.1:8384") or changed

    target = state["targetFolder"]
    if any(
        folder.get("id") == FOLDER_ID and not same_path(folder.get("path", ""), vault)
        for folder in state["folders"]
    ):
        raise SetupError("vault-folder-id-conflict", "目标文件夹 ID 已指向其他路径；未改动配置。")
    if target is None:
        if any(folder.get("id") == FOLDER_ID for folder in state["folders"]):
            raise SetupError("vault-folder-id-conflict", "第二大脑文件夹 ID 已被其他路径占用；未改动配置。")
        target = ET.Element(
            "folder",
            {
                "id": FOLDER_ID,
                "label": FOLDER_LABEL,
                "path": str(vault),
                "type": "sendreceive",
            },
        )
        ET.SubElement(target, "device", {"id": state["localDeviceId"]})
        ET.SubElement(target, "paused").text = "true"
        root.insert(0, target)
        changed = True
    else:
        if target.get("paused") is not None:
            if target.get("paused") != "true":
                target.set("paused", "true")
                changed = True
        else:
            changed = set_child_text(target, "paused", "true") or changed
        refs = [node for node in list(target) if _xml_name(node) == "device"]
        if not refs:
            ET.SubElement(target, "device", {"id": state["localDeviceId"]})
            changed = True

    return {
        "changed": changed,
        "folderId": target.get("id"),
        "folderPath": target.get("path"),
        "folderPaused": folder_paused(target),
        "localDeviceId": state["localDeviceId"],
        "remoteDeviceCount": state["remoteDeviceCount"],
        "network": {
            "listenAddress": ["tcp://127.0.0.1:22000"],
            "globalAnnounceEnabled": False,
            "localAnnounceEnabled": False,
            "relaysEnabled": False,
            "natEnabled": False,
        },
    }


def serialize_config(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def merge_ignore_text(original: str) -> tuple[str, list[str]]:
    lines = original.splitlines()
    starts = [i for i, line in enumerate(lines) if line.strip() == IGNORE_START]
    ends = [i for i, line in enumerate(lines) if line.strip() == IGNORE_END]
    if len(starts) != len(ends) or len(starts) > 1 or (starts and starts[0] >= ends[0]):
        raise SetupError("stignore-markers-conflict", ".stignore 管理标记残缺、重复或顺序错误，未修改。")
    present = {line.strip() for line in lines}
    missing = [rule for rule in IGNORE_RULES if rule not in present]
    if not missing:
        return original, []

    newline = "\r\n" if "\r\n" in original else "\n"
    if starts:
        end = ends[0]
        updated_lines = lines[:end] + missing + lines[end:]
        return newline.join(updated_lines) + (newline if original.endswith(("\n", "\r")) else ""), missing
    suffix = newline.join([IGNORE_START, *missing, IGNORE_END])
    if original:
        prefix = original if original.endswith(("\n", "\r")) else original + newline
        return prefix + suffix + newline, missing
    return suffix + newline, missing


def app_install_dir() -> Path:
    home = Path.home()
    system = platform.system().lower()
    if system == "windows":
        root = Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local")) / "Programs/CodexLazyPack/Syncthing"
    elif system == "darwin":
        root = home / "Library/Application Support/CodexLazyPack/Syncthing"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", home / ".local/share")) / "codex-lazy-pack/syncthing"
    return root


def install_syncthing(lock: dict[str, Any], platform_id: str) -> Path:
    artifact = lock.get("artifacts", {}).get(platform_id)
    if not isinstance(artifact, dict):
        raise SetupError("artifact-unavailable", f"锁文件没有当前平台安装包：{platform_id}")
    filename = str(artifact.get("file", ""))
    expected_hash = str(artifact.get("sha256", "")).lower()
    if not filename or Path(filename).name != filename or "/" in filename or "\\" in filename:
        raise SetupError("artifact-lock-invalid", "Syncthing 安装包文件名不是安全的单一文件名。")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise SetupError("artifact-lock-invalid", "Syncthing SHA-256 锁值无效。")
    version = str(lock["version"])
    dest_dir = app_install_dir() / version
    executable_name = "syncthing.exe" if platform.system().lower() == "windows" else "syncthing"
    executable = dest_dir / executable_name
    if executable.exists():
        return executable
    if dest_dir.exists():
        raise SetupError("install-path-conflict", "Syncthing 安装目标目录已存在但缺少可执行程序，未覆盖。")

    url = f"https://github.com/syncthing/syncthing/releases/download/v{version}/{filename}"
    parent = dest_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".syncthing-stage-", dir=parent) as stage_name:
        stage = Path(stage_name)
        archive = stage / filename
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=60) as response, archive.open("wb") as output:
                final_host = urlparse(response.geturl()).hostname or ""
                if not response.geturl().startswith("https://") or not (
                    final_host == "github.com" or final_host.endswith("githubusercontent.com")
                ):
                    raise SetupError("download-redirect-invalid", "下载重定向目标不在官方 HTTPS 域名范围内。")
                shutil.copyfileobj(response, output)
        except SetupError:
            raise
        except Exception as exc:
            raise SetupError("download-failed", "无法下载锁定的 Syncthing 官方发布包。") from exc

        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != expected_hash:
            raise SetupError("checksum-mismatch", "Syncthing 安装包校验值不匹配；未安装。")

        extracted = stage / executable_name
        if filename.endswith(".zip"):
            try:
                with zipfile.ZipFile(archive) as bundle:
                    matches = [name for name in bundle.namelist() if Path(name).name == executable_name]
                    if len(matches) != 1:
                        raise SetupError("archive-invalid", "Syncthing 压缩包中的可执行文件不唯一。")
                    info = bundle.getinfo(matches[0])
                    if (info.external_attr >> 16) & 0o170000 == 0o120000:
                        raise SetupError("archive-invalid", "拒绝从压缩包提取符号链接。")
                    with bundle.open(info) as source, extracted.open("wb") as output:
                        shutil.copyfileobj(source, output)
            except (OSError, zipfile.BadZipFile) as exc:
                raise SetupError("archive-invalid", "Syncthing ZIP 文件无法安全读取。") from exc
        else:
            try:
                with tarfile.open(archive, "r:gz") as bundle:
                    matches = [item for item in bundle.getmembers() if item.isfile() and Path(item.name).name == executable_name]
                    if len(matches) != 1:
                        raise SetupError("archive-invalid", "Syncthing 压缩包中的可执行文件不唯一。")
                    source = bundle.extractfile(matches[0])
                    if source is None:
                        raise SetupError("archive-invalid", "无法读取 Syncthing 可执行文件。")
                    with source, extracted.open("wb") as output:
                        shutil.copyfileobj(source, output)
            except (OSError, tarfile.TarError) as exc:
                raise SetupError("archive-invalid", "Syncthing TAR 文件无法安全读取。") from exc

        if platform.system().lower() != "windows":
            extracted.chmod(0o755)
        stage_final = stage / "package"
        stage_final.mkdir()
        shutil.move(str(extracted), str(stage_final / executable_name))
        dest_dir.parent.mkdir(parents=True, exist_ok=True)
        os.replace(stage_final, dest_dir)
    if not executable.exists():
        raise SetupError("install-failed", "安装结束后未找到 Syncthing 可执行文件。")
    return executable


def syncthing_version(executable: Path) -> tuple[str, tuple[int, int, int]]:
    result = run([str(executable), "--version"], timeout=15)
    if result.returncode != 0:
        raise SetupError("version-check-failed", "无法读取 Syncthing 版本。")
    text = (result.stdout + result.stderr).strip()
    match = re.search(r"v(\d+)\.(\d+)\.(\d+)", text)
    if not match:
        raise SetupError("version-unrecognized", "Syncthing 版本输出无法识别。")
    version_tuple = tuple(map(int, match.groups()))
    if version_tuple[0] != 2 or version_tuple < SUPPORTED_MIN_VERSION:
        raise SetupError("version-incompatible", "现有 Syncthing 版本不兼容；不会自动升级或降级。")
    return text.splitlines()[0], version_tuple


def verify_local_device_identity(executable: Path, profile: Path, configured_id: str) -> str:
    result = run([str(executable), "device-id", f"--home={profile}"], timeout=20)
    if result.returncode != 0:
        raise SetupError(
            "local-device-identity-unverified",
            "无法从当前 Syncthing profile 的证书只读验证本机设备身份；未修改配置。",
        )
    output_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(output_lines) != 1 or not re.fullmatch(r"[A-Za-z0-9-]+", output_lines[0]):
        raise SetupError(
            "local-device-identity-unverified",
            "Syncthing 未返回唯一、可识别的 profile 设备 ID；未修改配置。",
        )
    certificate_id = re.sub(r"[-\s]", "", output_lines[0]).upper()
    config_id = re.sub(r"[-\s]", "", configured_id).upper()
    if len(certificate_id) < 32 or certificate_id != config_id:
        raise SetupError(
            "local-device-identity-mismatch",
            "Syncthing config.xml 中唯一设备 ID 与本机证书身份不一致；未修改或启动 Syncthing。",
        )
    return output_lines[0]


def profile_dir_for(startup: list[StartupEntry]) -> Path:
    defaults = default_profile_dirs()
    if any(path.is_symlink() for path in defaults):
        raise SetupError("profile-symlink", "标准 Syncthing 配置目录候选中存在符号链接，未修改。")
    homes = {normalize_path(entry.home) for entry in startup if entry.home}
    if len(homes) > 1:
        raise SetupError("profile-ambiguous", "发现多个 Syncthing 配置目录，未修改。")
    if homes:
        raw_home = next(entry.home for entry in startup if entry.home)
        expanded_home = Path(os.path.expandvars(os.path.expanduser(raw_home)))
        if not expanded_home.is_absolute():
            raise SetupError("profile-ambiguous", "Syncthing 启动项使用相对配置目录，无法安全解析。")
        if expanded_home.is_symlink():
            raise SetupError("profile-symlink", "Syncthing 配置目录是符号链接，未修改。")
        selected = expanded_home.resolve()
        if selected.exists() and not selected.is_dir():
            raise SetupError("profile-conflict", "Syncthing 配置路径不是目录，未修改。")
        if selected.exists() and not (selected / "config.xml").exists():
            if any(selected.iterdir()):
                raise SetupError("profile-partial", "启动项指向不完整的 Syncthing 配置目录，未覆盖。")
            raise SetupError("profile-partial", "启动项指向空的 Syncthing 配置目录；需先确认其用途。")
        other_profiles = [
            path
            for path in defaults
            if not same_path(path, selected)
            and ((path / "config.xml").exists() or (path.exists() and any(path.iterdir())))
        ]
        if other_profiles:
            raise SetupError("profile-ambiguous", "启动项指向的配置目录之外还存在 Syncthing profile，未修改。")
        return selected
    existing = [path for path in defaults if (path / "config.xml").exists()]
    if len(existing) > 1:
        raise SetupError("profile-ambiguous", "发现多个 Syncthing 配置目录，未修改。")
    if existing:
        return existing[0].resolve()
    partial = [path for path in defaults if path.exists() and any(path.iterdir())]
    if partial:
        raise SetupError("profile-partial", "发现不完整的 Syncthing 配置目录，未覆盖。")
    return defaults[0].resolve()


def startup_for_profile(entries: list[StartupEntry], profile: Path) -> StartupEntry | None:
    syncthing_entries = [
        entry
        for entry in entries
        if "syncthing" in (entry.executable + " " + entry.arguments + " " + entry.name).lower()
        or entry.kind == "process"
    ]
    matching = [
        entry
        for entry in syncthing_entries
        if (Path(entry.home).expanduser().resolve() if entry.home else default_profile_dirs()[0].resolve()) == profile
    ]
    other = [entry for entry in syncthing_entries if entry not in matching]
    if other:
        raise SetupError("startup-conflict", "发现指向其他配置目录的 Syncthing 实例或启动项，未修改。")
    if len(matching) > 1 and not all(entry.kind == "process" for entry in matching):
        raise SetupError("startup-duplicate", "发现多个 Syncthing 登录启动项，未修改。")
    return matching[0] if matching else None


def linux_headless_or_ssh() -> bool:
    if platform.system().lower() != "linux":
        return False
    return bool(
        os.environ.get("SSH_CONNECTION")
        or os.environ.get("SSH_CLIENT")
        or not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    )


def process_targets_profile(entry: StartupEntry, profile: Path) -> bool:
    if entry.kind != "process":
        return False
    if entry.home:
        return same_path(entry.home, profile)
    return same_path(default_profile_dirs()[0], profile)


def desired_arguments(profile: Path) -> list[str]:
    result = [
        "--home",
        str(profile),
        "serve",
        f"--gui-address={LOCAL_GUI_ADDRESS}",
        "--no-browser",
        "--no-upgrade",
    ]
    if platform.system().lower() == "windows":
        result.append("--no-console")
    return result


def startup_is_safe(entry: StartupEntry, profile: Path) -> bool:
    expected_executable = "syncthing.exe" if platform.system().lower() == "windows" else "syncthing"
    actual_executable = entry.executable.replace("\\", "/").rsplit("/", 1)[-1].casefold()
    if actual_executable != expected_executable:
        return False
    try:
        args = shlex.split(entry.arguments, posix=platform.system().lower() != "windows")
    except ValueError:
        return False
    if platform.system().lower() == "windows":
        args = [
            item[1:-1] if len(item) >= 2 and item[0] == item[-1] and item[0] in {'"', "'"} else item
            for item in args
        ]
    try:
        validate_syncthing_environment(entry.environment or {})
    except SetupError:
        return False
    homes: list[str] = []
    flags: set[str] = set()
    gui_addresses: list[str] = []
    paused_options: list[tuple[str, str]] = []
    index = 0
    while index < len(args):
        item = args[index]
        if item == "--home" and index + 1 < len(args):
            homes.append(args[index + 1])
            index += 2
            continue
        if item.startswith("--home="):
            homes.append(item.split("=", 1)[1])
        elif item in {"serve", "--no-browser", "--no-console", "--no-upgrade"}:
            flags.add(item)
        elif item == "--gui-address" and index + 1 < len(args):
            gui_addresses.append(args[index + 1])
            index += 1
        elif item.startswith("--gui-address="):
            gui_addresses.append(item.split("=", 1)[1])
        elif item == "--paused":
            paused_options.append(("paused", "true"))
        elif item.startswith("--paused="):
            paused_options.append(("paused", item.split("=", 1)[1].casefold()))
        elif item == "--unpaused" and index + 1 < len(args):
            paused_options.append(("unpaused", args[index + 1].casefold()))
            index += 1
        elif item.startswith("--unpaused="):
            paused_options.append(("unpaused", item.split("=", 1)[1].casefold()))
        else:
            return False
        index += 1
    if not homes and entry.home is None and same_path(default_profile_dirs()[0], profile):
        homes = [str(profile)]
    if len(homes) != 1 or "serve" not in flags or "--no-browser" not in flags or "--no-upgrade" not in flags:
        return False
    if platform.system().lower() == "windows" and "--no-console" not in flags:
        return False
    if len(gui_addresses) > 1 or any(address != LOCAL_GUI_ADDRESS for address in gui_addresses):
        return False
    if paused_options:
        return False
    if entry.kind == "process" and (
        gui_addresses != [LOCAL_GUI_ADDRESS]
        or paused_options
    ):
        # Persisted folder state, not process arguments, controls whether sync is active.
        return False
    home = entry.home or str(default_profile_dirs()[0])
    return (
        same_path(home, profile)
        and same_path(homes[0], profile)
    )


def prepare_ignore(vault: Path) -> tuple[Path, str, list[str], bool]:
    path = vault / ".stignore"
    if path.is_symlink():
        raise SetupError("stignore-symlink", ".stignore 是符号链接，未修改。")
    if path.exists():
        if not path.is_file():
            raise SetupError("stignore-unreadable", ".stignore 不是普通文件，未修改。")
        try:
            original = path.read_bytes().decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise SetupError("stignore-unreadable", ".stignore 无法按 UTF-8 安全读取，未修改。") from exc
    else:
        original = ""
    merged, added = merge_ignore_text(original)
    return path, merged, added, path.exists()


def validate_profile(root: ET.Element, vault: Path) -> dict[str, Any]:
    state = device_and_folder_state(root, vault)
    folder = state["targetFolder"]
    if folder is not None:
        state["folderId"] = folder.get("id")
        state["folderPaused"] = folder_paused(folder)
    else:
        state["folderId"] = None
        state["folderPaused"] = None
    options_nodes = [node for node in list(root) if _xml_name(node) == "options"]
    gui_nodes = [node for node in list(root) if _xml_name(node) == "gui"]
    if len(options_nodes) > 1 or len(gui_nodes) > 1:
        raise SetupError("config-structure-ambiguous", "Syncthing 配置有重复的 options 或 GUI 节点，未修改。")
    options = options_nodes[0] if options_nodes else None
    for field in NETWORK_FALSE_FIELDS:
        if options is not None and sum(1 for node in list(options) if _xml_name(node) == field) > 1:
            raise SetupError("network-option-ambiguous", f"Syncthing 网络选项 {field} 重复，未修改。")
    state["network"] = {}
    for field in NETWORK_FALSE_FIELDS:
        state["network"][field] = _xml_text(options, field, "") if options is not None else ""
    state["listenAddress"] = [
        node.text.strip()
        for node in (list(options) if options is not None else [])
        if _xml_name(node) == "listenAddress" and node.text
    ]
    gui = gui_nodes[0] if gui_nodes else None
    gui_addresses = [node for node in list(gui) if _xml_name(node) == "address"] if gui is not None else []
    if len(gui_addresses) > 1:
        raise SetupError("gui-address-ambiguous", "Syncthing GUI 有重复的 address 字段，未修改配置。")
    state["guiAddress"] = (gui_addresses[0].text or "").strip() if gui_addresses else ""
    state["compliant"] = (
        all(state["network"].get(field) == "false" for field in NETWORK_FALSE_FIELDS)
        and state["listenAddress"] == ["tcp://127.0.0.1:22000"]
        and state["guiAddress"] == "127.0.0.1:8384"
        and state["folderPaused"] is True
    )
    return state


def validate_existing_pair_profile(root: ET.Element, vault: Path, role: str, onboarding: dict[str, Any]) -> dict[str, Any]:
    """Read-only validation for a recorded pair stage; never applies first-install defaults."""
    stage = onboarding.get("status")
    expected_modes = {
        "primary": {
            "paired-paused": "sendonly",
            "seeding": "sendonly",
            "primary-promoted": "sendreceive",
            "active": "sendreceive",
        },
        "server": {
            "paired-paused": "receiveonly",
            "receiver-ready": "receiveonly",
            "seed-verified": "receiveonly",
            "server-promoted": "sendreceive",
            "active": "sendreceive",
        },
    }
    expected_type = expected_modes.get(role, {}).get(stage)
    if expected_type is None:
        raise SetupError("paired-onboarding-stage-invalid", "同步阶段没有已知的双机配置要求；不修改现有 profile。")
    own_id = onboarding.get("syncthingDeviceId")
    peer_id = onboarding.get("peerSyncthingDeviceId")
    if not isinstance(own_id, str) or not own_id.strip() or not isinstance(peer_id, str) or not peer_id.strip():
        raise SetupError("paired-device-identity-missing", "同步状态已记录配对阶段，但缺少绑定的本机/对端 Syncthing Device ID；保留现有配置，不重置。")
    own_normalized = _normalized_device_id(own_id)
    peer_normalized = _normalized_device_id(peer_id)
    if own_normalized == peer_normalized:
        raise SetupError("paired-device-identity-conflict", "同步状态把本机和对端绑定为同一设备；不修改现有配置。")

    devices = [item for item in list(root) if _xml_name(item) == "device"]
    configured_ids = [item.get("id", "").strip() for item in devices]
    normalized_ids = [_normalized_device_id(value) for value in configured_ids]
    if (len(devices) != 2 or any(not value for value in configured_ids)
            or len(set(normalized_ids)) != len(normalized_ids)
            or set(normalized_ids) != {own_normalized, peer_normalized}):
        raise SetupError("paired-device-config-conflict", "同步 profile 中的设备表与已记录的唯一双机身份不符；只读保留，不重置。")

    folders = [item for item in list(root) if _xml_name(item) == "folder"]
    matches = [item for item in folders if item.get("id") == FOLDER_ID or
               (item.get("path") and same_path(item.get("path", ""), vault))]
    if (len(matches) != 1 or matches[0].get("id") != FOLDER_ID
            or not matches[0].get("path") or not same_path(matches[0].get("path", ""), vault)):
        raise SetupError("paired-vault-folder-conflict", "同步 profile 的固定 folder ID 与本机 Vault 路径无法唯一匹配；不修改。")
    folder = matches[0]
    if folder.get("type") != expected_type:
        raise SetupError("paired-vault-folder-mode-conflict", f"同步阶段 {stage} 要求 folder 为 {expected_type}，实际模式不符；不更改同步方向。")
    paused_nodes = [node for node in list(folder) if _xml_name(node) == "paused"]
    if len(paused_nodes) > 1 or (folder.get("paused") is not None and paused_nodes):
        raise SetupError("paired-folder-paused-ambiguous", "目标 folder 的暂停配置重复或冲突；不修改。")
    members = [node.get("id", "").strip() for node in list(folder) if _xml_name(node) == "device"]
    normalized_members = [_normalized_device_id(value) for value in members]
    if (len(members) != 2 or any(not value for value in members)
            or len(set(normalized_members)) != 2
            or set(normalized_members) != {own_normalized, peer_normalized}):
        raise SetupError("paired-folder-membership-conflict", "Vault folder 成员与已记录的双机身份不符；不修改。")

    local_devices = [item for item in devices if _normalized_device_id(item.get("id", "")) == own_normalized]
    peer_devices = [item for item in devices if _normalized_device_id(item.get("id", "")) == peer_normalized]
    if len(local_devices) != 1 or len(peer_devices) != 1:
        raise SetupError("paired-device-config-conflict", "本机或对端设备记录无法唯一识别；不修改。")
    peer_paused_text = _xml_text(peer_devices[0], "paused", peer_devices[0].get("paused", "false")).strip().lower()
    if peer_paused_text not in {"true", "false"}:
        raise SetupError("paired-peer-paused-invalid", "对端暂停状态无法从 profile 核验；不修改。")
    peer_paused = peer_paused_text == "true"

    options_nodes = [node for node in list(root) if _xml_name(node) == "options"]
    gui_nodes = [node for node in list(root) if _xml_name(node) == "gui"]
    if len(options_nodes) > 1 or len(gui_nodes) > 1:
        raise SetupError("paired-config-ambiguous", "profile 含重复 options/GUI 节点；不修改。")
    options = options_nodes[0] if options_nodes else None
    if options is not None:
        for field in (*NETWORK_FALSE_FIELDS, "announceLANAddresses"):
            if sum(1 for node in list(options) if _xml_name(node) == field) > 1:
                raise SetupError("paired-config-ambiguous", f"profile 的网络字段 {field} 重复；不修改。")
    listen_addresses = [node.text.strip() for node in (list(options) if options is not None else [])
                        if _xml_name(node) == "listenAddress" and node.text and node.text.strip()]
    gui = gui_nodes[0] if gui_nodes else None
    gui_addresses = [node for node in list(gui) if _xml_name(node) == "address"] if gui is not None else []
    if len(gui_addresses) > 1:
        raise SetupError("paired-config-ambiguous", "profile 的 GUI 地址重复；不修改。")
    options_state = {
        field: _xml_text(options, field, "") if options is not None else ""
        for field in (*NETWORK_FALSE_FIELDS, "announceLANAddresses")
    }
    actual_network = {key: value.strip().lower() for key, value in options_state.items()}
    gui_address = (gui_addresses[0].text or "").strip() if gui_addresses else ""
    if (set(listen_addresses) != set(PAIRED_LISTENERS)
            or len(listen_addresses) != len(PAIRED_LISTENERS)
            or actual_network != PAIRED_NETWORK_OPTIONS
            or gui_address != LOCAL_GUI_ADDRESS):
        raise SetupError("paired-network-policy-conflict", "已配对 profile 的监听、发现、中继、NAT、浏览器或 GUI 策略与确认基线不符；不覆盖用户配置。")
    folder_paused_value = folder_paused(folder)
    if stage == "paired-paused" and (folder_paused_value is not True or peer_paused is not True):
        raise SetupError("paired-paused-state-conflict", "引导状态为 paired-paused，但 folder 或对端未保持暂停；不修改并停止后续阶段。")
    return {
        "verification": "recorded-pair-stage-static-config",
        "onboardingStatus": stage,
        "localDeviceId": own_id,
        "peerDeviceId": peer_id,
        "remoteDeviceCount": 1,
        "folderId": FOLDER_ID,
        "folderType": folder.get("type"),
        "folderPaused": folder_paused_value,
        "peerPaused": peer_paused,
        "folderPathMatches": True,
        "network": options_state,
        "listenAddress": listen_addresses,
        "guiAddress": (gui_addresses[0].text or "").strip() if gui_addresses else "",
        "role": role,
    }


def xml_bytes_from_path(path: Path, vault: Path) -> tuple[bytes, dict[str, Any]]:
    root = inspect_xml(path)
    state = patch_config(root, vault)
    return serialize_config(root), state


def snapshot_file(path: Path, label: str) -> bytes | None:
    if path.is_symlink():
        raise SetupError("target-symlink", f"{label} 是符号链接，未修改。")
    if not path.exists():
        return None
    if not path.is_file():
        raise SetupError("target-not-file", f"{label} 不是普通文件，未修改。")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise SetupError("target-unreadable", f"{label} 无法安全读取，未修改。") from exc


def durable_replace_file(source: str | Path, destination: Path) -> None:
    """Atomically replace a file and flush the directory entry before returning."""
    if platform.system().lower() == "windows":
        import ctypes

        move_file_ex = ctypes.WinDLL("kernel32", use_last_error=True).MoveFileExW
        move_file_ex.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
        move_file_ex.restype = ctypes.c_int
        flags = 0x1 | 0x8  # MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH
        if not move_file_ex(str(source), str(destination), flags):
            error = ctypes.get_last_error()
            raise OSError(error, "MoveFileExW durable replacement failed", str(destination))
        return
    os.replace(source, destination)
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        directory_fd = os.open(destination.parent, directory_flags)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        raise SetupError("target-directory-sync-failed", "原子替换后的父目录无法持久化；没有开始依赖该状态的后续操作。") from exc


def write_atomic(
    path: Path,
    data: bytes,
    mode: int = 0o600,
    *,
    expected_current: bytes | None | object = _SNAPSHOT_UNSET,
) -> None:
    if path.is_symlink():
        raise SetupError("target-symlink", f"写入目标 {path.name} 是符号链接，未修改。")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and platform.system().lower() != "windows":
        import stat
        mode = stat.S_IMODE(path.stat().st_mode)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        if platform.system().lower() != "windows":
            os.chmod(temp_name, mode)
        if expected_current is not _SNAPSHOT_UNSET and snapshot_file(path, path.name) != expected_current:
            raise SetupError("concurrent-file-change", f"{path.name} 在安装期间发生变化，未覆盖。")
        durable_replace_file(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def write_new_atomic(path: Path, data: bytes, mode: int = 0o600) -> None:
    """Atomically create a new file without replacing a racing user file."""
    if path.is_symlink():
        raise SetupError("target-symlink", f"写入目标 {path.name} 是符号链接，未修改。")
    if path.exists():
        raise SetupError("startup-name-conflict", f"启动项目标 {path.name} 已存在，未覆盖。")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        if platform.system().lower() != "windows":
            os.chmod(temp_name, mode)
        try:
            os.link(temp_name, path)
        except FileExistsError as exc:
            raise SetupError("startup-name-conflict", f"启动项目标 {path.name} 在写入期间被占用，未覆盖。") from exc
        except OSError as exc:
            raise SetupError("startup-register-failed", f"无法安全地原子创建启动项 {path.name}，未覆盖任何文件。") from exc
    finally:
        try:
            os.unlink(temp_name)
        except OSError:
            pass


def _install_staged_profile_create_only(stage: Path, profile: Path) -> None:
    """Materialize a generated profile without replacing a raced-in directory/file."""
    if stage.is_symlink() or not stage.is_dir():
        raise SetupError("profile-stage-invalid", "Syncthing 临时 profile 不存在或不是普通目录。")
    if profile.is_symlink() or profile.exists():
        raise SetupError("profile-create-conflict", "Syncthing profile 在创建期间已被占用，未覆盖。")
    try:
        profile.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise SetupError("profile-create-conflict", "Syncthing profile 在创建期间已被占用，未覆盖。") from exc
    except OSError as exc:
        raise SetupError("profile-install-failed", "无法安全创建 Syncthing profile 目录。") from exc

    try:
        for source in sorted(stage.rglob("*")):
            if source.is_symlink():
                raise SetupError("profile-stage-invalid", "Syncthing 临时 profile 含符号链接，未复制。")
            relative = source.relative_to(stage)
            destination = profile / relative
            if source.is_dir():
                destination.mkdir(mode=0o700)
                continue
            if not source.is_file():
                raise SetupError("profile-stage-invalid", "Syncthing 临时 profile 含无法识别的文件类型。")
            with source.open("rb") as input_file, destination.open("xb") as output_file:
                shutil.copyfileobj(input_file, output_file)
                output_file.flush()
                os.fsync(output_file.fileno())
            if platform.system().lower() != "windows":
                import stat
                os.chmod(destination, stat.S_IMODE(source.stat().st_mode))
    except FileExistsError as exc:
        raise SetupError("profile-create-conflict", "Syncthing profile 文件在创建期间被占用，未覆盖。") from exc
    except SetupError:
        raise
    except OSError as exc:
        raise SetupError("profile-install-failed", "无法安全复制生成的 Syncthing profile；已保留部分进度。") from exc


def backup_targets(codex_home: Path, targets: list[tuple[Path, str]]) -> str | None:
    existing = [(path, name) for path, name in targets if path.exists()]
    if not existing:
        return None
    second_brain = codex_home / "second-brain"
    backups = second_brain / "backups"
    if second_brain.is_symlink() or backups.is_symlink():
        raise SetupError("backup-path-conflict", "第二大脑备份目录是符号链接，未写入任何目标文件。")
    if second_brain.exists() and not second_brain.is_dir():
        raise SetupError("backup-path-conflict", "第二大脑配置路径不是目录，未写入任何目标文件。")
    if backups.exists() and not backups.is_dir():
        raise SetupError("backup-path-conflict", "备份目标不是目录，未写入任何目标文件。")
    backup_location = backups.resolve()
    if is_inside_git_repository(backup_location) or any(
        is_within_path(backup_location, root) for root in (PACK_ROOT,)
    ):
        raise SetupError("backup-path-conflict", "备份目标位于 Git 仓库内，未写入任何目标文件。")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = backups / f"{timestamp}-syncthing-setup"
    suffix = 1
    while backup_root.exists():
        backup_root = codex_home / "second-brain" / "backups" / f"{timestamp}-syncthing-setup-{suffix}"
        suffix += 1
    _PROGRESS["phase"] = "backup"
    _PROGRESS["backupPath"] = str(backup_root)
    backup_root.mkdir(parents=True, mode=0o700)
    for source, name in existing:
        target = backup_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if platform.system().lower() != "windows":
            target.chmod(0o600)
    return str(backup_root)


def profile_is_compliant(root: ET.Element, vault: Path) -> bool:
    try:
        return bool(validate_profile(root, vault)["compliant"])
    except SetupError:
        return False


def _task_xml(executable: Path, profile: Path) -> bytes:
    whoami = shutil.which("whoami")
    account = run([whoami], timeout=5).stdout.strip() if whoami else ""
    user = account or os.environ.get("USERNAME") or os.environ.get("USER") or ""
    root = ET.Element("Task", {"version": "1.4", "xmlns": "http://schemas.microsoft.com/windows/2004/02/mit/task"})
    triggers = ET.SubElement(root, "Triggers")
    trigger = ET.SubElement(triggers, "LogonTrigger")
    ET.SubElement(trigger, "Enabled").text = "true"
    principals = ET.SubElement(root, "Principals")
    principal = ET.SubElement(principals, "Principal", {"id": "Author"})
    ET.SubElement(principal, "UserId").text = user
    ET.SubElement(principal, "LogonType").text = "InteractiveToken"
    ET.SubElement(principal, "RunLevel").text = "LeastPrivilege"
    settings = ET.SubElement(root, "Settings")
    ET.SubElement(settings, "MultipleInstancesPolicy").text = "IgnoreNew"
    ET.SubElement(settings, "StartWhenAvailable").text = "true"
    ET.SubElement(settings, "Enabled").text = "true"
    ET.SubElement(settings, "ExecutionTimeLimit").text = "PT0S"
    ET.SubElement(settings, "DisallowStartIfOnBatteries").text = "false"
    ET.SubElement(settings, "StopIfGoingOnBatteries").text = "false"
    actions = ET.SubElement(root, "Actions", {"Context": "Author"})
    action = ET.SubElement(actions, "Exec")
    ET.SubElement(action, "Command").text = str(executable)
    args = desired_arguments(profile)
    ET.SubElement(action, "Arguments").text = subprocess.list2cmdline(args)
    ET.SubElement(action, "WorkingDirectory").text = str(executable.parent)
    return ET.tostring(root, encoding="utf-16", xml_declaration=True)


def _launch_agent(executable: Path, profile: Path) -> bytes:
    label = "com.codex.lazy-pack.syncthing"
    payload = {
        "Label": label,
        "ProgramArguments": [str(executable), *desired_arguments(profile)],
        "EnvironmentVariables": {
            "STGUIADDRESS": LOCAL_GUI_ADDRESS,
        },
        "RunAtLoad": True,
        "KeepAlive": True,
    }
    return plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True)


def _systemd_unit(executable: Path, profile: Path) -> bytes:
    args = shlex.join([str(executable), *desired_arguments(profile)])
    content = (
        "[Unit]\nDescription=Codex Second Brain Syncthing\nAfter=default.target\n\n"
        "[Service]\nType=simple\n"
        f"Environment=STGUIADDRESS={LOCAL_GUI_ADDRESS}\n"
        "ExecStart=" + args + "\nRestart=on-failure\nRestartSec=5\n\n"
        "[Install]\nWantedBy=default.target\n"
    )
    return content.encode("utf-8")


def _xdg_desktop(executable: Path, profile: Path) -> bytes:
    def quote_argument(value: str) -> str:
        escaped = value.replace("%", "%%").replace("\\", "\\\\").replace('"', '\\"')
        escaped = escaped.replace("$", "\\$").replace("`", "\\`")
        return f'"{escaped}"'

    args = " ".join(quote_argument(item) for item in [str(executable), *desired_arguments(profile)])
    return (
        "[Desktop Entry]\nType=Application\nName=Syncthing (Codex Second Brain)\n"
        "Comment=Local-only paused second-brain folder\n"
        f"Exec={args}\nTerminal=false\nX-GNOME-Autostart-enabled=true\n"
    ).encode("utf-8")


def _require_ssh_linger() -> str | None:
    headless = not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if not (os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_CLIENT") or headless):
        return None
    loginctl = shutil.which("loginctl")
    user = os.environ.get("USER") or ""
    linger = run([loginctl, "show-user", user, "--property=Linger", "--value"], timeout=10) if loginctl and user else None
    if linger is None or linger.returncode != 0 or linger.stdout.strip().casefold() not in {"yes", "true"}:
        raise SetupError(
            "linger-required",
            f"SSH 服务器需要为用户 {user or '<当前用户>'} 启用 systemd linger，才能在 SSH 注销后持续运行。请由你在服务器上执行 `sudo loginctl enable-linger {user or '<用户名>'}`，完成后重新运行 05；本次尚未创建或复用服务。",
        )
    return user


def register_startup(executable: Path, profile: Path, existing: StartupEntry | None) -> dict[str, Any]:
    if existing:
        if linux_headless_or_ssh() and existing.kind == "xdg-autostart":
            raise SetupError("headless-xdg-conflict", "SSH/无桌面 Linux 不得复用桌面 XDG 自启动项；请先确认 systemd 用户服务方案。")
        if not existing.enabled:
            raise SetupError("startup-disabled", "已有 Syncthing 登录启动项处于禁用状态；未更改其状态。")
        if not startup_is_safe(existing, profile):
            raise SetupError("startup-conflict", "已有 Syncthing 自启动项参数不符合本机安全基线，未覆盖。")
        linger_user = _require_ssh_linger() if existing.kind == "systemd-user" else None
        return {"state": "reused", "kind": existing.kind, "name": existing.name, "registered": True, "lingerEnabled": True if linger_user else None}

    system = platform.system().lower()
    if system == "windows":
        task_name = "Codex Lazy Pack - Syncthing"
        schtasks = shutil.which("schtasks.exe")
        if not schtasks:
            raise SetupError("startup-unavailable", "找不到 Windows Task Scheduler 命令。")
        exists = run([schtasks, "/Query", "/TN", task_name], timeout=10)
        if exists.returncode == 0:
            raise SetupError("startup-name-conflict", "预留的 Syncthing 登录任务名称已被占用，未覆盖。")
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as temp:
            temp_path = Path(temp.name)
            temp.write(_task_xml(executable, profile))
        try:
            result = run([schtasks, "/Create", "/TN", task_name, "/XML", str(temp_path)], timeout=30)
        finally:
            temp_path.unlink(missing_ok=True)
        if result.returncode != 0:
            raise SetupError("startup-register-failed", "无法注册 Windows 用户登录任务。")
        return {"state": "registered", "kind": "windows-task", "name": task_name, "registered": True}

    if system == "darwin":
        path = Path.home() / "Library/LaunchAgents/com.codex.lazy-pack.syncthing.plist"
        write_new_atomic(path, _launch_agent(executable, profile))
        uid = os.getuid()
        result = run(["launchctl", "bootstrap", f"gui/{uid}", str(path)], timeout=20)
        if result.returncode != 0:
            raise SetupError("startup-register-failed", "无法加载 macOS 用户 LaunchAgent。")
        return {"state": "registered", "kind": "launch-agent", "name": path.stem, "registered": True}

    systemctl = shutil.which("systemctl")
    if systemctl and run([systemctl, "--user", "show-environment"], timeout=10).returncode == 0:
        linger_user = _require_ssh_linger()
        directory = Path.home() / ".config/systemd/user"
        path = directory / "codex-lazy-pack-syncthing.service"
        write_new_atomic(path, _systemd_unit(executable, profile), 0o600)
        reload_result = run([systemctl, "--user", "daemon-reload"], timeout=15)
        enable_result = run([systemctl, "--user", "enable", "--now", path.name], timeout=30)
        if reload_result.returncode != 0 or enable_result.returncode != 0:
            raise SetupError("startup-register-failed", "无法启用 systemd 用户登录服务。")
        return {"state": "registered", "kind": "systemd-user", "name": path.name, "registered": True, "lingerEnabled": True if linger_user else None}

    if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_CLIENT") or not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise SetupError(
            "headless-user-service-unavailable",
            "当前是无桌面的 Linux/SSH 环境且 systemd 用户服务不可用，不能用桌面自启动满足注销后运行。请在服务器配置可持久化的用户服务后重试；不要以 root 运行 Syncthing。",
        )
    path = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "autostart/codex-lazy-pack-syncthing.desktop"
    write_new_atomic(path, _xdg_desktop(executable, profile), 0o600)
    return {"state": "registered", "kind": "xdg-autostart", "name": path.name, "registered": True}


def launch_existing_startup(entry: StartupEntry | None, executable: Path, profile: Path) -> None:
    if entry and entry.kind == "process":
        return
    system = platform.system().lower()
    if system == "windows":
        task_name = entry.name if entry else "Codex Lazy Pack - Syncthing"
        result = run([shutil.which("schtasks.exe") or "schtasks.exe", "/Run", "/TN", task_name], timeout=20)
        if result.returncode != 0:
            raise SetupError("service-start-failed", "Windows 登录任务已注册，但启动失败。")
    elif system == "darwin":
        label = entry.name if entry else "com.codex.lazy-pack.syncthing"
        uid = os.getuid()
        result = run(["launchctl", "kickstart", "-k", f"gui/{uid}/{label}"], timeout=20)
        if result.returncode != 0 and not entry:
            path = Path.home() / "Library/LaunchAgents/com.codex.lazy-pack.syncthing.plist"
            result = run(["launchctl", "bootstrap", f"gui/{uid}", str(path)], timeout=20)
        if result.returncode != 0:
            raise SetupError("service-start-failed", "macOS 用户 LaunchAgent 已注册，但后台启动失败。")
    else:
        if entry and entry.kind == "xdg-autostart":
            subprocess.Popen(
                [str(executable), *desired_arguments(profile)],
                cwd=str(executable.parent),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return
        if entry and entry.kind == "systemd-user":
            unit = entry.name
        elif shutil.which("systemctl") and run([shutil.which("systemctl") or "systemctl", "--user", "show-environment"]).returncode == 0:
            unit = "codex-lazy-pack-syncthing.service"
        else:
            return
        result = run([shutil.which("systemctl") or "systemctl", "--user", "start", unit], timeout=25)
        if result.returncode != 0:
            raise SetupError("service-start-failed", "systemd 用户服务已注册，但后台启动失败。")


def wait_for_runtime(profile: Path, executable: Path, timeout_seconds: int = 20) -> bool:
    # Avoid REST/API credentials in process arguments or logs. Runtime is verified
    # by matching the process command line to the resolved executable and profile.
    deadline = datetime.now(timezone.utc).timestamp() + timeout_seconds
    while datetime.now(timezone.utc).timestamp() < deadline:
        for item in discover_running():
            if same_path(item.executable, executable) and item.home and same_path(item.home, profile):
                return True
        import time
        time.sleep(0.5)
    return False


def _normalized_device_id(value: str) -> str:
    return re.sub(r"[\s-]+", "", value).upper()


def _runtime_state_from_api(
    root: ET.Element,
    vault: Path,
    status: Any,
    connections: Any,
    devices: Any,
    folders: Any,
) -> dict[str, Any]:
    def invalid() -> SetupError:
        return SetupError("runtime-api-invalid", "Syncthing 运行时 API 返回无法验证的设备或文件夹状态。")

    configured_devices = [node for node in list(root) if _xml_name(node) == "device"]
    if len(configured_devices) != 1 or not configured_devices[0].get("id"):
        raise invalid()
    configured_local_id = configured_devices[0].get("id", "")
    if not isinstance(status, dict) or not isinstance(status.get("myID"), str) or not status["myID"]:
        raise invalid()
    api_local_id = status["myID"]
    local_matches = _normalized_device_id(api_local_id) == _normalized_device_id(configured_local_id)

    if not isinstance(devices, list):
        raise invalid()
    api_device_ids: list[str] = []
    for item in devices:
        if not isinstance(item, dict) or not isinstance(item.get("deviceID"), str) or not item["deviceID"]:
            raise invalid()
        api_device_ids.append(item["deviceID"])
    normalized_api_device_ids = [_normalized_device_id(item) for item in api_device_ids]
    if len(set(normalized_api_device_ids)) != len(normalized_api_device_ids):
        raise invalid()
    local_api_matches = [item for item in normalized_api_device_ids if item == _normalized_device_id(api_local_id)]
    if len(local_api_matches) != 1:
        raise invalid()
    configured_remote_count = sum(
        1 for item in normalized_api_device_ids if item != _normalized_device_id(api_local_id)
    )

    if not isinstance(connections, dict) or not isinstance(connections.get("connections"), dict):
        raise invalid()
    connected_remote_count = 0
    for device_id, state in connections["connections"].items():
        if device_id == "_total":
            continue
        if not isinstance(device_id, str) or not isinstance(state, dict) or not isinstance(state.get("connected"), bool):
            raise invalid()
        if _normalized_device_id(device_id) != _normalized_device_id(api_local_id) and state["connected"]:
            connected_remote_count += 1

    target_folders = [
        item
        for item in list(root)
        if _xml_name(item) == "folder"
        and item.get("id")
        and item.get("path")
        and same_path(item.get("path", ""), vault)
    ]
    if len(target_folders) != 1:
        raise invalid()
    target_id = target_folders[0].get("id")
    if not isinstance(folders, list):
        raise invalid()
    matches = [item for item in folders if isinstance(item, dict) and item.get("id") == target_id]
    if len(matches) != 1:
        raise invalid()
    runtime_folder = matches[0]
    if not isinstance(runtime_folder.get("path"), str) or not isinstance(runtime_folder.get("paused"), bool):
        raise invalid()
    folder_path_matches = same_path(runtime_folder["path"], vault)
    folder_devices = runtime_folder.get("devices")
    if not isinstance(folder_devices, list):
        raise invalid()
    folder_device_ids: list[str] = []
    for item in folder_devices:
        if not isinstance(item, dict) or not isinstance(item.get("deviceID"), str) or not item["deviceID"]:
            raise invalid()
        folder_device_ids.append(_normalized_device_id(item["deviceID"]))
    folder_devices_match = (
        len(folder_device_ids) == 1
        and folder_device_ids[0] == _normalized_device_id(api_local_id)
    )
    return {
        "available": True,
        "connectionStatus": "connected" if connected_remote_count else "none",
        "configuredRemoteCount": configured_remote_count,
        "connectedRemoteCount": connected_remote_count,
        "localDeviceIdMatchesProfile": local_matches,
        "folderPaused": runtime_folder["paused"],
        "folderPathMatches": folder_path_matches,
        "folderDevicesMatch": folder_devices_match,
    }


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        raise HTTPError(req.full_url, code, "Syncthing 本机 API 不允许重定向", headers, fp)


def build_local_api_opener(*, tls: bool):
    handlers: list[Any] = [ProxyHandler({}), _NoRedirectHandler()]
    if tls:
        handlers.append(HTTPSHandler(context=ssl._create_unverified_context()))
    return build_opener(*handlers)


def runtime_api_state(profile: Path, vault: Path) -> dict[str, Any]:
    root = inspect_xml(profile / "config.xml")
    gui = _xml_local(root, "gui")
    if gui is None:
        return {"available": False, "connectionStatus": "unavailable"}
    gui_addresses = [node for node in list(gui) if _xml_name(node) == "address"]
    if len(gui_addresses) != 1 or not (gui_addresses[0].text or "").strip():
        return {"available": False, "connectionStatus": "gui-address-ambiguous"}
    address = (gui_addresses[0].text or "").strip()
    host, separator, port_text = address.rpartition(":")
    if not separator or host != "127.0.0.1" or not port_text.isdigit():
        return {"available": False, "connectionStatus": "not-local"}
    port = int(port_text)
    if not 1 <= port <= 65535:
        return {"available": False, "connectionStatus": "not-local"}
    api_key = _xml_text(gui, "apikey", "")
    if not api_key:
        return {"available": False, "connectionStatus": "api-key-missing"}
    tls = gui.get("tls", "false").lower() == "true"
    scheme = "https" if tls else "http"
    opener = build_local_api_opener(tls=tls)

    def get_json(path: str) -> Any:
        request = Request(
            f"{scheme}://127.0.0.1:{port}{path}",
            headers={"X-API-Key": api_key, "User-Agent": USER_AGENT},
            method="GET",
        )
        with opener.open(request, timeout=4) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        status = get_json("/rest/system/status")
        connections = get_json("/rest/system/connections")
        devices = get_json("/rest/config/devices")
        folders = get_json("/rest/config/folders")
        return _runtime_state_from_api(root, vault, status, connections, devices, folders)
    except SetupError:
        return {"available": False, "connectionStatus": "api-invalid"}
    except Exception:
        return {"available": False, "connectionStatus": "api-unavailable"}


def verify_runtime_state(state: dict[str, Any]) -> None:
    if (
        not isinstance(state, dict)
        or state.get("available") is not True
        or state.get("folderPaused") is not True
        or type(state.get("configuredRemoteCount")) is not int
        or state.get("configuredRemoteCount") != 0
        or type(state.get("connectedRemoteCount")) is not int
        or state.get("connectedRemoteCount") != 0
        or state.get("localDeviceIdMatchesProfile") is not True
        or state.get("folderPathMatches") is not True
        or state.get("folderDevicesMatch") is not True
        or state.get("connectionStatus") != "none"
    ):
        raise SetupError(
            "runtime-verification-failed",
            "Syncthing 运行时 API 不可用，或有效状态偏离本机、无远端、文件夹暂停基线；不能报告配置成功。",
        )


def _assert_empty_server_vault(vault: Path) -> None:
    if not vault.exists():
        return
    if not vault.is_dir() or vault.is_symlink():
        raise SetupError("server-vault-not-directory", "服务器接收路径不是普通目录；未修改。")
    try:
        unexpected = [item.name for item in vault.iterdir() if item.name not in {".stignore", ".stfolder"}]
    except OSError as exc:
        raise SetupError("server-vault-unreadable", "无法检查服务器接收目录是否为空；未修改。") from exc
    if unexpected:
        raise SetupError("server-vault-not-empty", "服务器接收目录含有 Vault 内容或未知文件；为避免覆盖/合并，未修改。")


def _create_confirmed_empty_vault(vault: Path, confirmed: bool, role: str, *, expected_missing: bool) -> bool:
    if vault.exists():
        if expected_missing:
            raise SetupError("server-vault-race", "服务器 Vault 路径在预检后已出现；重新检查目录内容后再继续。")
        if role == "server":
            _assert_empty_server_vault(vault)
        return False
    if role != "server" or not confirmed:
        raise SetupError("server-vault-confirmation-required", "服务器 Vault 目录不存在；需先展示精确路径并取得用户确认后再创建。")
    if not vault.parent.is_dir() or vault.parent.is_symlink() or vault == vault.parent:
        raise SetupError("server-vault-parent-invalid", "服务器 Vault 的父目录不存在、不是普通目录或为符号链接；未创建目录。")
    try:
        vault.mkdir()
    except FileExistsError as exc:
        raise SetupError("server-vault-race", "服务器 Vault 路径在预检后被创建；重新检查目录内容后再继续。") from exc
    _assert_empty_server_vault(vault)
    return True


def preflight(codex_home: Path, lock_path: Path, supplied_vault: str | None, *, role: str = "primary") -> dict[str, Any]:
    package_version, lock = load_lock(lock_path)
    onboarding_path = codex_home / SYNC_ONBOARDING_RELATIVE
    onboarding_state = None
    if onboarding_path.exists() or onboarding_path.is_symlink():
        _, _, onboarding_state = _read_sync_onboarding_state(codex_home, role)
    pending_onboarding = bool(onboarding_state and onboarding_state.get("pendingOperation") is not None)
    paired_onboarding = bool(
        onboarding_state
        and onboarding_state.get("status") != "local-prepared"
        and not pending_onboarding
    )
    original_device, updated_device, vault, device_path, device_snapshot = read_device_config(
        codex_home, supplied_vault, role=role, allow_missing_vault=(role == "server")
    )
    if role == "server" and not paired_onboarding and not pending_onboarding:
        _assert_empty_server_vault(vault)
    if paired_onboarding and not vault.is_dir():
        raise SetupError("paired-vault-missing", "设备已进入双机引导阶段，但本机 Vault 目录不可访问；不创建空目录或更改现有配置。")
    if is_within_path(device_path, vault) or is_inside_git_repository(device_path):
        raise SetupError("device-config-location-conflict", "设备配置位于 Vault 或 Git 仓库中，未修改。")
    startup = discover_startup_entries()
    assert_safe_syncthing_environment(startup)
    running = discover_running()
    profile = profile_dir_for(startup + running)
    if is_within_path(profile, vault) or is_inside_git_repository(profile):
        raise SetupError("profile-location-conflict", "Syncthing 配置目录位于 Vault 或 Git 仓库中，未修改。")
    if profile.exists() and not (profile / "config.xml").exists():
        raise SetupError("profile-partial", "Syncthing 配置目录已存在但不含 config.xml，未覆盖。")
    matching_startup = startup_for_profile(startup, profile)
    if linux_headless_or_ssh() and matching_startup and matching_startup.kind == "xdg-autostart":
        raise SetupError("headless-xdg-conflict", "SSH/无桌面 Linux 发现既有 XDG 自启动项；为避免注销后停止，未复用或改写。")
    if matching_startup and not matching_startup.enabled:
        raise SetupError("startup-disabled", "已有 Syncthing 登录启动项处于禁用状态；停止相关配置写入。")
    matching_processes = [item for item in running if process_targets_profile(item, profile)]
    if len(matching_processes) > 1:
        raise SetupError("running-process-duplicate", "同一配置目录有多个 Syncthing 进程，未修改。")
    if any(not startup_is_safe(item, profile) for item in matching_processes):
        raise SetupError("running-process-conflict", "现有 Syncthing 进程启动参数无法确认符合本机基线，未修改。")
    candidates = executable_candidates(startup + running)
    if matching_startup and matching_startup.kind != "process":
        startup_executable = Path(matching_startup.executable).expanduser()
        if not startup_executable.is_absolute() or not startup_executable.is_file():
            raise SetupError("startup-executable-missing", "已有 Syncthing 登录项指向的程序不存在或路径不明确。")
        candidates = [startup_executable.resolve()]
    if matching_processes:
        process_executable = Path(matching_processes[0].executable).expanduser()
        if not process_executable.is_file():
            raise SetupError("running-executable-missing", "无法验证正在运行的 Syncthing 可执行文件路径。")
        if matching_startup and not same_path(candidates[0], process_executable):
            raise SetupError("running-executable-conflict", "启动项和运行进程使用不同 Syncthing 程序，未修改。")
        candidates = [process_executable.resolve()]
    executable_name = "syncthing.exe" if platform.system().lower() == "windows" else "syncthing"
    locked_executable = app_install_dir() / str(lock["version"]) / executable_name
    if not matching_startup and not matching_processes:
        if locked_executable.exists() and not any(same_path(locked_executable, item) for item in candidates):
            candidates.append(locked_executable.resolve())
        if len(candidates) > 1:
            raise SetupError("executable-ambiguous", "发现多个 Syncthing 程序且没有启动项可确定应复用哪一个，未修改。")
    executable = candidates[0] if candidates else None
    version_text = None
    if executable:
        version_text, _ = syncthing_version(executable)
    profile_path = profile / "config.xml"
    if profile.is_symlink() or profile_path.is_symlink():
        raise SetupError("profile-symlink", "Syncthing 配置目录或 config.xml 是符号链接，未修改。")
    profile_state: dict[str, Any] | None = None
    if paired_onboarding and not profile_path.is_file():
        raise SetupError("paired-profile-missing", "设备已进入双机引导阶段，但本机 Syncthing profile/config.xml 不存在；不生成新身份或重置同步配置。")
    if profile_path.exists():
        root = inspect_xml(profile_path)
        if pending_onboarding:
            profile_state = {"verification": "deferred-pending-operation"}
        elif paired_onboarding:
            profile_state = validate_existing_pair_profile(root, vault, role, onboarding_state or {})
            if executable is None:
                raise SetupError("paired-syncthing-executable-missing", "设备已进入双机引导阶段，但无法识别本机 Syncthing 程序；不安装、启动或重置现有同步配置。")
            verify_local_device_identity(executable, profile, profile_state["localDeviceId"])
        else:
            profile_state = validate_profile(root, vault)
            if executable is not None:
                verify_local_device_identity(executable, profile, profile_state["localDeviceId"])
        if not pending_onboarding and not paired_onboarding and not profile_is_compliant(root, vault):
            # A stopped profile is safely updated offline. A live profile is not
            # rewritten while the daemon may be saving the same file.
            active = any(
                process_targets_profile(item, profile) for item in running
            )
            if active:
                raise SetupError("running-profile-needs-change", "Syncthing 正在运行且配置需变更；为避免并发覆盖，未写入。")
    ignore_path, merged_ignore, ignore_added, ignore_exists = prepare_ignore(vault)
    if matching_startup and matching_startup.kind != "process" and not startup_is_safe(matching_startup, profile):
        raise SetupError("startup-conflict", "已有登录启动项参数不符合无浏览器本机基线，未修改。")
    return {
        "status": "ready",
        "packageVersion": package_version,
        "platform": platform_key(),
        "codexHome": str(codex_home),
        "syncOnboarding": {
            "status": onboarding_state.get("status") if onboarding_state else None,
            "pairedProfile": paired_onboarding,
            "pendingOperation": ({"action": onboarding_state["pendingOperation"].get("action"), "phase": onboarding_state["pendingOperation"].get("phase")} if onboarding_state and isinstance(onboarding_state.get("pendingOperation"), dict) else ("invalid" if onboarding_state and onboarding_state.get("pendingOperation") is not None else None)),
        },
        "deviceConfig": {
            "path": str(device_path),
            "exists": device_path.exists(),
            "snapshotSha256": hashlib.sha256(device_snapshot).hexdigest() if device_snapshot is not None else None,
            "needsWrite": updated_device != (_read_json_object(device_path) if device_path.exists() else {}),
            "deviceLabel": updated_device.get("deviceLabel"),
        },
        "vault": {"path": str(vault), "exists": vault.is_dir()},
        "syncthing": {
            "version": version_text,
            "executable": str(executable) if executable else None,
            "installRequired": executable is None,
            "profilePath": str(profile),
            "profileExists": profile_path.exists(),
            "profileState": profile_state,
            "running": any(
                process_targets_profile(item, profile) for item in running
            ),
        },
        "ignore": {"path": str(ignore_path), "exists": ignore_exists, "rulesToAdd": ignore_added},
        "startup": {
            "state": "reuse" if matching_startup else "create",
            "kind": matching_startup.kind if matching_startup else None,
            "name": matching_startup.name if matching_startup else None,
        },
    }


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


_ONBOARDING_STAGE_ORDER = {
    "primary": {"local-prepared": 0, "paired-paused": 1, "seeding": 2, "primary-promoted": 3, "active": 4},
    "server": {"local-prepared": 0, "paired-paused": 1, "receiver-ready": 2, "seed-verified": 3, "server-promoted": 4, "active": 5},
}

_ONBOARDING_OPERATION_START = {
    ("server", "arm-receiver"): "paired-paused",
    ("primary", "start-source"): "paired-paused",
    ("server", "promote-server"): "seed-verified",
    ("primary", "promote-primary"): "seeding",
}

_ONBOARDING_OPERATION_COMPLETION = {
    ("server", "arm-receiver"): "receiver-ready",
    ("primary", "start-source"): "seeding",
    ("server", "promote-server"): "server-promoted",
    ("primary", "promote-primary"): "primary-promoted",
}


def write_sync_onboarding_state(
    codex_home: Path,
    role: str,
    status: str,
    *,
    peer_syncthing_device_id: str | None = None,
    syncthing_device_id: str | None = None,
) -> dict[str, Any]:
    if role not in _ONBOARDING_STAGE_ORDER or status not in _ONBOARDING_STAGE_ORDER[role]:
        raise SetupError("onboarding-state-invalid", "第二大脑同步引导状态值无效。")
    path = codex_home / SYNC_ONBOARDING_RELATIVE
    snapshot = snapshot_file(path, "第二大脑同步引导状态")
    current: dict[str, Any] = {}
    if snapshot is not None:
        try:
            loaded = json.loads(snapshot.decode("utf-8"))
        except (UnicodeError, ValueError) as exc:
            raise SetupError("onboarding-state-invalid", "同步引导状态文件损坏；未覆盖。") from exc
        if not isinstance(loaded, dict) or loaded.get("schemaVersion") != 1:
            raise SetupError("onboarding-state-invalid", "同步引导状态文件格式不受支持；未覆盖。")
        if loaded.get("role") not in {None, role}:
            raise SetupError("onboarding-role-conflict", "同步引导状态记录了不同设备角色；未覆盖。")
        if loaded.get("status") is not None and loaded.get("status") not in _ONBOARDING_STAGE_ORDER[role]:
            raise SetupError("onboarding-state-invalid", "同步引导状态包含未知阶段；未覆盖。")
        existing_peer = loaded.get("peerSyncthingDeviceId")
        if existing_peer is not None and not isinstance(existing_peer, str):
            raise SetupError("onboarding-state-invalid", "同步引导状态中的配对设备 ID 格式无效；未覆盖。")
        existing_device = loaded.get("syncthingDeviceId")
        if existing_device is not None and not isinstance(existing_device, str):
            raise SetupError("onboarding-state-invalid", "同步引导状态中的本机 Syncthing Device ID 格式无效；未覆盖。")
        if peer_syncthing_device_id and existing_peer and _normalized_device_id(existing_peer) != _normalized_device_id(peer_syncthing_device_id):
            raise SetupError("onboarding-peer-conflict", "同步引导状态已绑定另一台设备；未覆盖。")
        if syncthing_device_id and existing_device and _normalized_device_id(existing_device) != _normalized_device_id(syncthing_device_id):
            raise SetupError("onboarding-device-conflict", "同步引导状态已绑定另一台本机 Syncthing 身份；未覆盖。")
        if loaded.get("pendingOperation") is not None:
            raise SetupError("onboarding-operation-pending", "同步引导存在未完成的操作；必须先按恢复流程处理，未推进阶段。")
        current = loaded
    current_status = current.get("status")
    order = _ONBOARDING_STAGE_ORDER[role]
    if current_status in order and order[current_status] > order[status]:
        return {"path": str(path), "status": current_status, "preserved": True, "backupPath": None}
    if (current_status == status and current.get("folderId") == FOLDER_ID
            and (not peer_syncthing_device_id or (isinstance(current.get("peerSyncthingDeviceId"), str)
                 and _normalized_device_id(current["peerSyncthingDeviceId"]) == _normalized_device_id(peer_syncthing_device_id)))
            and (not syncthing_device_id or (isinstance(current.get("syncthingDeviceId"), str)
                 and _normalized_device_id(current["syncthingDeviceId"]) == _normalized_device_id(syncthing_device_id)))):
        return {"path": str(path), "status": current_status, "preserved": True, "backupPath": None}
    updated = dict(current)
    updated.update({
        "schemaVersion": 1,
        "role": role,
        "status": status,
        "folderId": FOLDER_ID,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    })
    if peer_syncthing_device_id:
        updated["peerSyncthingDeviceId"] = peer_syncthing_device_id
    if syncthing_device_id:
        updated["syncthingDeviceId"] = syncthing_device_id
    backup = backup_targets(codex_home, [(path, "second-brain/sync-onboarding.json")]) if snapshot is not None else None
    write_atomic(path, (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode("utf-8"), mode=0o600, expected_current=snapshot)
    return {"path": str(path), "status": status, "preserved": False, "backupPath": backup}


def _read_sync_onboarding_state(codex_home: Path, role: str) -> tuple[Path, bytes | None, dict[str, Any]]:
    if role not in _ONBOARDING_STAGE_ORDER:
        raise SetupError("onboarding-state-invalid", "第二大脑同步引导设备角色无效。")
    path = codex_home / SYNC_ONBOARDING_RELATIVE
    snapshot = snapshot_file(path, "第二大脑同步引导状态")
    if snapshot is None:
        raise SetupError("onboarding-state-missing", "缺少第二大脑同步引导状态；先完成本机 setup。")
    try:
        loaded = json.loads(snapshot.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise SetupError("onboarding-state-invalid", "同步引导状态文件损坏；未覆盖。") from exc
    if not isinstance(loaded, dict) or loaded.get("schemaVersion") != 1:
        raise SetupError("onboarding-state-invalid", "同步引导状态文件格式不受支持；未覆盖。")
    if loaded.get("role") != role or loaded.get("status") not in _ONBOARDING_STAGE_ORDER[role]:
        raise SetupError("onboarding-state-invalid", "同步引导状态中的设备角色或阶段不匹配。")
    if loaded.get("folderId") != FOLDER_ID:
        raise SetupError("onboarding-state-invalid", "同步引导状态中的 folder ID 不匹配。")
    return path, snapshot, loaded


def _write_sync_onboarding_snapshot(
    codex_home: Path, path: Path, snapshot: bytes, updated: dict[str, Any]
) -> dict[str, Any]:
    backup = backup_targets(codex_home, [(path, "second-brain/sync-onboarding.json")])
    write_atomic(
        path,
        (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        mode=0o600,
        expected_current=snapshot,
    )
    return {"path": str(path), "status": updated.get("status"), "backupPath": backup}


def begin_sync_onboarding_operation(
    codex_home: Path,
    role: str,
    *,
    action: str,
    syncthing_device_id: str,
    peer_syncthing_device_id: str,
    vault_path: str,
    expected_folder_type: str,
    backup_path: str,
    confirmations: dict[str, bool],
    source_folder_type: str | None = None,
    baseline_manifest_sha256: str | None = None,
    peer_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    if (role, action) not in _ONBOARDING_OPERATION_START:
        raise SetupError("onboarding-operation-invalid", "不支持的同步引导操作。")
    path, snapshot, current = _read_sync_onboarding_state(codex_home, role)
    status = str(current["status"])
    pending = current.get("pendingOperation")
    committed_recovery = isinstance(pending, dict) and pending.get("completionCommitUncertain") is True
    if pending is not None:
        if (not isinstance(pending, dict) or pending.get("action") != action
                or pending.get("phase") != "held" or not isinstance(pending.get("operationId"), str)):
            raise SetupError("onboarding-operation-pending", "存在其他或尚未恢复的同步操作；未解除暂停。")
        expected_start_status = _ONBOARDING_OPERATION_START[(role, action)]
        expected_completion = _ONBOARDING_OPERATION_COMPLETION[(role, action)]
        expected_current_status = expected_completion if committed_recovery else expected_start_status
        if (status != expected_current_status or pending.get("previousStatus") != expected_start_status
                or (committed_recovery and pending.get("committedStatus") != expected_completion)):
            raise SetupError("onboarding-operation-state-conflict", "待恢复操作原阶段与当前引导阶段不符；保持暂停并人工检查。")
        for key, expected in (("syncthingDeviceId", syncthing_device_id), ("peerSyncthingDeviceId", peer_syncthing_device_id), ("vaultPath", vault_path), ("folderId", FOLDER_ID)):
            actual = pending.get(key)
            if key.endswith("DeviceId"):
                matches = isinstance(actual, str) and _normalized_device_id(actual) == _normalized_device_id(expected)
            else:
                matches = actual == expected
            if not matches:
                raise SetupError("onboarding-operation-identity-conflict", "待恢复操作的设备身份或路径与当前环境不一致；未解除暂停。")
        if pending.get("previousStatus") != expected_start_status:
            raise SetupError("onboarding-operation-state-conflict", "待恢复操作记录的阶段与当前阶段不一致；未解除暂停。")
        if not isinstance(pending.get("containment"), dict) or pending["containment"].get("containmentVerified") is not True:
            raise SetupError("onboarding-operation-containment-unverified", "待恢复操作没有已核验的暂停记录；未解除暂停。")
        if not isinstance(confirmations, dict) or not all(value is True for value in confirmations.values()):
            raise SetupError("onboarding-operation-confirmation-required", "重试同步操作需要重新确认所有必要条件。")
    elif status != _ONBOARDING_OPERATION_START[(role, action)]:
        raise SetupError("onboarding-operation-order-conflict", "当前引导阶段不允许开始该同步操作。")

    existing_device = current.get("syncthingDeviceId")
    existing_peer = current.get("peerSyncthingDeviceId")
    if existing_device and _normalized_device_id(str(existing_device)) != _normalized_device_id(syncthing_device_id):
        raise SetupError("onboarding-device-conflict", "同步引导状态中的本机身份与当前 Syncthing profile 不符。")
    if existing_peer and _normalized_device_id(str(existing_peer)) != _normalized_device_id(peer_syncthing_device_id):
        raise SetupError("onboarding-peer-conflict", "同步引导状态中的配对身份与当前对端不符。")
    if action == "arm-receiver" and (role != "server" or expected_folder_type != "receiveonly"):
        raise SetupError("onboarding-operation-invalid", "服务器仅可执行 receive-only 接收准备。")
    if action == "start-source" and (role != "primary" or expected_folder_type != "sendonly"):
        raise SetupError("onboarding-operation-invalid", "个人电脑仅可执行 send-only 首次播种。")
    if action in {"promote-server", "promote-primary"} and (
        expected_folder_type != "sendreceive"
        or source_folder_type != ("receiveonly" if role == "server" else "sendonly")
        or not isinstance(baseline_manifest_sha256, str)
        or not re.fullmatch(r"[0-9a-fA-F]{64}", baseline_manifest_sha256)
        or not isinstance(peer_manifest_sha256, str)
        or not re.fullmatch(r"[0-9a-fA-F]{64}", peer_manifest_sha256)
        or baseline_manifest_sha256.lower() != peer_manifest_sha256.lower()
    ):
        raise SetupError("onboarding-operation-invalid", "晋级操作缺少有效的源/目标模式或一致的内容指纹基线。")
    required_confirmations = {
        "arm-receiver": {"receiverPreparationApproved"},
        "start-source": {"receiverReady", "writersPaused"},
        "promote-server": {"promotionApproved", "writersPaused", "peerStageVerified"},
        "promote-primary": {"promotionApproved", "writersPaused", "peerStageVerified"},
    }[action]
    if not isinstance(confirmations, dict) or any(confirmations.get(key) is not True for key in required_confirmations):
        raise SetupError("onboarding-operation-confirmation-required", "待执行操作缺少必需的本阶段确认；未解除暂停。")
    operation_id = str(pending["operationId"]) if isinstance(pending, dict) else str(uuid.uuid4())
    previous_status = _ONBOARDING_OPERATION_START[(role, action)]
    attempt_time = datetime.now(timezone.utc).isoformat()
    pending_operation = {
        "operationId": operation_id,
        "action": action,
        "phase": "mutating",
        "role": role,
        "syncthingDeviceId": syncthing_device_id,
        "peerSyncthingDeviceId": peer_syncthing_device_id,
        "vaultPath": vault_path,
        "folderId": FOLDER_ID,
        "expectedFolderType": expected_folder_type,
        "sourceFolderType": source_folder_type,
        "targetFolderType": expected_folder_type,
        "baselineManifestSha256": baseline_manifest_sha256.lower() if baseline_manifest_sha256 else None,
        "peerManifestSha256": peer_manifest_sha256.lower() if peer_manifest_sha256 else None,
        "previousStatus": previous_status,
        "backupPath": backup_path,
        "requiredConfirmations": dict(confirmations),
        "startedAt": pending.get("startedAt", attempt_time) if isinstance(pending, dict) else attempt_time,
        "lastAttemptAt": attempt_time,
        "containment": None,
    }
    if committed_recovery:
        pending_operation.update({
            "completionCommitUncertain": True,
            "committedStatus": _ONBOARDING_OPERATION_COMPLETION[(role, action)],
        })
    updated = dict(current)
    updated.update({
        "schemaVersion": 1,
        "role": role,
        "folderId": FOLDER_ID,
        "syncthingDeviceId": syncthing_device_id,
        "peerSyncthingDeviceId": peer_syncthing_device_id,
        "pendingOperation": pending_operation,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    })
    result = _write_sync_onboarding_snapshot(codex_home, path, snapshot, updated)
    result.update({"operationId": operation_id, "pendingOperation": pending_operation})
    return result


def hold_sync_onboarding_operation(
    codex_home: Path,
    role: str,
    operation_id: str,
    containment: dict[str, Any],
    *,
    pending_operation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path, snapshot, current = _read_sync_onboarding_state(codex_home, role)
    pending = current.get("pendingOperation")
    if isinstance(pending, dict) and pending.get("operationId") == operation_id:
        updated_pending = dict(pending)
    elif pending is None and isinstance(pending_operation, dict):
        action = pending_operation.get("action")
        expected_completion = _ONBOARDING_OPERATION_COMPLETION.get((role, action))
        expected_start = _ONBOARDING_OPERATION_START.get((role, action))
        current_device = current.get("syncthingDeviceId")
        operation_device = pending_operation.get("syncthingDeviceId")
        current_peer = current.get("peerSyncthingDeviceId")
        operation_peer = pending_operation.get("peerSyncthingDeviceId")
        if (pending_operation.get("operationId") != operation_id
                or pending_operation.get("role") != role
                or pending_operation.get("phase") != "mutating"
                or expected_completion is None or expected_start is None
                or pending_operation.get("previousStatus") != expected_start
                or pending_operation.get("folderId") != FOLDER_ID
                or current.get("status") != expected_completion
                or current.get("role") != role or current.get("folderId") != FOLDER_ID
                or not isinstance(current_device, str) or not isinstance(operation_device, str)
                or _normalized_device_id(current_device) != _normalized_device_id(operation_device)
                or not isinstance(current_peer, str) or not isinstance(operation_peer, str)
                or _normalized_device_id(current_peer) != _normalized_device_id(operation_peer)):
            raise SetupError("onboarding-operation-drift", "完成阶段虽已可见但缺少匹配的操作记录；不回退阶段也不覆盖状态。")
        updated_pending = dict(pending_operation)
        updated_pending.update({
            "completionCommitUncertain": True,
            "committedStatus": expected_completion,
        })
    else:
        raise SetupError("onboarding-operation-drift", "待恢复操作标记在处理期间发生变化；未覆盖。")
    updated_pending.update({
        "phase": "held",
        "containment": containment,
        "heldAt": datetime.now(timezone.utc).isoformat(),
    })
    updated = dict(current)
    updated["pendingOperation"] = updated_pending
    updated["updatedAt"] = datetime.now(timezone.utc).isoformat()
    return _write_sync_onboarding_snapshot(codex_home, path, snapshot, updated)


def complete_sync_onboarding_operation(
    codex_home: Path,
    role: str,
    operation_id: str,
    status: str,
) -> dict[str, Any]:
    if status not in _ONBOARDING_STAGE_ORDER.get(role, {}):
        raise SetupError("onboarding-state-invalid", "第二大脑同步引导完成状态无效。")
    path, snapshot, current = _read_sync_onboarding_state(codex_home, role)
    pending = current.get("pendingOperation")
    if not isinstance(pending, dict) or pending.get("operationId") != operation_id or pending.get("phase") != "mutating":
        raise SetupError("onboarding-operation-drift", "待恢复操作标记与当前操作不一致；未清除。")
    expected_completion = _ONBOARDING_OPERATION_COMPLETION
    if expected_completion.get((role, pending.get("action"))) != status:
        raise SetupError("onboarding-operation-state-conflict", "完成阶段与已持久化操作不匹配；未清除待执行标记。")
    expected_start = _ONBOARDING_OPERATION_START[(role, str(pending.get("action")))]
    commit_recovery = pending.get("completionCommitUncertain") is True
    if (pending.get("previousStatus") != expected_start
            or (commit_recovery and (pending.get("committedStatus") != status or current.get("status") != status))
            or (not commit_recovery and current.get("status") != expected_start)):
        raise SetupError("onboarding-operation-state-conflict", "操作原阶段/待恢复完成阶段与当前状态不一致；未清除待执行标记。")
    stage_order = _ONBOARDING_STAGE_ORDER[role]
    if stage_order.get(status, -1) < stage_order.get(str(current.get("status")), -1):
        raise SetupError("onboarding-state-regression", "同步引导阶段不能回退；未清除待执行标记。")
    updated = dict(current)
    updated["status"] = status
    updated.pop("pendingOperation", None)
    updated["updatedAt"] = datetime.now(timezone.utc).isoformat()
    result = _write_sync_onboarding_snapshot(codex_home, path, snapshot, updated)
    result["status"] = status
    return result


def create_fresh_profile(executable: Path, profile: Path, vault: Path) -> dict[str, Any]:
    if profile.exists():
        raise SetupError("profile-exists", "Syncthing 配置目录已存在；不会覆盖或初始化。")
    profile.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".syncthing-profile-stage-", dir=profile.parent) as temp_root:
        stage_profile = Path(temp_root) / "profile"
        result = run([str(executable), "generate", f"--home={stage_profile}"], timeout=45)
        if result.returncode != 0 or not (stage_profile / "config.xml").exists():
            raise SetupError("profile-generate-failed", "Syncthing 无法在隔离目录生成本机密钥和初始配置。")
        root = inspect_xml(stage_profile / "config.xml")
        local_state = device_and_folder_state(root, vault)
        verify_local_device_identity(executable, stage_profile, local_state["localDeviceId"])
        state = patch_config(root, vault, fresh=True)
        write_atomic(stage_profile / "config.xml", serialize_config(root))
        _install_staged_profile_create_only(stage_profile, profile)
    state["freshProfile"] = True
    return state


def apply_setup(
    codex_home: Path,
    lock_path: Path,
    supplied_vault: str | None,
    *,
    role: str = "primary",
    create_empty_vault_confirmed: bool = False,
) -> dict[str, Any]:
    _PROGRESS.clear()
    _PROGRESS.update({"phase": "preflight", "completed": [], "backupPath": None})
    plan = preflight(codex_home, lock_path, supplied_vault, role=role)
    _PROGRESS["completed"].append("本机路径、配置与冲突预检通过")
    if plan.get("syncOnboarding", {}).get("pendingOperation") is not None:
        raise SetupError("onboarding-operation-pending", "存在未完成的 Syncthing 操作；本机 setup 不会绕过 HOLD 或重新配置 profile。")
    if plan.get("syncOnboarding", {}).get("pairedProfile") is True:
        profile_state = plan["syncthing"].get("profileState") or {}
        stage = str(plan.get("syncOnboarding", {}).get("status") or "unknown")
        sync_paused = profile_state.get("folderPaused") is True or profile_state.get("peerPaused") is True
        if stage == "active":
            result_status = "active-sync-paused-no-changes" if sync_paused else "already-active-no-changes"
        else:
            result_status = "existing-pair-paused-no-changes" if sync_paused else "existing-pair-no-changes"
        return {
            "status": result_status,
            "packageVersion": plan["packageVersion"],
            "role": role,
            "onboardingStatus": stage,
            "vaultPath": plan["vault"]["path"],
            "syncthingVersion": plan["syncthing"].get("version"),
            "syncthingExecutable": plan["syncthing"].get("executable"),
            "syncthingProfile": plan["syncthing"]["profilePath"],
            "syncthingDeviceId": profile_state.get("localDeviceId"),
            "peerSyncthingDeviceId": profile_state.get("peerDeviceId"),
            "folderId": profile_state.get("folderId"),
            "folderType": profile_state.get("folderType"),
            "folderPaused": profile_state.get("folderPaused"),
            "peerPaused": profile_state.get("peerPaused"),
            "remoteDeviceCount": profile_state.get("remoteDeviceCount"),
            "network": profile_state.get("network"),
            "listenAddress": profile_state.get("listenAddress"),
            "guiAddress": profile_state.get("guiAddress"),
            "networkPolicyVerified": True,
            "ignoreRulesMissing": plan["ignore"].get("rulesToAdd", []),
            "startup": plan["startup"],
            "backgroundProcessObserved": plan["syncthing"].get("running") is True,
            "configurationModified": False,
            "onboardingStageAdvanced": False,
            "crossDeviceSyncVerified": False,
            "note": f"仅只读核验并保留已记录阶段 {stage} 的双机 profile；未应用首次安装默认值、改变暂停状态、启动/停止服务、改写 .stignore 或推进阶段。实时连接和跨设备内容状态未验证。",
        }
    vault = Path(plan["vault"]["path"])
    vault_expected_missing = not bool(plan["vault"]["exists"])
    if vault_expected_missing and (role != "server" or not create_empty_vault_confirmed):
        raise SetupError("server-vault-confirmation-required", "服务器 Vault 目录不存在；需先展示精确路径并取得用户确认后再创建。")
    device_path = Path(plan["deviceConfig"]["path"])
    profile = Path(plan["syncthing"]["profilePath"])
    assert_safe_syncthing_environment(discover_startup_entries())
    running_after_preflight = discover_running()
    matching_after_preflight = [
        item for item in running_after_preflight if process_targets_profile(item, profile)
    ]
    if len(matching_after_preflight) > 1 or any(
        not startup_is_safe(item, profile) for item in matching_after_preflight
    ):
        raise SetupError("running-process-conflict", "预检后发现重复或不安全的 Syncthing 进程，未修改任何配置。")
    if not plan["syncthing"]["running"] and matching_after_preflight:
        raise SetupError("running-process-appeared", "Syncthing 在预检后启动；为避免离线配置冲突，未进行任何写入。")
    profile_path = profile / "config.xml"
    ignore_path = Path(plan["ignore"]["path"])
    device_snapshot = snapshot_file(device_path, "第二大脑设备配置")
    expected_device_hash = plan["deviceConfig"].get("snapshotSha256")
    actual_device_hash = hashlib.sha256(device_snapshot).hexdigest() if device_snapshot is not None else None
    if actual_device_hash != expected_device_hash:
        raise SetupError(
            "preflight-input-changed",
            "第二大脑设备配置在预检后发生变化；Vault 目标可能已变更，因此停止所有 Syncthing 写入。",
        )
    ignore_snapshot = snapshot_file(ignore_path, "Vault 根目录 .stignore")
    profile_snapshot = snapshot_file(profile_path, "Syncthing config.xml")
    try:
        original_device = json.loads(device_snapshot.decode("utf-8")) if device_snapshot is not None else {}
    except (UnicodeError, ValueError) as exc:
        raise SetupError("device-config-invalid", "第二大脑设备配置在预检后发生变化，未修改。") from exc
    if not isinstance(original_device, dict):
        raise SetupError("device-config-invalid", "第二大脑设备配置在预检后格式发生变化，未修改。")
    device_data = dict(original_device)
    device_data.setdefault("schemaVersion", 2)
    if not isinstance(device_data.get("deviceId"), str) or not device_data.get("deviceId", "").strip():
        device_data["deviceId"] = str(uuid.uuid4())
    if not isinstance(device_data.get("deviceLabel"), str) or not device_data.get("deviceLabel", "").strip():
        device_data["deviceLabel"] = socket.gethostname()
    device_data["vaultPath"] = str(vault)
    device_data.setdefault("syncMode", "syncthing")
    device_data.setdefault("backupMode", "github-manual")
    expected_backup_role = role == "primary"
    existing_backup_role = original_device.get("gitBackupDevice")
    if type(existing_backup_role) is bool and existing_backup_role != expected_backup_role:
        raise SetupError("backup-role-conflict", "现有设备配置的 GitHub 备份角色与本次确认的 primary/server 角色冲突；未修改。")
    device_data["gitBackupDevice"] = expected_backup_role
    device_data.setdefault("writePolicy", "tiered")
    device_data.setdefault("weeklyAutomationId", None)

    ignore_path, ignore_text, ignore_added, _ = prepare_ignore(vault)
    exe = Path(plan["syncthing"]["executable"]) if plan["syncthing"]["executable"] else None
    if exe is None:
        _PROGRESS["phase"] = "install-syncthing"
        _, lock = load_lock(lock_path)
        exe = install_syncthing(lock, plan["platform"])
        version_text, _ = syncthing_version(exe)
        _PROGRESS["completed"].append("已安装并校验锁定的 Syncthing 程序")
    else:
        version_text, _ = syncthing_version(exe)
        _PROGRESS["completed"].append("已复用现有 Syncthing 程序")

    profile_state: dict[str, Any]
    _PROGRESS["phase"] = "configure-profile"
    if profile_snapshot is None:
        profile_state = create_fresh_profile(exe, profile, vault)
        _PROGRESS["completed"].append("已创建新的本机 Syncthing profile")
    else:
        root = inspect_xml(profile_path)
        local_state = device_and_folder_state(root, vault)
        verify_local_device_identity(exe, profile, local_state["localDeviceId"])
        profile_state = patch_config(root, vault)
        _PROGRESS["completed"].append("已计算本机 Syncthing profile 增量配置")

    entries = discover_startup_entries()
    running = discover_running()
    matching_processes = [item for item in running if process_targets_profile(item, profile)]
    if len(matching_processes) > 1 or any(
        not startup_is_safe(item, profile) for item in matching_processes
    ):
        raise SetupError("running-process-conflict", "写入前发现重复或不安全的 Syncthing 进程，未修改启动项。")
    if not plan["syncthing"]["running"] and matching_processes:
        raise SetupError("running-process-appeared", "Syncthing 在预检后启动；为避免并发覆盖，未进行后续写入。")
    if matching_processes and profile_state.get("changed"):
        raise SetupError("running-profile-needs-change", "Syncthing 已运行且 profile 需要改动；为避免并发覆盖，未写入。")
    startup_entry = startup_for_profile(entries, profile)
    if startup_entry and startup_entry.kind != "process" and not startup_is_safe(startup_entry, profile):
        raise SetupError("startup-conflict", "发现不安全的已有自启动项；配置文件可能已备份，未修改启动项。")

    targets: list[tuple[Path, str]] = []
    if device_data != original_device:
        targets.append((device_path, "device/config.json"))
    if ignore_text.encode("utf-8") != (ignore_snapshot if ignore_snapshot is not None else b""):
        targets.append((ignore_path, "vault/.stignore"))
    if profile_snapshot is not None and profile_state.get("changed"):
        targets.append((profile_path, "syncthing/config.xml"))

    if snapshot_file(device_path, "第二大脑设备配置") != device_snapshot:
        raise SetupError("concurrent-file-change", "设备配置在预检后发生变化，未覆盖。")
    if snapshot_file(ignore_path, "Vault 根目录 .stignore") != ignore_snapshot:
        raise SetupError("concurrent-file-change", ".stignore 在预检后发生变化，未覆盖。")
    if profile_snapshot is not None and snapshot_file(profile_path, "Syncthing config.xml") != profile_snapshot:
        raise SetupError("concurrent-file-change", "Syncthing 配置在预检后发生变化，未覆盖。")
    backup_path = backup_targets(codex_home, targets)
    _PROGRESS["backupPath"] = backup_path
    if backup_path:
        _PROGRESS["completed"].append("已备份所有将要修改的既有文件")

    vault_created = _create_confirmed_empty_vault(
        vault,
        create_empty_vault_confirmed,
        role,
        expected_missing=vault_expected_missing,
    )
    if vault_created:
        _PROGRESS["completed"].append("已在确认路径创建空的服务器 Vault 接收目录")

    expected_device = device_snapshot
    device_bytes = (json.dumps(device_data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if device_data != original_device:
        _PROGRESS["phase"] = "write-device-config"
        write_atomic(device_path, device_bytes, expected_current=device_snapshot)
        expected_device = device_bytes
        _PROGRESS["completed"].append("已写入第二大脑设备配置")

    ignore_bytes = ignore_text.encode("utf-8")
    expected_ignore = ignore_snapshot
    if ignore_bytes != (ignore_snapshot if ignore_snapshot is not None else b""):
        _PROGRESS["phase"] = "write-stignore"
        write_atomic(ignore_path, ignore_bytes, expected_current=ignore_snapshot)
        expected_ignore = ignore_bytes
        _PROGRESS["completed"].append("已安全合并 Vault 根目录 .stignore")

    expected_profile = profile_snapshot
    if profile_snapshot is None:
        expected_profile = snapshot_file(profile_path, "新建的 Syncthing config.xml")
    elif profile_state.get("changed"):
        _PROGRESS["phase"] = "write-syncthing-profile"
        root = inspect_xml(profile_path)
        rechecked = patch_config(root, vault)
        if not rechecked.get("changed"):
            profile_state = rechecked
        else:
            config_bytes = serialize_config(root)
            write_atomic(profile_path, config_bytes, expected_current=profile_snapshot)
            expected_profile = config_bytes
            profile_state = rechecked
            _PROGRESS["completed"].append("已写入 Syncthing 本机网络与暂停文件夹配置")

    if snapshot_file(device_path, "第二大脑设备配置") != expected_device:
        raise SetupError("concurrent-file-change", "设备配置在写入后发生变化，停止启动 Syncthing。")
    if snapshot_file(ignore_path, "Vault 根目录 .stignore") != expected_ignore:
        raise SetupError("concurrent-file-change", ".stignore 在写入后发生变化，停止启动 Syncthing。")
    if snapshot_file(profile_path, "Syncthing config.xml") != expected_profile:
        raise SetupError("concurrent-file-change", "Syncthing 配置在写入后发生变化，停止启动。")

    assert_safe_syncthing_environment(discover_startup_entries())
    _PROGRESS["phase"] = "register-startup"
    startup_report = register_startup(exe, profile, startup_entry)
    verified_startup = startup_for_profile(discover_startup_entries(), profile)
    if not verified_startup or not verified_startup.enabled or not startup_is_safe(verified_startup, profile):
        raise SetupError("startup-verification-failed", "无法验证登录启动项已注册且包含无浏览器参数。")
    startup_report["noBrowser"] = True
    _PROGRESS["completed"].append("已验证用户登录后台启动项与无浏览器参数")
    running_after_registration = discover_running()
    active_processes = [item for item in running_after_registration if process_targets_profile(item, profile)]
    if len(active_processes) > 1 or any(not startup_is_safe(item, profile) for item in active_processes):
        raise SetupError("running-process-conflict", "启动阶段发现重复或不安全的 Syncthing 进程，未继续启动。")
    already_running = bool(active_processes)
    if not already_running:
        _PROGRESS["phase"] = "start-background-process"
        assert_safe_syncthing_environment(discover_startup_entries())
        launch_existing_startup(verified_startup, exe, profile)
    runtime_running = wait_for_runtime(profile, exe)
    if not runtime_running:
        raise SetupError("runtime-not-running", "登录启动项已配置，但未能验证 Syncthing 后台进程。")

    final_root = inspect_xml(profile_path)
    final_state = validate_profile(final_root, vault)
    if not final_state["compliant"]:
        raise SetupError("verification-failed", "Syncthing 最终配置未通过本机安全基线验证。")
    _PROGRESS["completed"].append("已验证 profile、loopback 网络设置和 Vault 文件夹暂停状态")
    final_ignore, _, remaining, _ = prepare_ignore(vault)
    if remaining:
        raise SetupError("ignore-verification-failed", ".stignore 忽略规则未能完整验证。")
    _PROGRESS["completed"].append("已验证忽略规则与后台进程")
    _PROGRESS["phase"] = "verify-runtime"
    runtime_state = runtime_api_state(profile, vault)
    verify_runtime_state(runtime_state)
    onboarding_state = write_sync_onboarding_state(
        codex_home, role, "local-prepared", syncthing_device_id=final_state["localDeviceId"]
    )
    _PROGRESS["phase"] = "complete"
    _PROGRESS["completed"].append("本机配置与运行状态验证完成；跨设备同步尚未验证")

    return {
        "status": "configured",
        "packageVersion": plan["packageVersion"],
        "syncthingVersion": version_text,
        "syncthingExecutable": str(exe),
        "syncthingProfile": str(profile),
        "syncthingDeviceId": final_state["localDeviceId"],
        "vaultPath": str(vault),
        "deviceConfigPath": str(device_path),
        "role": role,
        "gitBackupDevice": device_data["gitBackupDevice"],
        "syncOnboardingState": onboarding_state,
        "folderId": final_state["folderId"],
        "folderPaused": final_state["folderPaused"],
        "remoteDeviceCount": final_state["remoteDeviceCount"],
        "network": final_state["network"],
        "listenAddress": final_state["listenAddress"],
        "guiAddress": final_state["guiAddress"],
        "ignoreRules": list(IGNORE_RULES),
        "ignoreRulesAdded": ignore_added,
        "startup": startup_report,
        "browserAutoOpen": False,
        "backgroundProcessVerified": runtime_running,
        "runtimeStatus": runtime_state,
        "backupPath": backup_path,
        "crossDeviceSyncVerified": False,
        "note": "没有添加远端设备；跨设备连接和实际文件传输尚未验证。",
        "progress": dict(_PROGRESS),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Codex-invoked local Syncthing bootstrap")
    parser.add_argument("action", choices=("preflight", "begin", "apply"))
    parser.add_argument("--codex-home")
    parser.add_argument("--vault-path")
    parser.add_argument("--role", choices=("primary", "server"), default="primary")
    parser.add_argument("--create-empty-vault-confirmed", action="store_true")
    args = parser.parse_args()
    codex_home = codex_home_from(args.codex_home)
    lock_path = LOCK_FILE
    try:
        if args.action == "preflight":
            emit(preflight(codex_home, lock_path, args.vault_path, role=args.role))
        if args.action == "begin":
            plan = preflight(codex_home, lock_path, args.vault_path, role=args.role)
            state = write_sync_onboarding_state(codex_home, args.role, "local-prepared")
            paused = state["status"] != "active"
            note = "引导状态已先行写入；全局第二大脑自动维护保持暂停，直到双机验证完成。" if paused else "本机已有 active 双机状态；按单调状态规则保留，不自动降级或暂停既有维护。"
            emit({"status": "onboarding-begun", "role": args.role, "vaultPath": plan["vault"]["path"], "onboardingState": state, "maintenancePaused": paused, "note": note})
        emit(apply_setup(
            codex_home,
            lock_path,
            args.vault_path,
            role=args.role,
            create_empty_vault_confirmed=args.create_empty_vault_confirmed,
        ))
    except SetupError as exc:
        emit(
            {
                "status": "blocked",
                "code": exc.code,
                "message": str(exc),
                "installerWritesStopped": True,
                "containmentStatus": "not-attempted",
                "containmentVerified": False,
                "syncthingChangesStopped": None,
                "otherSelectedPackInstallsMayContinue": True,
                "progress": {
                    "phase": _PROGRESS.get("phase"),
                    "completed": list(_PROGRESS.get("completed", [])),
                    "backupPath": _PROGRESS.get("backupPath"),
                } if args.action == "apply" else None,
            },
            2,
        )
    except OSError as exc:
        emit(
            {
                "status": "blocked",
                "code": "filesystem-operation-failed",
                "message": f"本机文件操作失败（{exc.strerror or type(exc).__name__}）；保留备份和已完成步骤。",
                "installerWritesStopped": True,
                "containmentStatus": "not-attempted",
                "containmentVerified": False,
                "syncthingChangesStopped": None,
                "otherSelectedPackInstallsMayContinue": True,
                "progress": {
                    "phase": _PROGRESS.get("phase"),
                    "completed": list(_PROGRESS.get("completed", [])),
                    "backupPath": _PROGRESS.get("backupPath"),
                } if args.action == "apply" else None,
            },
            2,
        )


if __name__ == "__main__":
    main()
