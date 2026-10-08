#!/usr/bin/env python3
"""Codex-invoked, safety-gated Syncthing pairing for the Second Brain Vault.

This program is called by the installed Skill, not exposed as a user-run installer.
It only talks to the local Syncthing REST API and never contacts SSH or GitHub.
"""

from __future__ import annotations

import argparse
import copy
import functools
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.error import HTTPError
from urllib.request import Request

import setup_syncthing as base


FOLDER_ID = base.FOLDER_ID
FOLDER_LABEL = base.FOLDER_LABEL
LOOPBACK_LISTENER = "tcp://127.0.0.1:22000"
RELAY_LISTENER = "dynamic+https://relays.syncthing.net/endpoint"
EXPECTED_LISTENERS = [LOOPBACK_LISTENER, RELAY_LISTENER]
MANIFEST_IGNORES = {".git", ".claudian", ".stignore", ".stfolder"}
MANAGED_WORKSPACE_PREFIX = "workspace"
DEVICE_ID_RE = re.compile(r"^(?:[A-Z2-7]{7}-){7}[A-Z2-7]{7}$")
_PROGRESS: dict[str, Any] = {"phase": "idle", "completed": [], "backupPath": None}
_MUTATING_ACTIONS = {"pair", "arm-receiver", "start-source", "verify-seed", "promote-server", "promote-primary", "complete", "pause"}


class PairingError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@contextmanager
def _transition_lock(profile: Path):
    if profile.is_symlink() or not profile.is_dir():
        raise PairingError("transition-lock-conflict", "Syncthing profile 不存在、不是普通目录或为符号链接；拒绝并行修改。")
    profile = profile.resolve()
    lock_path = profile / "codex-second-brain-transition.lock"
    if lock_path.is_symlink() or (lock_path.exists() and not lock_path.is_file()):
        raise PairingError("transition-lock-conflict", "Syncthing profile 锁文件不是普通文件；拒绝并行修改。")
    try:
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(lock_path, flags, 0o600)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise PairingError("transition-lock-conflict", "同步状态锁目标不是普通文件；拒绝并行修改。")
        stream = os.fdopen(descriptor, "r+b")
    except OSError as exc:
        raise PairingError("transition-lock-unavailable", "无法锁定 Syncthing profile；未修改配置。") from exc
    locked = False
    try:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except (OSError, BlockingIOError) as exc:
            raise PairingError("transition-in-progress", "另一条 Codex 对话正在修改本机同步状态；请等待后重试。") from exc
        yield
    finally:
        if locked:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        stream.close()


def _serialized_transition(function):
    @functools.wraps(function)
    def wrapped(args: argparse.Namespace, codex_home: Path, *values: Any, **options: Any):
        api = next((value for value in reversed(values) if isinstance(getattr(value, "profile", None), Path)), None)
        if api is None:
            raise PairingError("transition-lock-unavailable", "无法从本次操作定位 Syncthing profile；未修改配置。")
        vault = values[0] if values and isinstance(values[0], Path) else None
        if vault is None:
            raise PairingError("transition-lock-unavailable", "无法定位本次同步操作的 Vault；未修改配置。")
        with _transition_lock(api.profile):
            _contain_pending_before_mutation(args, codex_home, vault, api)
            return function(args, codex_home, *values, **options)
    return wrapped


class LocalSyncthingAPI:
    def __init__(self, profile: Path):
        self.profile = profile
        root = base.inspect_xml(profile / "config.xml")
        gui = base._xml_local(root, "gui")
        if gui is None:
            raise PairingError("gui-config-missing", "Syncthing 本机 GUI/API 配置缺失。")
        addresses = [node for node in list(gui) if base._xml_name(node) == "address"]
        if len(addresses) != 1:
            raise PairingError("gui-address-ambiguous", "Syncthing 本机 API 地址不唯一。")
        address = (addresses[0].text or "").strip()
        host, separator, port_text = address.rpartition(":")
        if not separator or host != "127.0.0.1" or not port_text.isdigit():
            raise PairingError("gui-not-loopback", "拒绝连接非 loopback 的 Syncthing 管理 API。")
        port = int(port_text)
        if not 1 <= port <= 65535:
            raise PairingError("gui-address-invalid", "Syncthing 本机 API 端口无效。")
        self.api_key = base._xml_text(gui, "apikey", "")
        if not self.api_key:
            raise PairingError("api-key-missing", "Syncthing 本机 API key 缺失。")
        self.scheme = "https" if gui.get("tls", "false").lower() == "true" else "http"
        self.origin = f"{self.scheme}://127.0.0.1:{port}"
        self.opener = base.build_local_api_opener(tls=self.scheme == "https")

    def request(self, method: str, path: str, payload: Any = None) -> Any:
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"X-API-Key": self.api_key, "User-Agent": base.USER_AGENT}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = Request(f"{self.origin}{path}", data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=8) as response:
                body = response.read()
        except HTTPError as exc:
            # Never include request headers, response bodies, or API credentials in errors.
            raise PairingError("syncthing-api-error", f"Syncthing 本机 API 返回 HTTP {exc.code}。") from exc
        except Exception as exc:
            raise PairingError("syncthing-api-unavailable", "无法访问本机 Syncthing API；未尝试改写 config.xml。") from exc
        if not body:
            return None
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeError, ValueError) as exc:
            raise PairingError("syncthing-api-invalid", "Syncthing 本机 API 返回了无法解析的数据。") from exc


def _codex_home(value: str | None) -> Path:
    return base.codex_home_from(value)


def _profile() -> tuple[Path, Path]:
    entries = base.discover_startup_entries()
    base.assert_safe_syncthing_environment(entries)
    running = base.discover_running()
    all_entries = entries + running
    profile = base.profile_dir_for(all_entries)
    matched = [item for item in running if base.process_targets_profile(item, profile)]
    if len(matched) != 1:
        raise PairingError("syncthing-not-running", "未能唯一识别正在运行的 Syncthing profile。")
    if not base.startup_is_safe(matched[0], profile):
        raise PairingError("syncthing-process-conflict", "Syncthing 运行参数不符合安全基线，未修改。")
    if not (profile / "config.xml").is_file():
        raise PairingError("syncthing-profile-missing", "目标 Syncthing profile 中没有 config.xml。")
    return profile.resolve(), Path(matched[0].executable).resolve()


def _read_device_config(codex_home: Path, vault: Path, role: str) -> dict[str, Any]:
    path = codex_home / base.DEVICE_CONFIG_RELATIVE
    if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
        raise PairingError("device-config-missing", "第二大脑设备配置不存在或不安全；先完成 05 的本机 setup。")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PairingError("device-config-invalid", "第二大脑设备配置无法解析。") from exc
    if not isinstance(value, dict) or value.get("schemaVersion") != 2:
        raise PairingError("device-config-schema", "需要有效的 Schema 2 设备配置。")
    configured = value.get("vaultPath")
    if not isinstance(configured, str) or not base.same_path(configured, vault):
        raise PairingError("vault-path-conflict", "命令路径与设备配置中的 Vault 路径不一致。")
    expected_backup = role == "primary"
    if type(value.get("gitBackupDevice")) is bool and value["gitBackupDevice"] != expected_backup:
        raise PairingError("backup-role-conflict", "设备配置的 GitHub 备份角色与本次设备角色不符；未修改。")
    return value


def _device_id(api: LocalSyncthingAPI) -> str:
    status = api.request("GET", "/rest/system/status")
    if not isinstance(status, dict) or not isinstance(status.get("myID"), str):
        raise PairingError("device-id-unavailable", "无法从本机 Syncthing API 核验设备 ID。")
    return status["myID"]


def _device_records(api: LocalSyncthingAPI) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    own_id = _device_id(api)
    devices = api.request("GET", "/rest/config/devices")
    folders = api.request("GET", "/rest/config/folders")
    if not isinstance(devices, list) or not isinstance(folders, list):
        raise PairingError("api-config-invalid", "Syncthing 设备或文件夹配置格式无法验证。")
    if any(not isinstance(item, dict) for item in devices + folders):
        raise PairingError("api-config-invalid", "Syncthing 设备或文件夹列表中含无效对象。")
    local = [item for item in devices if item.get("deviceID") and base._normalized_device_id(item["deviceID"]) == base._normalized_device_id(own_id)]
    if len(local) != 1:
        raise PairingError("local-device-ambiguous", "Syncthing 配置中的本机设备 ID 不唯一。")
    return own_id, devices, folders


def _target_folder(folders: list[dict[str, Any]], vault: Path) -> dict[str, Any]:
    matches = [item for item in folders if item.get("id") == FOLDER_ID or (isinstance(item.get("path"), str) and base.same_path(item["path"], vault))]
    if len(matches) != 1:
        raise PairingError("vault-folder-conflict", "固定第二大脑 folder ID 与本机 Vault 路径无法唯一匹配。")
    folder = matches[0]
    if folder.get("id") != FOLDER_ID or not isinstance(folder.get("path"), str) or not base.same_path(folder["path"], vault):
        raise PairingError("vault-folder-conflict", "第二大脑 folder ID 指向其他路径；未修改。")
    return folder


def _peer_device_id(value: str, own_id: str) -> str:
    canonical = value.strip().upper()
    if not DEVICE_ID_RE.fullmatch(canonical):
        raise PairingError("peer-device-id-invalid", "对端 Syncthing Device ID 格式无效。")
    if base._normalized_device_id(canonical) == base._normalized_device_id(own_id):
        raise PairingError("peer-device-id-self", "对端 Device ID 与本机相同。")
    return canonical


def _peer_label(value: str) -> str:
    label = value.strip()
    if not label or len(label) > 80 or any(ord(char) < 32 for char in label):
        raise PairingError("peer-label-invalid", "对端设备标签为空、过长或含控制字符。")
    return label


def _backup_config(codex_home: Path, profile: Path, vault: Path) -> Path:
    config = profile / "config.xml"
    if config.is_symlink() or not config.is_file():
        raise PairingError("profile-config-conflict", "Syncthing config.xml 不是普通文件，无法安全备份。")
    second_brain = codex_home / "second-brain"
    parent = second_brain / "backups"
    if second_brain.is_symlink() or parent.is_symlink():
        raise PairingError("backup-path-conflict", "Syncthing 配置备份路径包含符号链接；拒绝复制可能含 API key 的配置。")
    if second_brain.exists() and not second_brain.is_dir():
        raise PairingError("backup-path-conflict", "第二大脑状态路径不是目录；拒绝复制 Syncthing 配置。")
    if parent.exists() and not parent.is_dir():
        raise PairingError("backup-path-conflict", "Syncthing 配置备份路径不是目录；拒绝写入。")
    def validate_backup_parent(candidate: Path) -> None:
        resolved = candidate.resolve()
        if (base.is_within_path(resolved, vault)
                or base.is_inside_git_repository(resolved)
                or base.is_within_path(resolved, base.PACK_ROOT)):
            raise PairingError("backup-path-conflict", "Syncthing 配置备份位置位于 Vault、Git 仓库或懒人包源码内；拒绝复制含 API key 的配置。")
    validate_backup_parent(parent)
    parent.mkdir(parents=True, exist_ok=True)
    validate_backup_parent(parent)
    try:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        for suffix in range(1000):
            name = f"{stamp}-syncthing-pairing" if suffix == 0 else f"{stamp}-syncthing-pairing-{suffix}"
            destination = parent / name
            try:
                destination.mkdir(mode=0o700, exist_ok=False)
                break
            except FileExistsError:
                continue
        else:
            raise FileExistsError("unable to allocate a unique backup directory")
        backup = destination / "config.xml"
        shutil.copy2(config, backup)
        if os.name != "nt":
            os.chmod(backup, stat.S_IRUSR | stat.S_IWUSR)
    except OSError as exc:
        raise PairingError("backup-failed", "Syncthing 配置备份失败；没有开始配对修改。") from exc
    return backup


