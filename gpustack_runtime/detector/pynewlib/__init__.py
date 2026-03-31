"""
Python ctypes bindings for NewChip management library (libXXXml.so).

TODO: Replace this template with actual bindings for the target chip vendor.
      This module wraps the vendor's native C management library.
"""

from __future__ import annotations as __future_annotations__

import ctypes
import ctypes.util
import threading

# Lock for library initialization.
libLoadLock = threading.Lock()

# Library state.
_lib = None
_libInitialized = False
_libInitializedException = None


class XXXmlError(Exception):
    """Exception for XXXml library errors."""


def _check_ret(ret: int, func_name: str):
    """Check return value and raise XXXmlError on failure."""
    if ret != 0:
        raise XXXmlError(f"{func_name} failed with error code {ret}")


def _load_library():
    """Load the shared library."""
    global _lib
    if _lib is not None:
        return _lib

    # TODO: Replace "XXXml" with the actual library name.
    # The library is typically located at /usr/lib or /opt/<vendor>/lib.
    lib_name = ctypes.util.find_library("XXXml")
    if not lib_name:
        raise XXXmlError("Cannot find libXXXml.so")

    _lib = ctypes.CDLL(lib_name)
    return _lib


def XXXmlInit():
    """Initialize the library (idempotent)."""
    global _libInitialized, _libInitializedException

    if _libInitialized:
        if _libInitializedException is not None:
            raise _libInitializedException
        return

    try:
        lib = _load_library()
        ret = lib.XXXml_init()
        _check_ret(ret, "XXXml_init")
    except Exception as e:
        with libLoadLock:
            _libInitializedException = e
        raise
    finally:
        with libLoadLock:
            _libInitialized = True


def XXXmlShutdown():
    """Shutdown the library."""
    global _libInitialized, _libInitializedException

    if not _libInitialized:
        return

    lib = _load_library()
    lib.XXXml_shutdown()

    with libLoadLock:
        if not _libInitialized:
            return
        _libInitialized = False
        _libInitializedException = None


def XXXmlGetDeviceCount() -> int:
    """Get the number of devices."""
    lib = _load_library()
    count = ctypes.c_int()
    ret = lib.XXXml_get_device_count(ctypes.byref(count))
    _check_ret(ret, "XXXml_get_device_count")
    return count.value


def XXXmlGetDeviceName(index: int) -> str:
    """Get device name by index."""
    lib = _load_library()
    buf = ctypes.create_string_buffer(256)
    ret = lib.XXXml_get_device_name(index, buf, 256)
    _check_ret(ret, "XXXml_get_device_name")
    return buf.value.decode("utf-8")


def XXXmlGetDeviceUUID(index: int) -> str:
    """Get device UUID by index."""
    lib = _load_library()
    buf = ctypes.create_string_buffer(256)
    ret = lib.XXXml_get_device_uuid(index, buf, 256)
    _check_ret(ret, "XXXml_get_device_uuid")
    return buf.value.decode("utf-8")


def XXXmlGetDriverVersion() -> str:
    """Get driver version string."""
    lib = _load_library()
    buf = ctypes.create_string_buffer(256)
    ret = lib.XXXml_get_driver_version(buf, 256)
    _check_ret(ret, "XXXml_get_driver_version")
    return buf.value.decode("utf-8")


def XXXmlGetDeviceCores(index: int) -> int:
    """Get total compute cores for the device."""
    lib = _load_library()
    cores = ctypes.c_int()
    ret = lib.XXXml_get_device_cores(index, ctypes.byref(cores))
    _check_ret(ret, "XXXml_get_device_cores")
    return cores.value


def XXXmlGetDeviceMemTotal(index: int) -> int:
    """Get total memory in bytes."""
    lib = _load_library()
    total = ctypes.c_uint64()
    ret = lib.XXXml_get_device_mem_total(index, ctypes.byref(total))
    _check_ret(ret, "XXXml_get_device_mem_total")
    return total.value


def XXXmlGetDeviceMemUsed(index: int) -> int:
    """Get used memory in bytes."""
    lib = _load_library()
    used = ctypes.c_uint64()
    ret = lib.XXXml_get_device_mem_used(index, ctypes.byref(used))
    _check_ret(ret, "XXXml_get_device_mem_used")
    return used.value


def XXXmlGetDeviceUtilization(index: int) -> int:
    """Get device core utilization percentage (0-100)."""
    lib = _load_library()
    util = ctypes.c_int()
    ret = lib.XXXml_get_device_utilization(index, ctypes.byref(util))
    _check_ret(ret, "XXXml_get_device_utilization")
    return util.value


def XXXmlGetDeviceTemperature(index: int) -> int:
    """Get device temperature in Celsius."""
    lib = _load_library()
    temp = ctypes.c_int()
    ret = lib.XXXml_get_device_temperature(index, ctypes.byref(temp))
    _check_ret(ret, "XXXml_get_device_temperature")
    return temp.value


def XXXmlGetDevicePowerUsage(index: int) -> float:
    """Get device power usage in Watts."""
    lib = _load_library()
    power = ctypes.c_float()
    ret = lib.XXXml_get_device_power_usage(index, ctypes.byref(power))
    _check_ret(ret, "XXXml_get_device_power_usage")
    return power.value


def XXXmlGetDeviceEccErrors(index: int) -> int:
    """Get uncorrected ECC error count."""
    lib = _load_library()
    errors = ctypes.c_uint64()
    ret = lib.XXXml_get_device_ecc_errors(index, ctypes.byref(errors))
    _check_ret(ret, "XXXml_get_device_ecc_errors")
    return errors.value


class _PciInfo(ctypes.Structure):
    _fields_ = [
        ("segment", ctypes.c_uint16),
        ("bus", ctypes.c_uint8),
        ("device", ctypes.c_uint8),
        ("function", ctypes.c_uint8),
    ]


def XXXmlGetDevicePciInfo(index: int) -> _PciInfo:
    """Get device PCI info (segment, bus, device, function)."""
    lib = _load_library()
    info = _PciInfo()
    ret = lib.XXXml_get_device_pci_info(index, ctypes.byref(info))
    _check_ret(ret, "XXXml_get_device_pci_info")
    return info
