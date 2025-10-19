"""Windows CoreAudio helpers for adjusting system and application volume."""

from __future__ import annotations

import ctypes
import logging
import os
from pathlib import Path
from typing import Iterable, List, Set

from ctypes import POINTER, byref, cast
from ctypes.wintypes import BOOL, DWORD, GUID, LPCWSTR, UINT

LOGGER = logging.getLogger(__name__)

if os.name != "nt":  # pragma: no cover - platform guard
    raise ImportError("windows.audio is only available on Windows platforms")

ole32 = ctypes.windll.ole32
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi

CLSCTX_ALL = 0x17
COINIT_APARTMENTTHREADED = 0x2

ERender = UINT(0)
ERoleMultimedia = UINT(1)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010


def _guid(value: str) -> GUID:
    guid = GUID()
    hr = ole32.CLSIDFromString(LPCWSTR(value), byref(guid))
    if hr != 0:
        raise OSError(hr, f"Failed to parse GUID {value}")
    return guid


CLSID_MMDeviceEnumerator = _guid("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
IID_IMMDeviceEnumerator = _guid("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
IID_IAudioEndpointVolume = _guid("{5CDF2C82-841E-4546-9722-0CF74078229A}")
IID_IAudioSessionManager2 = _guid("{77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F}")
IID_IAudioSessionEnumerator = _guid("{E2F5BB11-0570-40CA-ACDD-3AA01277DEE8}")
IID_IAudioSessionControl2 = _guid("{BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D}")
IID_ISimpleAudioVolume = _guid("{87CE5498-68D6-44E5-9215-6DA47EF883D8}")


def _check_hresult(result: int, message: str) -> None:
    if result != 0:
        raise OSError(result, message)


def _invoke(ptr: ctypes.c_void_p, index: int, restype, argtypes: Iterable[object], *args):
    vtable = cast(ptr, POINTER(POINTER(ctypes.c_void_p))).contents
    func_type = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    func = func_type(vtable[index])
    return func(ptr, *args)


def _release(ptr: ctypes.c_void_p) -> None:
    if ptr:
        _invoke(ptr, 2, ctypes.c_ulong, ())


def _query_interface(ptr: ctypes.c_void_p, iid: GUID) -> ctypes.c_void_p:
    result = ctypes.c_void_p()
    hr = _invoke(ptr, 0, ctypes.c_long, (POINTER(GUID), POINTER(ctypes.c_void_p)), byref(iid), byref(result))
    _check_hresult(hr, "QueryInterface failed")
    return result


class ComContext:
    """Context manager for initializing and uninitializing COM."""

    def __enter__(self) -> "ComContext":
        hr = ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
        if hr not in (0, 0x00000001):  # S_OK or S_FALSE
            _check_hresult(hr, "CoInitializeEx failed")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        ole32.CoUninitialize()


def _create_enumerator() -> ctypes.c_void_p:
    enumerator = ctypes.c_void_p()
    hr = ole32.CoCreateInstance(
        byref(CLSID_MMDeviceEnumerator),
        None,
        CLSCTX_ALL,
        byref(IID_IMMDeviceEnumerator),
        byref(enumerator),
    )
    _check_hresult(hr, "Unable to create MMDeviceEnumerator")
    return enumerator


def _get_default_device(enumerator: ctypes.c_void_p) -> ctypes.c_void_p:
    device = ctypes.c_void_p()
    hr = _invoke(
        enumerator,
        4,
        ctypes.c_long,
        (UINT, UINT, POINTER(ctypes.c_void_p)),
        ERender,
        ERoleMultimedia,
        byref(device),
    )
    _check_hresult(hr, "Failed to fetch default audio endpoint")
    return device


def _activate(device: ctypes.c_void_p, iid: GUID) -> ctypes.c_void_p:
    interface = ctypes.c_void_p()
    hr = _invoke(
        device,
        3,
        ctypes.c_long,
        (POINTER(GUID), DWORD, ctypes.c_void_p, POINTER(ctypes.c_void_p)),
        byref(iid),
        DWORD(CLSCTX_ALL),
        None,
        byref(interface),
    )
    _check_hresult(hr, "Failed to activate interface")
    return interface


def set_master_volume(percent: int) -> None:
    level = max(0.0, min(1.0, percent / 100.0))
    with ComContext():
        enumerator = _create_enumerator()
        try:
            device = _get_default_device(enumerator)
            try:
                endpoint = _activate(device, IID_IAudioEndpointVolume)
                try:
                    hr = _invoke(
                        endpoint,
                        7,
                        ctypes.c_long,
                        (ctypes.c_float, ctypes.c_void_p),
                        ctypes.c_float(level),
                        None,
                    )
                    _check_hresult(hr, "Failed to set master volume")
                finally:
                    _release(endpoint)
            finally:
                _release(device)
        finally:
            _release(enumerator)


def _iter_sessions(session_enum: ctypes.c_void_p):
    count = ctypes.c_int()
    hr = _invoke(session_enum, 3, ctypes.c_long, (POINTER(ctypes.c_int),), byref(count))
    _check_hresult(hr, "Failed to enumerate sessions")
    for index in range(count.value):
        session = ctypes.c_void_p()
        hr = _invoke(session_enum, 4, ctypes.c_long, (ctypes.c_int, POINTER(ctypes.c_void_p)), index, byref(session))
        _check_hresult(hr, "Failed to fetch session")
        try:
            yield session
        finally:
            _release(session)


def _process_name_from_pid(pid: int) -> str | None:
    access = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_QUERY_LIMITED_INFORMATION
    handle = kernel32.OpenProcess(access, BOOL(False), DWORD(pid))
    if not handle:
        return None
    try:
        buffer = ctypes.create_unicode_buffer(512)
        length = psapi.GetModuleFileNameExW(handle, None, buffer, len(buffer))
        if length == 0:
            return None
        return Path(buffer.value).name
    finally:
        kernel32.CloseHandle(handle)


def _match_process(target: str, process_name: str | None) -> bool:
    if not process_name:
        return False
    target_norm = target.lower()
    proc_norm = process_name.lower()
    if target_norm == proc_norm:
        return True
    if proc_norm.endswith(".exe") and target_norm == proc_norm[:-4]:
        return True
    if target_norm.endswith(".exe") and target_norm[:-4] == proc_norm:
        return True
    return target_norm in proc_norm


def _session_process_name(session: ctypes.c_void_p) -> str | None:
    try:
        session_control = _query_interface(session, IID_IAudioSessionControl2)
    except OSError:
        return None
    try:
        pid = DWORD()
        hr = _invoke(session_control, 14, ctypes.c_long, (POINTER(DWORD),), byref(pid))
        _check_hresult(hr, "Failed to read session process id")
        return _process_name_from_pid(pid.value)
    finally:
        _release(session_control)


def _set_session_volume(session: ctypes.c_void_p, process_hint: str, level: float) -> bool:
    try:
        session_control = _query_interface(session, IID_IAudioSessionControl2)
    except OSError:
        return False
    try:
        pid = DWORD()
        hr = _invoke(session_control, 14, ctypes.c_long, (POINTER(DWORD),), byref(pid))
        _check_hresult(hr, "Failed to read session process id")
        process_name = _process_name_from_pid(pid.value)
        if not _match_process(process_hint, process_name):
            return False
        simple_volume = _query_interface(session, IID_ISimpleAudioVolume)
        try:
            hr = _invoke(
                simple_volume,
                3,
                ctypes.c_long,
                (ctypes.c_float, ctypes.c_void_p),
                ctypes.c_float(level),
                None,
            )
            _check_hresult(hr, "Failed to set application volume")
            return True
        finally:
            _release(simple_volume)
    finally:
        _release(session_control)


def set_application_volume(process_hint: str, percent: int) -> bool:
    level = max(0.0, min(1.0, percent / 100.0))
    matched = False
    with ComContext():
        enumerator = _create_enumerator()
        try:
            device = _get_default_device(enumerator)
            try:
                session_manager = _activate(device, IID_IAudioSessionManager2)
                try:
                    session_enum = ctypes.c_void_p()
                    hr = _invoke(
                        session_manager,
                        5,
                        ctypes.c_long,
                        (POINTER(ctypes.c_void_p),),
                        byref(session_enum),
                    )
                    _check_hresult(hr, "Failed to obtain session enumerator")
                    try:
                        for session in _iter_sessions(session_enum):
                            if _set_session_volume(session, process_hint, level):
                                matched = True
                    finally:
                        _release(session_enum)
                finally:
                    _release(session_manager)
            finally:
                _release(device)
        finally:
            _release(enumerator)
    return matched


def list_audio_sessions() -> List[str]:
    """Return the names of processes with active audio sessions."""

    sessions: Set[str] = set()

    with ComContext():
        enumerator = _create_enumerator()
        try:
            device = _get_default_device(enumerator)
            try:
                session_manager = _activate(device, IID_IAudioSessionManager2)
                try:
                    session_enum = ctypes.c_void_p()
                    hr = _invoke(
                        session_manager,
                        5,
                        ctypes.c_long,
                        (POINTER(ctypes.c_void_p),),
                        byref(session_enum),
                    )
                    _check_hresult(hr, "Failed to obtain session enumerator")
                    try:
                        for session in _iter_sessions(session_enum):
                            process_name = _session_process_name(session)
                            if process_name:
                                sessions.add(process_name)
                    finally:
                        _release(session_enum)
                finally:
                    _release(session_manager)
            finally:
                _release(device)
        finally:
            _release(enumerator)

    return sorted(sessions, key=str.casefold)


__all__ = ["set_master_volume", "set_application_volume", "list_audio_sessions"]