def _ensure_only_expected_peer(devices: list[dict[str, Any]], own_id: str, peer_id: str | None = None) -> list[dict[str, Any]]:
    own_norm = base._normalized_device_id(own_id)
    peer_norm = base._normalized_device_id(peer_id) if peer_id else None
    remotes = [item for item in devices if base._normalized_device_id(str(item.get("deviceID", ""))) != own_norm]
    unexpected = [item for item in remotes if peer_norm is None or base._normalized_device_id(str(item.get("deviceID", ""))) != peer_norm]
    if unexpected:
        raise PairingError("unknown-remote-device", "发现未在本次配对卡中确认的 Syncthing 设备；未修改。")
    if len(remotes) > 1:
        raise PairingError("multiple-remote-devices", "发现多个远端设备；当前双设备方案停止相关写入。")
    return remotes


def _onboarding_state(codex_home: Path, role: str) -> dict[str, Any]:
    path = codex_home / base.SYNC_ONBOARDING_RELATIVE
    if path.is_symlink() or not path.is_file():
        raise PairingError("onboarding-state-missing", "缺少安全引导状态；先完成本机 setup。")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PairingError("onboarding-state-invalid", "同步引导状态无法解析；未修改。") from exc
    valid_stages = base._ONBOARDING_STAGE_ORDER.get(role, {})
    if not isinstance(value, dict) or value.get("schemaVersion") != 1 or value.get("role") != role or value.get("status") not in valid_stages:
        raise PairingError("onboarding-state-invalid", "同步引导状态版本、设备角色或阶段不匹配。")
    return value


def _known_remote_devices(codex_home: Path, role: str, devices: list[dict[str, Any]], own_id: str) -> list[dict[str, Any]]:
    state = _onboarding_state(codex_home, role)
    expected = state.get("peerSyncthingDeviceId")
    if expected:
        remotes = _ensure_only_expected_peer(devices, own_id, expected)
        if len(remotes) != 1 or base._normalized_device_id(str(remotes[0].get("deviceID", ""))) != base._normalized_device_id(expected):
            raise PairingError("peer-identity-drift", "Syncthing 当前远端设备与本机引导状态绑定的配对卡不一致。")
        return remotes
    remotes = _ensure_only_expected_peer(devices, own_id)
    if remotes:
        raise PairingError("unknown-remote-device", "存在远端设备但本机引导状态未记录其配对卡；停止而不猜测。")
    return remotes


def _folder_member_ids(folder: dict[str, Any]) -> list[str]:
    members = folder.get("devices")
    if not isinstance(members, list):
        raise PairingError("folder-members-invalid", "目标 Vault 文件夹的设备列表无法验证。")
    values: list[str] = []
    for member in members:
        if not isinstance(member, dict) or not isinstance(member.get("deviceID"), str):
            raise PairingError("folder-members-invalid", "目标 Vault 文件夹的设备列表含无效成员。")
        device_id = member["deviceID"].strip().upper()
        if not DEVICE_ID_RE.fullmatch(device_id):
            raise PairingError("folder-member-id-invalid", "目标 Vault 文件夹含格式无效的设备 ID。")
        values.append(base._normalized_device_id(device_id))
    if len(values) != len(set(values)):
        raise PairingError("folder-members-duplicate", "目标 Vault 文件夹含重复设备成员。")
    return values


def _backup_role(codex_home: Path, role: str) -> None:
    config = _read_device_config(codex_home, Path(json.loads((codex_home / base.DEVICE_CONFIG_RELATIVE).read_text(encoding="utf-8"))["vaultPath"]), role)
    if config.get("gitBackupDevice") is not (role == "primary"):
        raise PairingError("backup-role-missing", "设备配置没有记录对应的 GitHub 备份角色；先完成 setup。")


@_serialized_transition
def _pair(args: argparse.Namespace, codex_home: Path, vault: Path, profile: Path, api: LocalSyncthingAPI) -> dict[str, Any]:
    role = args.role
    _assert_no_pending_operation(codex_home, role)
    if role not in {"primary", "server"}:
        raise PairingError("role-invalid", "配对角色必须是 primary 或 server。")
    if not args.confirmed_network_metadata:
        raise PairingError(
            "network-metadata-consent-required",
            "启用公共设备发现/官方 relay 会处理 Device ID、IP 等连接元数据；说明后需取得用户确认，才可继续配对。",
        )
    _backup_role(codex_home, role)
    own_id, devices, folders = _device_records(api)
    peer_id = _peer_device_id(args.peer_device_id, own_id)
    peer_label = _peer_label(args.peer_label)
    onboarding = _onboarding_state(codex_home, role)
    recorded_peer = onboarding.get("peerSyncthingDeviceId")
    if recorded_peer and base._normalized_device_id(recorded_peer) != base._normalized_device_id(peer_id):
        raise PairingError("peer-identity-drift", "提供的配对卡与本机引导状态中记录的设备 ID 不同。")
    local_id_norm = base._normalized_device_id(own_id)
    peer_id_norm = base._normalized_device_id(peer_id)
    remotes = _ensure_only_expected_peer(devices, own_id, peer_id)
    folder = _target_folder(folders, vault)
    members = _folder_member_ids(folder)
    if local_id_norm not in members:
        raise PairingError("local-folder-membership-missing", "目标 Vault 文件夹未包含本机设备；未修改。")
    for existing_folder in folders:
        if existing_folder.get("id") != FOLDER_ID and peer_id_norm in _folder_member_ids(existing_folder):
            raise PairingError("peer-shares-other-folder", "该远端设备已与本机共享其他文件夹；不扩展其访问范围。")
    expected_type = "sendonly" if role == "primary" else "receiveonly"
    existing_type = folder.get("type")
    if existing_type not in {expected_type, "sendreceive"}:
        raise PairingError("folder-mode-conflict", "目标文件夹现有同步方向与本次播种角色冲突。")
    if remotes:
        if base._normalized_device_id(remotes[0].get("deviceID", "")) != peer_id_norm:
            raise PairingError("unknown-remote-device", "已有远端设备与用户提供的配对卡不一致。")
        if peer_id_norm not in members or existing_type not in {expected_type, "sendreceive"}:
            raise PairingError("pairing-state-conflict", "现有远端设备配置与预期配对状态不一致；未修复或覆盖。")
        if remotes[0].get("introducer") is not False or remotes[0].get("autoAcceptFolders") is not False:
            raise PairingError("pairing-state-conflict", "现有远端设备启用了 introducer 或自动接收文件夹；未覆盖该安全设置。")
        if onboarding.get("status") in {"local-prepared", "paired-paused"} and (
            remotes[0].get("paused") is not True or folder.get("paused") is not True
        ):
            raise PairingError("pairing-state-conflict", "首次配对尚未完成但 folder/设备已解除暂停；保持现状并先检查传输状态。")
        if existing_type == "sendreceive" and onboarding.get("status") not in {"server-promoted", "primary-promoted", "active"}:
            raise PairingError("pairing-state-conflict", "文件夹已进入双向模式但本机引导状态未记录该阶段；不作假设。")
        options = api.request("GET", "/rest/config/options")
        if not isinstance(options, dict):
            raise PairingError("network-options-invalid", "Syncthing 网络配置无法验证。")
        _validate_network_options(options)
        expected_options = {
            "listenAddresses": EXPECTED_LISTENERS,
            "globalAnnounceEnabled": True,
            "localAnnounceEnabled": False,
            "announceLANAddresses": False,
            "relaysEnabled": True,
            "natEnabled": False,
            "startBrowser": False,
        }
        if any(options.get(key) != value for key, value in expected_options.items()):
            raise PairingError("network-policy-conflict", "已配对设备的网络策略与预期不符；未覆盖用户设置。")
        if set(members) != {local_id_norm, peer_id_norm} or len(members) != 2:
            raise PairingError("pairing-state-conflict", "现有 Vault 文件夹包含未确认的设备成员。")
        if _restart_if_required(api, own_id):
            _PROGRESS["completed"].append("Syncthing 已通过本机 API 安全重启并重新核验设备身份")
            options = api.request("GET", "/rest/config/options")
            if not isinstance(options, dict) or any(options.get(key) != value for key, value in expected_options.items()):
                raise PairingError("network-policy-conflict", "Syncthing 重启后网络策略与预期不符；未报告配对完成。")
        onboarding = base.write_sync_onboarding_state(codex_home, role, "paired-paused", peer_syncthing_device_id=peer_id, syncthing_device_id=own_id)
        _PROGRESS["onboardingState"] = onboarding
        return _pair_status(args, own_id, peer_id, folder, options, already=True)
    if folder.get("paused") is not True:
        raise PairingError("folder-not-paused", "新增配对前目标 Vault 文件夹必须暂停。")
    if peer_id_norm in members:
        raise PairingError("folder-peer-without-device", "文件夹引用对端但设备表中没有该设备；未修改。")

    options = api.request("GET", "/rest/config/options")
    _validate_network_options(options)
    backup = _backup_config(codex_home, profile, vault)
    _PROGRESS["backupPath"] = str(backup)
    _PROGRESS["phase"] = "add-peer-device"
    _PROGRESS["completed"].append("已备份修改前的 Syncthing config.xml")

    default_device = api.request("GET", "/rest/config/defaults/device")
    if not isinstance(default_device, dict):
        raise PairingError("device-template-invalid", "Syncthing 没有返回可验证的设备模板。")
    new_device = copy.deepcopy(default_device)
    new_device.update({
        "deviceID": peer_id,
        "name": peer_label,
        "addresses": ["dynamic"],
        "introducer": False,
        "autoAcceptFolders": False,
        "paused": True,
    })
    api.request("POST", "/rest/config/devices", new_device)
    _PROGRESS["completed"].append("已添加唯一指定的远端设备（保持暂停、禁止自动接收文件夹）")

    _PROGRESS["phase"] = "share-paused-vault-folder"
    current_folder = api.request("GET", f"/rest/config/folders/{quote(FOLDER_ID, safe='')}")
    if not isinstance(current_folder, dict) or current_folder.get("id") != FOLDER_ID:
        raise PairingError("folder-reread-failed", "添加设备后无法重新读取目标文件夹；保留已完成步骤和备份。")
    current_members = current_folder.get("devices")
    if not isinstance(current_members, list):
        raise PairingError("folder-members-invalid", "文件夹设备成员格式无法验证；保留已完成步骤和备份。")
    local_member = next((item for item in current_members if isinstance(item, dict) and base._normalized_device_id(str(item.get("deviceID", ""))) == local_id_norm), None)
    if local_member is None or any(not isinstance(item, dict) for item in current_members):
        raise PairingError("folder-members-changed", "文件夹成员在配对过程中发生变化；保留已完成步骤和备份。")
    remote_member = copy.deepcopy(local_member)
    remote_member["deviceID"] = peer_id
    patched_members = current_members + [remote_member]
    api.request("PATCH", f"/rest/config/folders/{quote(FOLDER_ID, safe='')}", {
        "devices": patched_members,
        "type": expected_type,
        "paused": True,
    })
    _PROGRESS["completed"].append(f"已将目标文件夹设为 {expected_type} 并保持暂停")

    _PROGRESS["phase"] = "enable-relay-discovery"
    api.request("PATCH", "/rest/config/options", {
        "listenAddresses": EXPECTED_LISTENERS,
        "globalAnnounceEnabled": True,
        "localAnnounceEnabled": False,
        "announceLANAddresses": False,
        "relaysEnabled": True,
        "natEnabled": False,
        "startBrowser": False,
    })
    _PROGRESS["completed"].append("已启用公共设备发现与官方中继，保留 loopback TCP 并添加动态中继地址；未开放通用网卡监听")

    if _restart_if_required(api, own_id):
        _PROGRESS["completed"].append("Syncthing 已通过本机 API 安全重启并重新核验设备身份")
    final = _verified_pair_state(api, vault, role, peer_id)
    onboarding = base.write_sync_onboarding_state(codex_home, role, "paired-paused", peer_syncthing_device_id=peer_id, syncthing_device_id=own_id)
    _PROGRESS["onboardingState"] = onboarding
    _PROGRESS["phase"] = "paired-paused"
    return _pair_status(args, own_id, peer_id, final["folder"], final["options"], already=False)


def _validate_network_options(options: Any) -> None:
    if not isinstance(options, dict):
        raise PairingError("network-options-invalid", "Syncthing 网络选项格式无法验证。")
    listeners = options.get("listenAddresses")
    if not isinstance(listeners, list) or any(not isinstance(item, str) for item in listeners):
        raise PairingError("network-options-invalid", "Syncthing 监听地址列表无法验证。")
    current = set(listeners)
    if current not in ({LOOPBACK_LISTENER}, set(EXPECTED_LISTENERS)):
        raise PairingError("listener-conflict", "发现非预期的监听地址；为避免扩大网络暴露面，未覆盖。")
    for field in ("globalAnnounceEnabled", "localAnnounceEnabled", "relaysEnabled", "natEnabled", "startBrowser"):
        if field in options and type(options[field]) is not bool:
            raise PairingError("network-options-invalid", f"Syncthing 网络选项 {field} 类型异常。")


def _verified_pair_state(api: LocalSyncthingAPI, vault: Path, role: str, peer_id: str) -> dict[str, Any]:
    own_id, devices, folders = _device_records(api)
    _ensure_only_expected_peer(devices, own_id, peer_id)
    folder = _target_folder(folders, vault)
    members = _folder_member_ids(folder)
    expected_members = {base._normalized_device_id(own_id), base._normalized_device_id(peer_id)}
    if set(members) != expected_members or len(members) != 2:
        raise PairingError("pairing-verification-failed", "目标文件夹实际共享成员与双设备方案不一致。")
    expected_type = "sendonly" if role == "primary" else "receiveonly"
    if folder.get("type") != expected_type or folder.get("paused") is not True:
        raise PairingError("pairing-verification-failed", "目标文件夹未处于预期的暂停式单向播种状态。")
    peer = [item for item in devices if base._normalized_device_id(str(item.get("deviceID", ""))) == base._normalized_device_id(peer_id)]
    if len(peer) != 1 or peer[0].get("paused") is not True or peer[0].get("introducer") is not False or peer[0].get("autoAcceptFolders") is not False:
        raise PairingError("pairing-verification-failed", "远端设备未保持暂停、非 introducer、禁止自动接收文件夹。")
    options = api.request("GET", "/rest/config/options")
    if not isinstance(options, dict):
        raise PairingError("pairing-verification-failed", "Syncthing 网络设置读取失败。")
    expected_options = {
        "listenAddresses": EXPECTED_LISTENERS,
        "globalAnnounceEnabled": True,
        "localAnnounceEnabled": False,
        "announceLANAddresses": False,
        "relaysEnabled": True,
        "natEnabled": False,
        "startBrowser": False,
    }
    if any(options.get(key) != value for key, value in expected_options.items()):
        raise PairingError("pairing-verification-failed", "发现/中继/监听配置与预期不符。")
    restart_required = api.request("GET", "/rest/config/restart-required")
    if not isinstance(restart_required, dict) or type(restart_required.get("requiresRestart")) is not bool:
        raise PairingError("restart-state-invalid", "无法验证 Syncthing 是否仍需要重启。")
    if restart_required["requiresRestart"]:
        raise PairingError("restart-required", "Syncthing 重启后仍报告配置未生效；保留配置和备份，未报告配对完成。")
    return {"folder": folder, "options": options, "ownDeviceId": own_id}


def _verify_unpaused_pair_state(
    api: LocalSyncthingAPI, vault: Path, role: str, peer_id: str, own_id: str
) -> dict[str, Any]:
    observed_id, devices, folders = _device_records(api)
    if base._normalized_device_id(observed_id) != base._normalized_device_id(own_id):
        raise PairingError("device-id-changed", "操作期间本机 Syncthing 身份发生变化。")
    _ensure_only_expected_peer(devices, observed_id, peer_id)
    folder = _target_folder(folders, vault)
    expected_type = "sendonly" if role == "primary" else "receiveonly"
    expected_members = {base._normalized_device_id(own_id), base._normalized_device_id(peer_id)}
    if folder.get("type") != expected_type or folder.get("paused") is not False:
        raise PairingError("operation-verification-failed", "目标 Vault 文件夹未处于预期活动模式。")
    if set(_folder_member_ids(folder)) != expected_members or len(_folder_member_ids(folder)) != 2:
        raise PairingError("operation-verification-failed", "目标 Vault 文件夹成员在操作期间发生变化。")
    peer = [item for item in devices if base._normalized_device_id(str(item.get("deviceID", ""))) == base._normalized_device_id(peer_id)]
    if len(peer) != 1 or peer[0].get("paused") is not False:
        raise PairingError("operation-verification-failed", "唯一已确认的对端设备未处于活动状态。")
    if peer[0].get("introducer") is not False or peer[0].get("autoAcceptFolders") is not False:
        raise PairingError("operation-verification-failed", "对端安全设置在操作期间发生变化。")
    return {"folder": folder, "peer": peer[0], "syncthingDeviceId": observed_id}


def _contain_pending_operation(api: LocalSyncthingAPI, vault: Path, pending: dict[str, Any]) -> dict[str, Any]:
    """Best-effort containment; each target is mutated only after exact identity/path checks."""
    expected_own = pending.get("syncthingDeviceId")
    expected_peer = pending.get("peerSyncthingDeviceId")
    expected_path = pending.get("vaultPath")
    expected_folder_id = pending.get("folderId")
    report: dict[str, Any] = {
        "folder": {"targetVerified": False, "membershipMatchesPending": None, "initialPaused": None, "pauseRequested": False, "paused": None, "errors": []},
        "peerDevice": {"targetVerified": False, "initialPaused": None, "pauseRequested": False, "paused": None, "errors": []},
        "localIdentityMatches": None,
        "containmentVerified": False,
    }
    own_valid = isinstance(expected_own, str) and DEVICE_ID_RE.fullmatch(expected_own.strip().upper()) is not None
    peer_valid = isinstance(expected_peer, str) and DEVICE_ID_RE.fullmatch(expected_peer.strip().upper()) is not None
    if own_valid:
        try:
            observed_own = _device_id(api)
            report["localIdentityMatches"] = base._normalized_device_id(observed_own) == base._normalized_device_id(expected_own)
        except Exception as exc:
            report["identityError"] = f"local Device ID read failed: {getattr(exc, 'code', type(exc).__name__)}"
    else:
        report["identityError"] = "pending local Device ID is invalid"

    folder_path_valid = (isinstance(expected_path, str) and expected_folder_id == FOLDER_ID
                         and base.same_path(expected_path, vault))
    if not folder_path_valid:
        report["folder"]["errors"].append("pending folder ID/path is invalid or differs from current invocation")
    else:
        # Exact fixed ID + local Vault path identify the folder to pause. A changed
        # membership is reported, but does not prevent pausing that same folder.
        try:
            folders = api.request("GET", "/rest/config/folders")
            if not isinstance(folders, list) or any(not isinstance(item, dict) for item in folders):
                raise PairingError("containment-config-invalid", "folder list is not verifiable")
            folder = _target_folder(folders, vault)
            report["folder"]["targetVerified"] = True
            report["folder"]["initialPaused"] = folder.get("paused") if type(folder.get("paused")) is bool else None
            try:
                members = _folder_member_ids(folder)
                report["folder"]["membershipMatchesPending"] = (
                    own_valid and peer_valid and len(members) == 2
                    and set(members) == {base._normalized_device_id(expected_own), base._normalized_device_id(expected_peer)}
                )
            except Exception:
                report["folder"]["membershipMatchesPending"] = False
            if folder.get("paused") is not True:
                report["folder"]["pauseRequested"] = True
                api.request("PATCH", f"/rest/config/folders/{quote(FOLDER_ID, safe='')}", {"paused": True})
        except Exception as exc:
            report["folder"]["errors"].append(getattr(exc, "code", type(exc).__name__))
        try:
            folders = api.request("GET", "/rest/config/folders")
            if isinstance(folders, list) and all(isinstance(item, dict) for item in folders):
                current_folder = _target_folder(folders, vault)
                if type(current_folder.get("paused")) is bool:
                    report["folder"]["paused"] = current_folder["paused"]
                else:
                    report["folder"]["errors"].append("folder paused state is not boolean")
            else:
                report["folder"]["errors"].append("folder list reread failed")
        except Exception as exc:
            report["folder"]["errors"].append(getattr(exc, "code", type(exc).__name__))

    # Even if folder pause failed, independently pause the exact persisted peer.
    if not peer_valid or (own_valid and base._normalized_device_id(expected_peer) == base._normalized_device_id(expected_own)):
        report["peerDevice"]["errors"].append("pending peer Device ID is invalid or equals the local device")
    else:
        try:
            devices = api.request("GET", "/rest/config/devices")
            if not isinstance(devices, list) or any(not isinstance(item, dict) for item in devices):
                raise PairingError("containment-config-invalid", "device list is not verifiable")
            peers = [item for item in devices if isinstance(item.get("deviceID"), str)
                     and base._normalized_device_id(item["deviceID"]) == base._normalized_device_id(expected_peer)]
            if len(peers) != 1:
                raise PairingError("containment-target-ambiguous", "persisted peer Device ID is not unique")
            report["peerDevice"]["targetVerified"] = True
            report["peerDevice"]["initialPaused"] = peers[0].get("paused") if type(peers[0].get("paused")) is bool else None
            if peers[0].get("paused") is not True:
                report["peerDevice"]["pauseRequested"] = True
                api.request("PATCH", f"/rest/config/devices/{quote(expected_peer, safe='')}", {"paused": True})
        except Exception as exc:
            report["peerDevice"]["errors"].append(getattr(exc, "code", type(exc).__name__))
        try:
            devices = api.request("GET", "/rest/config/devices")
            if isinstance(devices, list) and all(isinstance(item, dict) for item in devices):
                peers = [item for item in devices if isinstance(item.get("deviceID"), str)
                         and base._normalized_device_id(item["deviceID"]) == base._normalized_device_id(expected_peer)]
                if len(peers) == 1 and type(peers[0].get("paused")) is bool:
                    report["peerDevice"]["paused"] = peers[0]["paused"]
                else:
                    report["peerDevice"]["errors"].append("peer identity or paused state could not be verified")
            else:
                report["peerDevice"]["errors"].append("device list reread failed")
        except Exception as exc:
            report["peerDevice"]["errors"].append(getattr(exc, "code", type(exc).__name__))
    report["containmentVerified"] = (
        report["localIdentityMatches"] is True
        and report["folder"]["targetVerified"] is True and report["folder"]["paused"] is True
        and report["peerDevice"]["targetVerified"] is True and report["peerDevice"]["paused"] is True
    )
    return report


def _persist_held_operation(codex_home: Path, role: str, pending: dict[str, Any], containment: dict[str, Any]) -> None:
    try:
        base.hold_sync_onboarding_operation(
            codex_home, role, str(pending["operationId"]), containment,
            pending_operation=pending,
        )
    except Exception as exc:
        containment.setdefault("stateWriteErrors", []).append(getattr(exc, "code", type(exc).__name__))
    _PROGRESS["containment"] = containment
    _PROGRESS["containmentVerified"] = containment.get("containmentVerified") is True
    _PROGRESS["containmentStatus"] = "verified" if _PROGRESS["containmentVerified"] else "attempted-unverified"


def _invalidate_containment_evidence() -> None:
    """A prior pause observation stops being current before any resume/mode change."""
    _PROGRESS["containment"] = None
    _PROGRESS["containmentVerified"] = False
    _PROGRESS["containmentStatus"] = "invalidated-before-resume"


def _containment_report_fields() -> dict[str, Any]:
    containment = _PROGRESS.get("containment")
    stopped = bool(
        isinstance(containment, dict)
        and containment.get("containmentVerified") is True
        and _PROGRESS.get("containmentVerified") is True
    )
    status = _PROGRESS.get("containmentStatus")
    if not isinstance(status, str):
        status = "verified" if stopped else ("attempted-unverified" if isinstance(containment, dict) else "not-attempted")
    return {
        "containmentStatus": status,
        "syncthingChangesStopped": stopped,
        "containmentVerified": stopped,
        "containment": containment,
    }


def _safe_contain_pending_operation(api: LocalSyncthingAPI, vault: Path, pending: dict[str, Any]) -> dict[str, Any]:
    try:
        return _contain_pending_operation(api, vault, pending)
    except Exception as exc:
        return {
            "folder": {"targetVerified": False, "initialPaused": None, "pauseRequested": False, "paused": None, "errors": [getattr(exc, "code", type(exc).__name__)]},
            "peerDevice": {"targetVerified": False, "initialPaused": None, "pauseRequested": False, "paused": None, "errors": [getattr(exc, "code", type(exc).__name__)]},
            "containmentVerified": False,
        }


def _contain_pending_before_mutation(
    args: argparse.Namespace, codex_home: Path, vault: Path, api: LocalSyncthingAPI
) -> None:
    onboarding = _onboarding_state(codex_home, args.role)
    pending = onboarding.get("pendingOperation")
    if pending is None:
        return
    if not isinstance(pending, dict) or pending.get("phase") not in {"mutating", "held"}:
        raise PairingError("onboarding-operation-invalid", "待执行状态损坏；不得执行任何新的同步变更。")
    phase = pending["phase"]
    containment = _safe_contain_pending_operation(api, vault, pending)
    _persist_held_operation(codex_home, args.role, pending, containment)
    if not containment.get("containmentVerified"):
        raise PairingError("operation-recovery-held", "存在未完成的同步操作，且无法核实 folder 与确切对端均已暂停；本次不执行任何后续阶段。")
    if phase == "mutating":
        raise PairingError("operation-interrupted-held", "发现上次同步操作执行中断。已隔离并记录 HOLD；本次只完成恢复，请在新的调用中重新确认。")
    if (containment["folder"].get("initialPaused") is not True
            or containment["peerDevice"].get("initialPaused") is not True):
        raise PairingError("operation-recontained-held", "待恢复目标原本未全部暂停；已隔离，本次不继续。请检查后在新的调用中重新确认。")


def _contain_and_hold_failed_operation(
    codex_home: Path, role: str, vault: Path, api: LocalSyncthingAPI, operation: Any
) -> None:
    if isinstance(operation, dict) and isinstance(operation.get("pendingOperation"), dict):
        pending = operation["pendingOperation"]
        containment = _safe_contain_pending_operation(api, vault, pending)
        _persist_held_operation(codex_home, role, pending, containment)


def _recover_pending_operation(
    args: argparse.Namespace,
    codex_home: Path,
    vault: Path,
    api: LocalSyncthingAPI,
    action: str,
    own_id: str,
    peer_id: str,
    confirmations: dict[str, bool],
) -> dict[str, Any] | None:
    state = _onboarding_state(codex_home, args.role)
    pending = state.get("pendingOperation")
    if pending is None:
        return None
    if not isinstance(pending, dict):
        raise PairingError("onboarding-operation-invalid", "待执行状态损坏；保持 Syncthing 当前状态并人工检查。")
    phase = pending.get("phase")
    if phase not in {"mutating", "held"} or not isinstance(pending.get("operationId"), str):
        raise PairingError("onboarding-operation-invalid", "待执行状态阶段或操作 ID 无效；保持 Syncthing 当前状态并人工检查。")
    containment = _safe_contain_pending_operation(api, vault, pending)
    _persist_held_operation(codex_home, args.role, pending, containment)
    if not containment.get("containmentVerified"):
        raise PairingError("operation-recovery-held", "上次同步操作未完成，且无法核实文件夹与对端设备均已暂停。不要继续同步；请按报告中的未知项人工处理。")
    if phase == "mutating":
        raise PairingError("operation-interrupted-held", "发现上次操作在执行中中断。已核实并暂停本机目标；本次只完成隔离，需重新确认后再发起一次新调用。")
    if (containment["folder"].get("initialPaused") is not True
            or containment["peerDevice"].get("initialPaused") is not True):
        raise PairingError("operation-recontained-held", "检测到待恢复目标原本未全部暂停；已先完成隔离并记录 HOLD。本次不继续，检查报告后需在新的调用中重新确认。")
    expected_type = "receiveonly" if args.role == "server" else "sendonly"
    expected_start = base._ONBOARDING_OPERATION_START.get((args.role, action))
    expected_completion = base._ONBOARDING_OPERATION_COMPLETION.get((args.role, action))
    committed_recovery = pending.get("completionCommitUncertain") is True
    expected_recorded_status = expected_completion if committed_recovery else expected_start
    if (pending.get("action") != action or pending.get("role") != args.role
            or expected_start != "paired-paused"
            or pending.get("previousStatus") != expected_start
            or state.get("status") != expected_recorded_status
            or (committed_recovery and pending.get("committedStatus") != expected_completion)
            or not isinstance(pending.get("syncthingDeviceId"), str)
            or base._normalized_device_id(pending["syncthingDeviceId"]) != base._normalized_device_id(own_id)
            or base._normalized_device_id(str(pending.get("peerSyncthingDeviceId", ""))) != base._normalized_device_id(peer_id)
            or not base.same_path(str(pending.get("vaultPath", "")), vault)
            or pending.get("folderId") != FOLDER_ID or pending.get("expectedFolderType") != expected_type):
        raise PairingError("operation-recovery-identity-conflict", "待恢复操作与当前设备、路径或阶段不一致；已暂停已识别的目标，不继续。")
    if not confirmations or not all(value is True for value in confirmations.values()):
        raise PairingError("operation-reconfirmation-required", "重试前必须重新确认所有安全条件；旧确认记录不能授权再次启动。")
    return pending


def _assert_no_pending_operation(codex_home: Path, role: str) -> None:
    state = _onboarding_state(codex_home, role)
    if state.get("pendingOperation") is not None:
        raise PairingError("onboarding-operation-pending", "存在未完成的同步操作；先用对应的接收/播种恢复流程处理，未执行后续阶段。")


def _restart_if_required(api: LocalSyncthingAPI, expected_device_id: str) -> bool:
    required = api.request("GET", "/rest/config/restart-required")
    if not isinstance(required, dict) or type(required.get("requiresRestart")) is not bool:
        raise PairingError("restart-state-invalid", "无法验证 Syncthing 是否需要重启；配对配置已写入但尚未确认生效。")
    if not required["requiresRestart"]:
        return False

    try:
        api.request("POST", "/rest/system/restart")
    except PairingError as exc:
        # The process may close the local API before its restart response reaches us.
        if exc.code != "syncthing-api-unavailable":
            raise

    deadline = time.monotonic() + 45
    last_error: PairingError | None = None
    while time.monotonic() < deadline:
        time.sleep(0.5)
        try:
            status = api.request("GET", "/rest/system/status")
            restarted = api.request("GET", "/rest/config/restart-required")
        except PairingError as exc:
            last_error = exc
            continue
        if not isinstance(status, dict) or not isinstance(status.get("myID"), str):
            continue
        if base._normalized_device_id(status["myID"]) != base._normalized_device_id(expected_device_id):
            raise PairingError("device-id-changed", "Syncthing 重启后设备身份发生变化；停止后续配对。")
        if not isinstance(restarted, dict) or type(restarted.get("requiresRestart")) is not bool:
            raise PairingError("restart-state-invalid", "Syncthing 重启后无法核验配置生效状态。")
        if not restarted["requiresRestart"]:
            profile, executable = _profile()
            if not base.same_path(profile, api.profile):
                raise PairingError("profile-changed", "Syncthing 重启后活动配置目录发生变化；停止后续配对。")
            base.verify_local_device_identity(executable, profile, status["myID"])
            return True
    detail = f"（最近状态：{last_error.code}）" if last_error else ""
    raise PairingError("restart-timeout", f"Syncthing 未能在 45 秒内重启并应用配对网络设置{detail}；保留配置和备份。")


def _pair_status(args: argparse.Namespace, own_id: str, peer_id: str, folder: dict[str, Any], options: dict[str, Any], *, already: bool) -> dict[str, Any]:
    return {
        "status": "already-paired" if already else "paired-paused",
        "role": args.role,
        "syncthingDeviceId": own_id,
        "peerSyncthingDeviceId": peer_id,
        "deviceLabel": args.device_label,
        "folderId": FOLDER_ID,
        "folderType": folder.get("type"),
        "folderPaused": folder.get("paused"),
        "network": {
            "listenAddresses": options.get("listenAddresses"),
            "globalDiscovery": options.get("globalAnnounceEnabled"),
            "lanDiscovery": options.get("localAnnounceEnabled"),
            "lanAddressAnnouncement": options.get("announceLANAddresses"),
            "publicRelays": options.get("relaysEnabled"),
            "natMapping": options.get("natEnabled"),
            "browserAutoOpen": options.get("startBrowser"),
        },
        "pairingCard": {
            "deviceLabel": args.device_label,
            "syncthingDeviceId": own_id,
            "folderId": FOLDER_ID,
            "role": args.role,
            "transferPolicy": "PC sendonly -> server receiveonly; paused until both endpoints are paired",
            "networkPolicy": "public discovery + official relay; TCP loopback + official dynamic relay address; LAN discovery/announcement and Syncthing NAT mapping off; no router/firewall changes",
        },
        "backupPath": _PROGRESS.get("backupPath"),
        "progress": dict(_PROGRESS),
        "note": "已核验设备与文件夹配置；本次操作未发起 Vault 文件传输。实际连接/同步状态以 status 查询为准。卡片不含本机路径、第二大脑 deviceId 或任何凭证。",
    }


def _folder_status(api: LocalSyncthingAPI) -> dict[str, Any]:
    return api.request("GET", f"/rest/db/status?folder={quote(FOLDER_ID, safe='')}")


def _folder_is_idle_and_clean(status: Any, *, require_receive_only_clean: bool = False) -> bool:
    if not isinstance(status, dict):
        return False
    required_zeroes = ["needTotalItems", "needBytes", "needDeletes", "pullErrors"]
    if require_receive_only_clean:
        required_zeroes.append("receiveOnlyTotalItems")
    return status.get("state") == "idle" and all(type(status.get(key)) is int and status[key] == 0 for key in required_zeroes)


def _seed_state_is_clean(state: dict[str, Any]) -> bool:
    return bool(
        state.get("folderPathMatches") is True
        and state.get("folderType") == "receiveonly"
        and state.get("folderPaused") is False
        and state.get("connectedRemoteCount") == 1
        and _folder_is_idle_and_clean(state.get("folderStatus"), require_receive_only_clean=True)
    )


def _seed_status_signature(state: dict[str, Any]) -> tuple[Any, ...]:
    folder_status = state.get("folderStatus")
    if not isinstance(folder_status, dict):
        return ()
    return (
        state.get("folderType"), state.get("folderPaused"), state.get("folderPathMatches"),
        state.get("connectedRemoteCount"), folder_status.get("state"),
        folder_status.get("needTotalItems"), folder_status.get("needBytes"),
        folder_status.get("needDeletes"), folder_status.get("pullErrors"),
        folder_status.get("receiveOnlyTotalItems"),
    )


def _connections(api: LocalSyncthingAPI, own_id: str) -> tuple[int, list[str]]:
    response = api.request("GET", "/rest/system/connections")
    if not isinstance(response, dict) or not isinstance(response.get("connections"), dict):
        raise PairingError("connection-state-invalid", "Syncthing 实时连接状态无法读取。")
    connected = 0
    connected_ids: list[str] = []
    for device_id, value in response["connections"].items():
        if device_id == "_total":
            continue
        if not isinstance(value, dict) or type(value.get("connected")) is not bool:
            raise PairingError("connection-state-invalid", "Syncthing 实时连接状态结构异常。")
        if value["connected"] and base._normalized_device_id(device_id) != base._normalized_device_id(own_id):
            connected += 1
            connected_ids.append(device_id)
    return connected, connected_ids


def _status(codex_home: Path, vault: Path, role: str, api: LocalSyncthingAPI) -> dict[str, Any]:
    own_id, devices, folders = _device_records(api)
    onboarding = _onboarding_state(codex_home, role)
    remotes = _known_remote_devices(codex_home, role, devices, own_id)
    folder = _target_folder(folders, vault)
    connected_count, connected_ids = _connections(api, own_id)
    db = _folder_status(api)
    if not isinstance(db, dict):
        raise PairingError("folder-status-invalid", "Syncthing 文件夹数据库状态无法读取。")
    return {
        "status": "observed",
        "role": role,
        "onboardingStage": onboarding.get("status"),
        "pendingOperation": ({"action": onboarding["pendingOperation"].get("action"), "phase": onboarding["pendingOperation"].get("phase")} if isinstance(onboarding.get("pendingOperation"), dict) else ("invalid" if onboarding.get("pendingOperation") is not None else None)),
        "syncthingDeviceId": own_id,
        "configuredRemoteDeviceIds": [item.get("deviceID") for item in remotes],
        "connectedRemoteCount": connected_count,
        "connectedRemoteDeviceIds": connected_ids,
        "folderId": FOLDER_ID,
        "folderPathMatches": base.same_path(str(folder.get("path", "")), vault),
        "folderType": folder.get("type"),
        "folderPaused": folder.get("paused"),
        "folderStatus": {key: db.get(key) for key in (
            "state", "needTotalItems", "needFiles", "needBytes", "needDeletes",
            "pullErrors", "receiveOnlyTotalItems", "receiveOnlyChangedFiles",
            "receiveOnlyChangedBytes", "receiveOnlyChangedDeletes", "globalFiles",
            "localFiles", "inSyncFiles", "globalBytes", "localBytes", "inSyncBytes",
        )},
        "backupDevice": _read_device_config(codex_home, vault, role).get("gitBackupDevice"),
        "crossDeviceSyncVerified": False,
    }


def _wait_for_promotion_live_state(
    codex_home: Path,
    vault: Path,
    role: str,
    api: LocalSyncthingAPI,
    peer_id: str,
    own_id: str,
    baseline_sha256: str,
    allowed_folder_types: set[str],
    *,
    timeout_seconds: int = 45,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        observed_id, devices, folders = _device_records(api)
        if base._normalized_device_id(observed_id) != base._normalized_device_id(own_id):
            raise PairingError("device-id-changed", "晋级核验期间本机 Syncthing 身份发生变化。")
        _ensure_only_expected_peer(devices, observed_id, peer_id)
        folder = _target_folder(folders, vault)
        if folder.get("type") not in allowed_folder_types:
            raise PairingError("promotion-mode-conflict", "晋级期间文件夹进入未记录的模式；保持 HOLD。")
        if folder.get("paused") is not False:
            time.sleep(0.5)
            continue
        members = _folder_member_ids(folder)
        if len(members) != 2 or set(members) != {base._normalized_device_id(own_id), base._normalized_device_id(peer_id)}:
            raise PairingError("promotion-membership-conflict", "晋级核验期间 Vault 文件夹成员发生变化。")
        peers = [item for item in devices if base._normalized_device_id(str(item.get("deviceID", ""))) == base._normalized_device_id(peer_id)]
        if len(peers) != 1 or peers[0].get("introducer") is not False or peers[0].get("autoAcceptFolders") is not False:
            raise PairingError("promotion-peer-conflict", "晋级核验期间对端身份或安全设置无法验证。")
        state = _status(codex_home, vault, role, api)
        db = state.get("folderStatus")
        clean = _folder_is_idle_and_clean(db)
        if role == "server" and folder.get("type") == "receiveonly":
            clean = _folder_is_idle_and_clean(db, require_receive_only_clean=True)
        if peers[0].get("paused") is False and state.get("connectedRemoteCount") == 1 and clean:
            manifest_before = _file_manifest(vault)
            if manifest_before["manifestSha256"] != baseline_sha256:
                raise PairingError("promotion-content-changed", "恢复晋级期间 Vault 内容偏离已验证基线；保留内容并进入 HOLD。")
            state_after = _status(codex_home, vault, role, api)
            manifest_after = _file_manifest(vault)
            if (not _folder_is_idle_and_clean(state_after.get("folderStatus"), require_receive_only_clean=(role == "server" and state_after.get("folderType") == "receiveonly"))
                    or _seed_status_signature(state) != _seed_status_signature(state_after)
                    or manifest_after["manifestSha256"] != baseline_sha256):
                raise PairingError("promotion-state-changed", "晋级内容/同步状态在核验窗口发生变化；保持 HOLD。")
            return {"state": state_after, "manifest": manifest_after, "folder": folder, "peerPaused": peers[0].get("paused")}
        time.sleep(0.5)
    raise PairingError("promotion-convergence-timeout", "晋级恢复后未在限定时间内重新达到唯一连接、idle、无待同步项/错误和稳定内容指纹；保持 HOLD。")


@_serialized_transition
def _arm_receiver(args: argparse.Namespace, codex_home: Path, vault: Path, api: LocalSyncthingAPI) -> dict[str, Any]:
    if args.role != "server":
        raise PairingError("role-conflict", "只有 server 角色可准备 receive-only 接收端。")
    _backup_role(codex_home, args.role)
    own_id, devices, folders = _device_records(api)
    remotes = _known_remote_devices(codex_home, args.role, devices, own_id)
    if len(remotes) != 1:
        raise PairingError("peer-not-paired", "尚未配置唯一对端，不能准备接收端。")
    peer_id = remotes[0]["deviceID"]
    pending = _recover_pending_operation(
        args, codex_home, vault, api, "arm-receiver", own_id, peer_id,
        {"receiverPreparationApproved": args.confirmed_arm_receiver is True},
    )
    if not args.confirmed_arm_receiver:
        raise PairingError("receiver-arming-confirmation-required", "准备接收端会解除服务器同步暂停；需要用户明确确认本次接收准备。")
    if pending is not None:
        own_id, devices, folders = _device_records(api)
        refreshed_peers = _known_remote_devices(codex_home, args.role, devices, own_id)
        if len(refreshed_peers) != 1:
            raise PairingError("peer-not-paired", "恢复后无法确认唯一的配对设备。")
        peer_id = refreshed_peers[0]["deviceID"]
    folder = _target_folder(folders, vault)
    if folder.get("type") != "receiveonly" or folder.get("paused") is not True:
        state = _onboarding_state(codex_home, args.role)
        if folder.get("type") == "receiveonly" and folder.get("paused") is False and state.get("status") == "receiver-ready":
            observed = _verify_unpaused_pair_state(api, vault, args.role, peer_id, own_id)
            return {"status": "already-receiver-ready", "role": args.role, "syncthingDeviceId": own_id, "peerSyncthingDeviceId": peer_id, "folderId": FOLDER_ID, "folderType": observed["folder"].get("type"), "folderPaused": observed["folder"].get("paused"), "peerPaused": observed["peer"].get("paused"), "transferStartedByThisEndpoint": False, "note": "服务器接收端和唯一对端均已核验为活动；未重复修改配置。"}
        raise PairingError("receiver-state-conflict", "服务器必须保持 receiveonly 且暂停，才可进入接收准备阶段。")
    _verified_pair_state(api, vault, args.role, peer_id)
    if not base.same_path(str(folder.get("path", "")), vault):
        raise PairingError("vault-path-conflict", "服务器 folder 路径与确认的本地 Vault 路径不符。")
    if not _is_empty_receiver(vault):
        raise PairingError("server-vault-not-empty", "服务器目录不再为空；停止以避免覆盖或合并数据。")
    if pending is None and _onboarding_state(codex_home, args.role).get("status") != "paired-paused":
        raise PairingError("receiver-stage-conflict", "服务器并非首次接收准备阶段；不重复解除暂停。")
    backup = _backup_config(codex_home, api.profile, vault)
    _PROGRESS["backupPath"] = str(backup)
    try:
        operation = base.begin_sync_onboarding_operation(
            codex_home, args.role, action="arm-receiver", syncthing_device_id=own_id,
            peer_syncthing_device_id=peer_id, vault_path=str(vault), expected_folder_type="receiveonly",
            backup_path=str(backup), confirmations={"receiverPreparationApproved": True},
        )
        _PROGRESS["pendingOperationId"] = operation["operationId"]
        _PROGRESS["completed"].append("已持久化接收端操作意图与确认记录")
        _invalidate_containment_evidence()
        _PROGRESS["phase"] = "unpause-peer-device"
        api.request("PATCH", f"/rest/config/devices/{quote(peer_id, safe='')}", {"paused": False})
        _PROGRESS["completed"].append("已解除唯一服务器对端设备暂停")
        _PROGRESS["phase"] = "unpause-receiver-folder"
        api.request("PATCH", f"/rest/config/folders/{quote(FOLDER_ID, safe='')}", {"paused": False})
        _PROGRESS["completed"].append("已解除服务器 receive-only 文件夹暂停")
        _PROGRESS["phase"] = "scan-receiver-folder"
        api.request("POST", f"/rest/db/scan?folder={quote(FOLDER_ID, safe='')}")
        _PROGRESS["phase"] = "verify-receiver-state"
        observed = _verify_unpaused_pair_state(api, vault, args.role, peer_id, own_id)
        _PROGRESS["phase"] = "commit-receiver-ready"
        onboarding = base.complete_sync_onboarding_operation(codex_home, args.role, operation["operationId"], "receiver-ready")
        _PROGRESS["phase"] = "complete"
    except KeyboardInterrupt:
        _contain_and_hold_failed_operation(codex_home, args.role, vault, api, locals().get("operation"))
        raise
    except Exception:
        _contain_and_hold_failed_operation(codex_home, args.role, vault, api, locals().get("operation"))
        raise
    return {"status": "receiver-ready", "role": args.role, "syncthingDeviceId": own_id, "peerSyncthingDeviceId": peer_id, "folderId": FOLDER_ID, "folderType": observed["folder"].get("type"), "folderPaused": observed["folder"].get("paused"), "peerPaused": observed["peer"].get("paused"), "backupPath": str(backup), "onboardingState": onboarding, "transferStartedByThisEndpoint": False, "note": "接收端与对端设备状态已回读核验；源端仍暂停时不会开始传输。请把此状态与配对卡一起交给 PC 端 Codex。"}


def _is_empty_receiver(vault: Path) -> bool:
    if not vault.exists() or not vault.is_dir() or vault.is_symlink():
        return False
    for child in vault.iterdir():
        if child.name in {".stignore", ".stfolder"}:
            continue
        return False
    return True


@_serialized_transition
def _start_source(args: argparse.Namespace, codex_home: Path, vault: Path, api: LocalSyncthingAPI) -> dict[str, Any]:
    if args.role != "primary":
        raise PairingError("role-conflict", "只有 primary 角色可启动 PC -> 服务器的首次播种。")
    _backup_role(codex_home, args.role)
    own_id, devices, folders = _device_records(api)
    remotes = _known_remote_devices(codex_home, args.role, devices, own_id)
    if len(remotes) != 1:
        raise PairingError("peer-not-paired", "尚未配置唯一服务器设备，不能开始首次传输。")
    peer_id = remotes[0]["deviceID"]
    pending = _recover_pending_operation(
        args, codex_home, vault, api, "start-source", own_id, peer_id,
        {"receiverReady": args.confirmed_receiver_ready is True, "writersPaused": args.confirmed_writers_paused is True},
    )
    if pending is not None:
        own_id, devices, folders = _device_records(api)
        remotes = _known_remote_devices(codex_home, args.role, devices, own_id)
        if len(remotes) != 1:
            raise PairingError("peer-not-paired", "恢复后无法确认唯一的服务器设备。")
        peer_id = remotes[0]["deviceID"]
    folder = _target_folder(folders, vault)
    state = _onboarding_state(codex_home, args.role)
    if folder.get("type") == "sendonly" and folder.get("paused") is False and state.get("status") == "seeding":
        observed = _verify_unpaused_pair_state(api, vault, args.role, peer_id, own_id)
        return {"status": "already-seeding", "role": args.role, "syncthingDeviceId": own_id, "peerSyncthingDeviceId": peer_id, "folderId": FOLDER_ID, "folderType": observed["folder"].get("type"), "folderPaused": observed["folder"].get("paused"), "peerPaused": observed["peer"].get("paused"), "note": "初次播种已开始；folder 与唯一对端均已核验为活动。请运行 status 检查实际进度。"}
    if folder.get("type") != "sendonly" or folder.get("paused") is not True:
        raise PairingError("source-state-conflict", "PC 必须是暂停的 sendonly 源端，才可开始首次播种。")
    _verified_pair_state(api, vault, args.role, peer_id)
    if not args.confirmed_receiver_ready or not args.confirmed_writers_paused:
        raise PairingError("receiver-confirmation-required", "必须先确认服务器已处于 receive-only 接收准备状态，且两端 Obsidian、Codex 和其他 Vault 写入者均已停写。")
    if pending is None and state.get("status") != "paired-paused":
        raise PairingError("source-stage-conflict", "PC 并非首次播种阶段；不重复解除暂停。")
    backup = _backup_config(codex_home, api.profile, vault)
    _PROGRESS["backupPath"] = str(backup)
    try:
        operation = base.begin_sync_onboarding_operation(
            codex_home, args.role, action="start-source", syncthing_device_id=own_id,
            peer_syncthing_device_id=peer_id, vault_path=str(vault), expected_folder_type="sendonly",
            backup_path=str(backup), confirmations={"receiverReady": True, "writersPaused": True},
        )
        _PROGRESS["pendingOperationId"] = operation["operationId"]
        _PROGRESS["completed"].append("已持久化首次播种操作意图与确认记录")
        _invalidate_containment_evidence()
        _PROGRESS["phase"] = "unpause-peer-device"
        api.request("PATCH", f"/rest/config/devices/{quote(peer_id, safe='')}", {"paused": False})
        _PROGRESS["completed"].append("已解除唯一服务器对端设备暂停")
        _PROGRESS["phase"] = "unpause-source-folder"
        api.request("PATCH", f"/rest/config/folders/{quote(FOLDER_ID, safe='')}", {"paused": False})
        _PROGRESS["completed"].append("已解除 PC send-only 源文件夹暂停")
        _PROGRESS["phase"] = "scan-source-folder"
        api.request("POST", f"/rest/db/scan?folder={quote(FOLDER_ID, safe='')}")
        _PROGRESS["phase"] = "verify-source-state"
        observed = _verify_unpaused_pair_state(api, vault, args.role, peer_id, own_id)
        _PROGRESS["phase"] = "commit-seeding"
        onboarding = base.complete_sync_onboarding_operation(codex_home, args.role, operation["operationId"], "seeding")
        _PROGRESS["phase"] = "complete"
    except KeyboardInterrupt:
        _contain_and_hold_failed_operation(codex_home, args.role, vault, api, locals().get("operation"))
        raise
    except Exception:
        _contain_and_hold_failed_operation(codex_home, args.role, vault, api, locals().get("operation"))
        raise
    return {"status": "seeding", "role": args.role, "syncthingDeviceId": own_id, "peerSyncthingDeviceId": peer_id, "folderId": FOLDER_ID, "folderType": observed["folder"].get("type"), "folderPaused": observed["folder"].get("paused"), "peerPaused": observed["peer"].get("paused"), "backupPath": str(backup), "onboardingState": onboarding, "initialTransferDirection": "PC -> SSH server", "note": "首次单向播种已启动并回读核验；两端 Obsidian、Codex 及其他 Vault 写入者应保持停写，直到两端索引与内容核验通过。"}


def _file_manifest(vault: Path) -> dict[str, Any]:
    if not vault.is_dir() or vault.is_symlink():
        raise PairingError("vault-path-invalid", "Manifest 目标不是普通目录。")
    digest = hashlib.sha256()
    files = 0
    directories = 0
    total_bytes = 0
    observed_files: list[tuple[Path, int, int, int, int, int]] = []
    observed_directories: list[tuple[Path, tuple[str, ...], int]] = []
    root = vault.resolve()
    stack = [root]

    def excluded(parts: tuple[str, ...]) -> bool:
        return bool(
            (parts and parts[0] in MANIFEST_IGNORES)
            or (len(parts) == 2 and parts[0] == ".obsidian" and parts[1].startswith(MANAGED_WORKSPACE_PREFIX))
        )

    while stack:
        current = stack.pop()
        try:
            before_directory = current.stat(follow_symlinks=False)
            children = sorted(current.iterdir(), key=lambda item: (item.name.casefold(), item.name))
        except OSError as exc:
            raise PairingError("manifest-read-failed", "读取 Vault 目录失败；没有生成验证指纹。") from exc
        included_names: list[str] = []
        for child in children:
            rel = child.relative_to(root).as_posix()
            parts = child.relative_to(root).parts
            if excluded(parts):
                continue
            included_names.append(child.name)
            try:
                if child.is_symlink() or (getattr(child, "is_junction", lambda: False)()):
                    raise PairingError("manifest-link-unsupported", "Vault 中存在符号链接或 junction；为避免越界读取，不生成验证指纹。")
                info = child.stat(follow_symlinks=False)
            except OSError as exc:
                raise PairingError("manifest-read-failed", "读取 Vault 元数据失败。") from exc
            if stat.S_ISDIR(info.st_mode):
                directories += 1
                digest.update(b"D\0" + rel.encode("utf-8") + b"\0")
                stack.append(child)
            elif stat.S_ISREG(info.st_mode):
                file_hash = hashlib.sha256()
                try:
                    with child.open("rb") as stream:
                        before = child.stat(follow_symlinks=False)
                        while True:
                            block = stream.read(1024 * 1024)
                            if not block:
                                break
                            file_hash.update(block)
                        after = child.stat(follow_symlinks=False)
                except OSError as exc:
                    raise PairingError("manifest-read-failed", "读取 Vault 文件失败。") from exc
                if (before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns
                        or before.st_ctime_ns != after.st_ctime_ns or before.st_ino != after.st_ino
                        or before.st_dev != after.st_dev or before.st_size != info.st_size
                        or before.st_mtime_ns != info.st_mtime_ns or before.st_ino != info.st_ino
                        or before.st_dev != info.st_dev):
                    raise PairingError("manifest-unstable", "计算期间 Vault 文件发生变化；暂停写入后再重试。")
                observed_files.append((child, after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_ino, after.st_dev))
                files += 1
                total_bytes += after.st_size
                digest.update(b"F\0" + rel.encode("utf-8") + b"\0" + str(after.st_size).encode("ascii") + b"\0" + file_hash.digest())
            else:
                raise PairingError("manifest-special-file", "Vault 中存在非普通文件；不能安全计算跨平台内容指纹。")
        try:
            after_directory = current.stat(follow_symlinks=False)
            after_names = tuple(
                item.name for item in sorted(current.iterdir(), key=lambda item: (item.name.casefold(), item.name))
                if not excluded(item.relative_to(root).parts)
            )
        except OSError as exc:
            raise PairingError("manifest-read-failed", "复核 Vault 目录时失败；未生成验证指纹。") from exc
        if (after_names != tuple(included_names) or before_directory.st_mtime_ns != after_directory.st_mtime_ns):
            raise PairingError("manifest-unstable", "计算期间 Vault 目录结构发生变化；暂停写入后再重试。")
        observed_directories.append((current, after_names, after_directory.st_mtime_ns))

    # Recheck the whole observed tree after hashing so additions, removals, or
    # modifications that occur later in the walk cannot silently escape it.
    try:
        for path, size, mtime_ns, ctime_ns, inode, device in observed_files:
            current = path.stat(follow_symlinks=False)
            if (not stat.S_ISREG(current.st_mode) or current.st_size != size or current.st_mtime_ns != mtime_ns
                    or current.st_ctime_ns != ctime_ns or current.st_ino != inode or current.st_dev != device):
                raise PairingError("manifest-unstable", "Vault 文件在指纹计算结束前发生变化；暂停写入后再重试。")
        for path, names, mtime_ns in observed_directories:
            current = path.stat(follow_symlinks=False)
            current_names = tuple(
                item.name for item in sorted(path.iterdir(), key=lambda item: (item.name.casefold(), item.name))
                if not excluded(item.relative_to(root).parts)
            )
            if not stat.S_ISDIR(current.st_mode) or current_names != names or current.st_mtime_ns != mtime_ns:
                raise PairingError("manifest-unstable", "Vault 目录结构在指纹计算结束前发生变化；暂停写入后再重试。")
    except OSError as exc:
        raise PairingError("manifest-read-failed", "复核 Vault 文件树时失败；未生成验证指纹。") from exc
    return {"status": "manifest", "manifestSha256": digest.hexdigest(), "files": files, "directories": directories, "bytes": total_bytes, "excludedRules": ["/.git", "/.claudian", "/.stignore", "/.stfolder", "/.obsidian/workspace*"], "pathsIncludedInOutput": False}


def _require_sha256(value: str, field: str) -> str:
    normalized = value.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise PairingError(f"{field}-required", f"{field} 必须是已核验的 64 位 SHA-256 指纹；不能跳过跨设备内容核对。")
    return normalized


def _recover_pending_promotion(
    args: argparse.Namespace,
    codex_home: Path,
    vault: Path,
    api: LocalSyncthingAPI,
    *,
    action: str,
    source_folder_type: str,
    peer_manifest_sha256: str | None,
) -> dict[str, Any] | None:
    onboarding = _onboarding_state(codex_home, args.role)
    pending = onboarding.get("pendingOperation")
    if pending is None:
        return None
    if not isinstance(pending, dict) or pending.get("phase") not in {"mutating", "held"}:
        raise PairingError("onboarding-operation-invalid", "待执行晋级状态损坏；保持现状并人工检查。")
    containment = _safe_contain_pending_operation(api, vault, pending)
    _persist_held_operation(codex_home, args.role, pending, containment)
    if not containment.get("containmentVerified"):
        raise PairingError("promotion-recovery-held", "晋级操作中断，未能核实本机 folder 与对端均暂停；保持 HOLD。")
    if pending.get("phase") == "mutating":
        raise PairingError("promotion-interrupted-held", "检测到晋级操作执行中断。已隔离并记录 HOLD；本次只完成恢复隔离，请在新的调用中重新确认。")
    if (containment["folder"].get("initialPaused") is not True
            or containment["peerDevice"].get("initialPaused") is not True):
        raise PairingError("promotion-recontained-held", "发现晋级目标原本未全部暂停；已隔离，本次不继续。请检查状态后在新的调用中重新确认。")

    start_stage = "seed-verified" if args.role == "server" else "seeding"
    completion_stage = base._ONBOARDING_OPERATION_COMPLETION.get((args.role, action))
    committed_recovery = pending.get("completionCommitUncertain") is True
    expected_recorded_stage = completion_stage if committed_recovery else start_stage
    own_id, devices, folders = _device_records(api)
    remotes = _known_remote_devices(codex_home, args.role, devices, own_id)
    if len(remotes) != 1:
        raise PairingError("promotion-peer-conflict", "恢复晋级时无法核实唯一配对设备。")
    peer_id = str(remotes[0].get("deviceID", ""))
    target_type = "sendreceive"
    if (pending.get("action") != action or pending.get("role") != args.role
            or onboarding.get("status") != expected_recorded_stage or pending.get("previousStatus") != start_stage
            or (committed_recovery and pending.get("committedStatus") != completion_stage)
            or not isinstance(pending.get("syncthingDeviceId"), str)
            or base._normalized_device_id(pending["syncthingDeviceId"]) != base._normalized_device_id(own_id)
            or base._normalized_device_id(str(pending.get("peerSyncthingDeviceId", ""))) != base._normalized_device_id(peer_id)
            or not base.same_path(str(pending.get("vaultPath", "")), vault)
            or pending.get("folderId") != FOLDER_ID
            or pending.get("sourceFolderType") != source_folder_type
            or pending.get("targetFolderType") != target_type
            or pending.get("expectedFolderType") != target_type):
        raise PairingError("promotion-recovery-identity-conflict", "待恢复晋级的操作、设备身份、路径或引导阶段不匹配；保持 HOLD。")
    if not (args.confirmed_verified and args.confirmed_writers_paused and args.confirmed_peer_state):
        raise PairingError("promotion-reconfirmation-required", "重试晋级需要重新确认内容/对端阶段、两端写入者停写和本次晋级授权。")
    expected_hash = _require_sha256(peer_manifest_sha256 or "", "peer-manifest-sha256")
    baseline_hash = _require_sha256(str(pending.get("baselineManifestSha256", "")), "promotion-baseline-sha256")
    recorded_peer_hash = _require_sha256(str(pending.get("peerManifestSha256", "")), "promotion-peer-manifest-sha256")
    if expected_hash != baseline_hash or recorded_peer_hash != expected_hash:
        raise PairingError("promotion-recovery-manifest-conflict", "新提供的对端 SHA-256 与晋级意图中记录的稳定基线不一致；不解除暂停。")

    folder = _target_folder(folders, vault)
    members = _folder_member_ids(folder)
    expected_members = {base._normalized_device_id(own_id), base._normalized_device_id(peer_id)}
    peer = [item for item in devices if base._normalized_device_id(str(item.get("deviceID", ""))) == base._normalized_device_id(peer_id)]
    if (folder.get("paused") is not True or folder.get("type") not in {source_folder_type, target_type}
            or len(members) != 2 or set(members) != expected_members
            or len(peer) != 1 or peer[0].get("paused") is not True
            or peer[0].get("introducer") is not False or peer[0].get("autoAcceptFolders") is not False):
        raise PairingError("promotion-recovery-config-conflict", "已暂停配置的文件夹模式、成员或对端状态不在可恢复集合中；不继续。")
    manifest = _file_manifest(vault)
    if manifest["manifestSha256"] != baseline_hash:
        raise PairingError("promotion-recovery-content-changed", "本机 Vault 内容已偏离持久化晋级基线；保留双方内容并保持 HOLD。")
    return pending


def _verify_seed_impl(args: argparse.Namespace, codex_home: Path, vault: Path, api: LocalSyncthingAPI) -> dict[str, Any]:
    _assert_no_pending_operation(codex_home, args.role)
    if args.role != "server":
        raise PairingError("role-conflict", "首次接收端验证必须在 server 设备上执行。")
    expected_source_hash = _require_sha256(args.source_manifest_sha256, "source-manifest-sha256")
    state = _status(codex_home, vault, args.role, api)
    if not _seed_state_is_clean(state):
        raise PairingError("seed-not-converged", "服务器尚未满足 receive-only、连接、idle、无待同步项/错误/本地差异条件；不要切换双向。")
    manifest = _file_manifest(vault)
    after_hash = _status(codex_home, vault, args.role, api)
    if not _seed_state_is_clean(after_hash) or _seed_status_signature(state) != _seed_status_signature(after_hash):
        raise PairingError("seed-state-changed", "计算内容指纹期间服务器连接或同步状态发生变化；保持 receive-only 并重新核验。")
    if manifest["manifestSha256"] != expected_source_hash:
        raise PairingError("manifest-mismatch", "服务器 Vault 内容指纹与 PC 源指纹不同；不要切换双向。保留两端文件并检查忽略规则或并发写入。")
    db = after_hash["folderStatus"]
    onboarding = base.write_sync_onboarding_state(codex_home, args.role, "seed-verified")
    return {"status": "seed-verified", "role": args.role, "folderId": FOLDER_ID, "folderType": state["folderType"], "connectedRemoteCount": state["connectedRemoteCount"], "folderStatus": db, "serverManifest": manifest, "manifestMatchesSource": True, "onboardingState": onboarding, "note": "服务器内容指纹与 PC 提供的指纹一致；确保两端写入者在整个核验窗口内停写。"}


@_serialized_transition
def _verify_seed(args: argparse.Namespace, codex_home: Path, vault: Path, api: LocalSyncthingAPI) -> dict[str, Any]:
    return _verify_seed_impl(args, codex_home, vault, api)


def _apply_promotion_operation(
    args: argparse.Namespace,
    codex_home: Path,
    vault: Path,
    api: LocalSyncthingAPI,
    *,
    action: str,
    role: str,
    own_id: str,
    peer_id: str,
    source_folder_type: str,
    baseline_sha256: str,
    peer_manifest_sha256: str,
    prior_verified: dict[str, Any],
    recovery_pending: dict[str, Any] | None,
) -> dict[str, Any]:
    backup = _backup_config(codex_home, api.profile, vault)
    _PROGRESS["backupPath"] = str(backup)
    operation: dict[str, Any] | None = None
    try:
        operation = base.begin_sync_onboarding_operation(
            codex_home,
            role,
            action=action,
            syncthing_device_id=own_id,
            peer_syncthing_device_id=peer_id,
            vault_path=str(vault),
            expected_folder_type="sendreceive",
            source_folder_type=source_folder_type,
            baseline_manifest_sha256=baseline_sha256,
            peer_manifest_sha256=peer_manifest_sha256,
            backup_path=str(backup),
            confirmations={"promotionApproved": True, "writersPaused": True, "peerStageVerified": True},
        )
        _PROGRESS["pendingOperationId"] = operation["operationId"]
        _PROGRESS["completed"].append("已持久化晋级意图、源/目标模式与双端内容指纹基线")
        if recovery_pending is not None:
            _invalidate_containment_evidence()
            _PROGRESS["phase"] = "resume-peer-for-promotion-recovery"
            api.request("PATCH", f"/rest/config/devices/{quote(peer_id, safe='')}", {"paused": False})
            _PROGRESS["phase"] = "resume-folder-for-promotion-recovery"
            api.request("PATCH", f"/rest/config/folders/{quote(FOLDER_ID, safe='')}", {"paused": False})
            _PROGRESS["phase"] = "scan-promotion-recovery-folder"
            api.request("POST", f"/rest/db/scan?folder={quote(FOLDER_ID, safe='')}")
        _PROGRESS["phase"] = "verify-promotion-live-baseline"
        allowed_types = {source_folder_type, "sendreceive"}
        before = _wait_for_promotion_live_state(
            codex_home, vault, role, api, peer_id, own_id, baseline_sha256, allowed_types
        )
        if before["folder"].get("type") == source_folder_type:
            _invalidate_containment_evidence()
            _PROGRESS["phase"] = "promote-folder-mode"
            api.request("PATCH", f"/rest/config/folders/{quote(FOLDER_ID, safe='')}", {"type": "sendreceive"})
        _PROGRESS["phase"] = "verify-promoted-folder-mode"
        folders = api.request("GET", "/rest/config/folders")
        if not isinstance(folders, list) or any(not isinstance(item, dict) for item in folders):
            raise PairingError("promotion-verification-failed", "晋级后 Syncthing 文件夹列表无法核验。")
        actual = _target_folder(folders, vault)
        if actual.get("type") != "sendreceive" or actual.get("paused") is not False:
            raise PairingError("promotion-verification-failed", "晋级后 folder 类型或暂停状态不符合预期。")
        _PROGRESS["phase"] = "verify-promoted-live-state"
        after = _wait_for_promotion_live_state(
            codex_home, vault, role, api, peer_id, own_id, baseline_sha256, {"sendreceive"}
        )
        completion = "server-promoted" if role == "server" else "primary-promoted"
        _PROGRESS["phase"] = "commit-promotion-stage"
        onboarding = base.complete_sync_onboarding_operation(codex_home, role, operation["operationId"], completion)
        _PROGRESS["phase"] = "complete"
    except KeyboardInterrupt:
        _contain_and_hold_failed_operation(codex_home, role, vault, api, operation)
        raise
    except Exception:
        _contain_and_hold_failed_operation(codex_home, role, vault, api, operation)
        raise
    return {
        "status": completion,
        "role": role,
        "folderType": after["folder"].get("type"),
        "folderPaused": after["folder"].get("paused"),
        "manifest": after["manifest"],
        "priorVerification": prior_verified,
        "onboardingState": onboarding,
        "backupPath": str(backup),
        "recoveredInterruptedOperation": recovery_pending is not None,
        "note": "晋级后 folder、peer、idle 状态和稳定内容指纹均已重新核验。另一设备仍需按顺序完成其阶段；双向写入探针未执行。",
    }


@_serialized_transition
def _promote_server(args: argparse.Namespace, codex_home: Path, vault: Path, api: LocalSyncthingAPI) -> dict[str, Any]:
    if args.role != "server":
        raise PairingError("role-conflict", "仅 server 设备可执行服务器晋级。")
    if not (args.confirmed_verified and args.confirmed_writers_paused and args.confirmed_peer_state):
        raise PairingError("promotion-confirmation-required", "服务器晋级需要确认源指纹、两端写入者停写、PC 仍处于正确的单向阶段，并授权本次晋级。")
    expected_source_hash = _require_sha256(args.source_manifest_sha256, "source-manifest-sha256")
    recovery_pending = _recover_pending_promotion(
        args, codex_home, vault, api, action="promote-server", source_folder_type="receiveonly",
        peer_manifest_sha256=expected_source_hash,
    )
    onboarding_before = _onboarding_state(codex_home, args.role)
    if onboarding_before.get("status") not in {"seed-verified", "server-promoted", "active"}:
        raise PairingError("promotion-order-conflict", "服务器尚未进入 seed-verified 阶段；不允许跳过首次接收核验。")
    own_id, devices, folders = _device_records(api)
    remotes = _known_remote_devices(codex_home, args.role, devices, own_id)
    if len(remotes) != 1:
        raise PairingError("peer-not-paired", "未找到唯一的 PC 对端。")
    peer_id = str(remotes[0]["deviceID"])
    existing = _target_folder(folders, vault)
    if recovery_pending is None and existing.get("type") == "sendreceive":
        live = _wait_for_promotion_live_state(
            codex_home, vault, args.role, api, peer_id, own_id, expected_source_hash, {"sendreceive"}
        )
        onboarding = base.write_sync_onboarding_state(codex_home, args.role, "server-promoted")
        verified = {"status": "already-server-promoted", "serverManifest": live["manifest"], "manifestMatchesSource": True}
        return {"status": "already-server-promoted", "role": args.role, "folderType": live["folder"].get("type"), "folderPaused": live["folder"].get("paused"), "seedVerification": verified, "onboardingState": onboarding, "note": "服务器晋级状态与内容指纹已复核；未重复修改配置。PC 仍应保持 sendonly。"}

    if recovery_pending is not None:
        baseline = str(recovery_pending["baselineManifestSha256"])
        folder = _target_folder(folders, vault)
        verified = {"status": "recovered-promotion-baseline", "serverManifestSha256": baseline, "manifestMatchesSource": True, "previousType": folder.get("type")}
    else:
        verified = _verify_seed_impl(args, codex_home, vault, api)
        baseline = str(verified["serverManifest"]["manifestSha256"])
    return _apply_promotion_operation(
        args, codex_home, vault, api, action="promote-server", role=args.role,
        own_id=own_id, peer_id=peer_id, source_folder_type="receiveonly",
        baseline_sha256=baseline, peer_manifest_sha256=expected_source_hash,
        prior_verified=verified, recovery_pending=recovery_pending,
    )


@_serialized_transition
def _promote_primary(args: argparse.Namespace, codex_home: Path, vault: Path, api: LocalSyncthingAPI) -> dict[str, Any]:
    if args.role != "primary":
        raise PairingError("role-conflict", "仅 primary 设备可执行 PC 晋级。")
    if not (args.confirmed_verified and args.confirmed_writers_paused and args.confirmed_peer_state):
        raise PairingError("promotion-confirmation-required", "PC 晋级需要确认服务器已为 sendreceive、双方写入者停写、内容指纹一致，并授权本次晋级。")
    expected_server_hash = _require_sha256(args.server_manifest_sha256, "server-manifest-sha256")
    recovery_pending = _recover_pending_promotion(
        args, codex_home, vault, api, action="promote-primary", source_folder_type="sendonly",
        peer_manifest_sha256=expected_server_hash,
    )
    onboarding_before = _onboarding_state(codex_home, args.role)
    if onboarding_before.get("status") not in {"seeding", "primary-promoted", "active"}:
        raise PairingError("promotion-order-conflict", "PC 尚未进入 seeding 阶段；不允许跳过首次播种。")
    own_id, devices, folders = _device_records(api)
    remotes = _known_remote_devices(codex_home, args.role, devices, own_id)
    if len(remotes) != 1:
        raise PairingError("peer-not-paired", "未找到唯一的服务器对端。")
    peer_id = str(remotes[0]["deviceID"])
    folder = _target_folder(folders, vault)
    if recovery_pending is None and folder.get("type") not in {"sendonly", "sendreceive"}:
        raise PairingError("promotion-state-conflict", "PC 源端必须仍为 sendonly。")
    if recovery_pending is not None:
        baseline = str(recovery_pending["baselineManifestSha256"])
        verified = {"status": "recovered-promotion-baseline", "serverManifestSha256": baseline, "manifestMatchesServer": True, "previousType": folder.get("type")}
    else:
        baseline = expected_server_hash
        if folder.get("type") == "sendreceive":
            live = _wait_for_promotion_live_state(
                codex_home, vault, args.role, api, peer_id, own_id, baseline, {"sendreceive"}
            )
            onboarding = base.write_sync_onboarding_state(codex_home, args.role, "primary-promoted")
            return {"status": "already-primary-promoted", "role": args.role, "folderType": live["folder"].get("type"), "folderPaused": live["folder"].get("paused"), "manifest": live["manifest"], "onboardingState": onboarding, "note": "PC 晋级状态与内容指纹已复核；未重复修改配置。双向写入探针仍未执行。"}
        live = _wait_for_promotion_live_state(
            codex_home, vault, args.role, api, peer_id, own_id, baseline, {"sendonly"}
        )
        verified = {"status": "primary-pre-promotion-verified", "manifest": live["manifest"], "manifestMatchesServer": True}
    return _apply_promotion_operation(
        args, codex_home, vault, api, action="promote-primary", role=args.role,
        own_id=own_id, peer_id=peer_id, source_folder_type="sendonly",
        baseline_sha256=baseline, peer_manifest_sha256=expected_server_hash,
        prior_verified=verified, recovery_pending=recovery_pending,
    )


@_serialized_transition
def _complete(args: argparse.Namespace, codex_home: Path, vault: Path, api: LocalSyncthingAPI) -> dict[str, Any]:
    _assert_no_pending_operation(codex_home, args.role)
    if not args.confirmed_bidirectional:
        raise PairingError("bidirectional-confirmation-required", "只有在两端 Codex 报告都已为 sendreceive、双方内容指纹相等且用户确认后，才能结束首次引导。")
    expected_peer_hash = _require_sha256(args.peer_manifest_sha256, "peer-manifest-sha256")
    expected_stage = "primary-promoted" if args.role == "primary" else "server-promoted"
    current_stage = _onboarding_state(codex_home, args.role).get("status")
    if current_stage not in {expected_stage, "active"}:
        raise PairingError("completion-order-conflict", "本机尚未完成对应角色的双向模式晋级；不能跳过配置阶段。")
    own_id, devices, folders = _device_records(api)
    remotes = _known_remote_devices(codex_home, args.role, devices, own_id)
    if len(remotes) != 1:
        raise PairingError("peer-not-paired", "未找到唯一的已配对设备。")
    peer_id = str(remotes[0].get("deviceID", ""))
    folder = _target_folder(folders, vault)
    folder_members = _folder_member_ids(folder)
    expected_members = {
        base._normalized_device_id(own_id),
        base._normalized_device_id(peer_id),
    }
    if len(folder_members) != 2 or set(folder_members) != expected_members:
        raise PairingError(
            "completion-folder-membership-conflict",
            "目标 Vault 文件夹成员必须恰为本机与已绑定对端；保留当前状态，不标记引导完成。",
        )
    if folder.get("type") != "sendreceive" or folder.get("paused") is not False:
        raise PairingError("bidirectional-state-conflict", "本机文件夹尚未处于活动 sendreceive 状态。")
    connected, connected_ids = _connections(api, own_id)
    valid_connected_ids = [device_id.strip().upper() for device_id in connected_ids]
    if (connected != 1 or len(valid_connected_ids) != 1
            or not DEVICE_ID_RE.fullmatch(valid_connected_ids[0])
            or base._normalized_device_id(valid_connected_ids[0]) != base._normalized_device_id(peer_id)):
        raise PairingError(
            "completion-peer-connection-conflict",
            "唯一活动连接必须对应本机引导状态绑定的对端；保留当前状态，不标记引导完成。",
        )
    db = _folder_status(api)
    manifest = _file_manifest(vault)
    if (not _folder_is_idle_and_clean(db)
            or manifest["manifestSha256"] != expected_peer_hash):
        raise PairingError("bidirectional-state-conflict", "本机与对端未满足连接、idle、无待同步项/错误和内容指纹一致的条件。")
    state = base.write_sync_onboarding_state(codex_home, args.role, "active")
    return {"status": "active", "role": args.role, "syncthingDeviceId": own_id, "peerSyncthingDeviceId": peer_id, "folderId": FOLDER_ID, "folderType": folder.get("type"), "folderPaused": folder.get("paused"), "folderMembershipMatchesPair": True, "connectedRemoteCount": connected, "connectedDeviceIds": connected_ids, "folderStatus": db, "manifest": manifest, "onboardingState": state, "bidirectionalSmokeProbe": "not-run; would modify Vault content and needs separate user approval"}


@_serialized_transition
def _pause(args: argparse.Namespace, codex_home: Path, vault: Path, profile: Path, api: LocalSyncthingAPI) -> dict[str, Any]:
    onboarding = _onboarding_state(codex_home, args.role)
    pending = onboarding.get("pendingOperation")
    if pending is not None and not isinstance(pending, dict):
        raise PairingError("onboarding-operation-invalid", "待执行状态损坏；未声称同步已停止。")
    if isinstance(pending, dict):
        containment = _safe_contain_pending_operation(api, vault, pending)
        _persist_held_operation(codex_home, args.role, pending, containment)
        if not containment.get("containmentVerified"):
            raise PairingError("pause-verification-failed", "未能核实待处理操作的文件夹和对端均已暂停；详见 containment 状态。")
        return {"status": "paused-held", "role": args.role, "folderId": FOLDER_ID, "containment": containment, "note": "目标 folder 与已记录的唯一对端均已核实暂停；未删除或覆盖数据。"}
    _, _, folders = _device_records(api)
    _target_folder(folders, vault)
    backup = _backup_config(codex_home, profile, vault)
    api.request("PATCH", f"/rest/config/folders/{quote(FOLDER_ID, safe='')}", {"paused": True})
    current = api.request("GET", "/rest/config/folders")
    if not isinstance(current, list) or not all(isinstance(item, dict) for item in current):
        raise PairingError("pause-verification-failed", "目标文件夹暂停状态无法核实。")
    folder = _target_folder(current, vault)
    if folder.get("paused") is not True:
        raise PairingError("pause-verification-failed", "目标文件夹暂停状态无法核实。")
    return {"status": "paused", "role": args.role, "folderId": FOLDER_ID, "folderType": folder.get("type"), "folderPaused": folder.get("paused"), "backupPath": str(backup), "note": "文件夹已暂停；未删除或覆盖文件。"}


def main() -> None:
    _PROGRESS.clear()
    _PROGRESS.update({"phase": "preflight", "completed": [], "backupPath": None, "containment": None, "containmentVerified": False, "containmentStatus": "not-attempted"})
    parser = argparse.ArgumentParser(description="Codex-invoked Syncthing Second Brain pairing helper")
    parser.add_argument("action", choices=("card", "pair", "arm-receiver", "start-source", "status", "manifest", "verify-seed", "promote-server", "promote-primary", "complete", "pause"))
    parser.add_argument("--codex-home")
    parser.add_argument("--vault-path", required=True)
    parser.add_argument("--role", choices=("primary", "server"), required=True)
    parser.add_argument("--peer-device-id")
    parser.add_argument("--peer-label")
    parser.add_argument("--device-label", default="")
    parser.add_argument("--confirmed-network-metadata", action="store_true")
    parser.add_argument("--confirmed-arm-receiver", action="store_true")
    parser.add_argument("--confirmed-receiver-ready", action="store_true")
    parser.add_argument("--confirmed-writers-paused", action="store_true")
    parser.add_argument("--source-manifest-sha256", default="")
    parser.add_argument("--server-manifest-sha256", default="")
    parser.add_argument("--peer-manifest-sha256", default="")
    parser.add_argument("--confirmed-verified", action="store_true")
    parser.add_argument("--confirmed-peer-state", action="store_true")
    parser.add_argument("--confirmed-bidirectional", action="store_true")
    args = parser.parse_args()
    try:
        codex_home = _codex_home(args.codex_home)
        vault_arg = Path(os.path.expandvars(os.path.expanduser(args.vault_path)))
        if not vault_arg.is_absolute():
            raise PairingError("vault-path-invalid", "Vault 路径必须为绝对路径。")
        if vault_arg.is_symlink() or getattr(vault_arg, "is_junction", lambda: False)():
            raise PairingError("vault-path-invalid", "Vault 路径为符号链接或 junction；拒绝跟随到其他位置。")
        vault = vault_arg.resolve()
        if not vault.is_dir() or vault.is_symlink():
            raise PairingError("vault-path-invalid", "Vault 路径不存在、不是目录或为符号链接。")
        config = _read_device_config(codex_home, vault, args.role)
        if args.action == "manifest":
            print(json.dumps(_file_manifest(vault), ensure_ascii=False, indent=2))
            return
        profile, executable = _profile()
        own_id_cli = base.verify_local_device_identity(executable, profile, _device_id(LocalSyncthingAPI(profile)))
        api = LocalSyncthingAPI(profile)
        own_id, devices, folders = _device_records(api)
        if base._normalized_device_id(own_id_cli) != base._normalized_device_id(own_id):
            raise PairingError("device-id-mismatch", "运行时 API 与本机证书派生 Device ID 不一致。")
        if args.action == "card":
            label = str(config.get("deviceLabel") or args.device_label or "")
            _known_remote_devices(codex_home, args.role, devices, own_id)
            folder = _target_folder(folders, vault)
            print(json.dumps({"status": "pairing-card", "deviceLabel": label, "syncthingDeviceId": own_id, "folderId": FOLDER_ID, "role": args.role, "transferPolicy": "PC sendonly -> server receiveonly; paused until both endpoints are paired", "networkPolicy": "public discovery + official relay; TCP loopback + official dynamic relay address; LAN discovery/announcement and Syncthing NAT mapping off; no router/firewall changes", "vaultPathIncluded": False, "credentialsIncluded": False, "secondBrainDeviceIdIncluded": False, "folderType": folder.get("type"), "folderPaused": folder.get("paused")}, ensure_ascii=False, indent=2))
            return
        if args.action == "pair":
            if not args.peer_device_id or not args.peer_label:
                raise PairingError("peer-card-required", "配对需要另一设备 pairing card 中的 Syncthing Device ID 与标签。")
            args.device_label = str(config.get("deviceLabel") or args.device_label or "")
            print(json.dumps(_pair(args, codex_home, vault, profile, api), ensure_ascii=False, indent=2))
            return
        if args.action == "arm-receiver":
            print(json.dumps(_arm_receiver(args, codex_home, vault, api), ensure_ascii=False, indent=2))
            return
        if args.action == "start-source":
            print(json.dumps(_start_source(args, codex_home, vault, api), ensure_ascii=False, indent=2))
            return
        if args.action == "status":
            print(json.dumps(_status(codex_home, vault, args.role, api), ensure_ascii=False, indent=2))
            return
        if args.action == "verify-seed":
            print(json.dumps(_verify_seed(args, codex_home, vault, api), ensure_ascii=False, indent=2))
            return
        if args.action == "promote-server":
            print(json.dumps(_promote_server(args, codex_home, vault, api), ensure_ascii=False, indent=2))
            return
        if args.action == "promote-primary":
            print(json.dumps(_promote_primary(args, codex_home, vault, api), ensure_ascii=False, indent=2))
            return
        if args.action == "complete":
            print(json.dumps(_complete(args, codex_home, vault, api), ensure_ascii=False, indent=2))
            return
        if args.action == "pause":
            print(json.dumps(_pause(args, codex_home, vault, profile, api), ensure_ascii=False, indent=2))
            return
    except KeyboardInterrupt:
        containment_fields = _containment_report_fields()
        print(json.dumps({"status": "blocked", "operationOutcome": "interrupted", "code": "user-interrupted", "message": "操作被中断；保留备份与待处理状态。请依据当前 containment 状态判断是否已核实暂停。", **containment_fields, "progress": dict(_PROGRESS)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(130)
    except (PairingError, base.SetupError) as exc:
        code = exc.code if hasattr(exc, "code") else "setup-error"
        containment_fields = _containment_report_fields()
        print(json.dumps({"status": "blocked", "operationOutcome": "failed", "code": code, "message": str(exc), **containment_fields, "progress": dict(_PROGRESS)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(2)
    except OSError as exc:
        containment_fields = _containment_report_fields()
        print(json.dumps({"status": "blocked", "operationOutcome": "failed", "code": "filesystem-operation-failed", "message": f"本机文件操作失败（{exc.strerror or type(exc).__name__}）；保留已有数据和备份。", **containment_fields, "progress": dict(_PROGRESS)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
