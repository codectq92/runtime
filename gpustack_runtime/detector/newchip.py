"""
NewChip GPU Detector.

TODO: Replace all placeholder values (PCI vendor ID, library calls, etc.)
      with actual implementations for the target chip vendor.
"""

from __future__ import annotations as __future_annotations__

import logging
from functools import lru_cache

from .. import envs
from ..logging import debug_log_exception, debug_log_warning
from . import DeviceMemoryStatusEnum, pynewlib
from .__types__ import (
    Detector,
    Device,
    Devices,
    ManufacturerEnum,
    Topology,
    TopologyDistanceEnum,
)
from .__utils__ import (
    PCIDevice,
    byte_to_mebibyte,
    get_numa_node_by_bdf,
    get_pci_devices,
    get_utilization,
    map_numa_node_to_cpu_affinity,
)

logger = logging.getLogger(__name__)


class NewChipDetector(Detector):
    """
    Detect NewChip GPUs.
    """

    @staticmethod
    @lru_cache(maxsize=1)
    def is_supported() -> bool:
        """
        Check if the NewChip detector is supported.

        Returns:
            True if supported, False otherwise.

        """
        supported = False
        if envs.GPUSTACK_RUNTIME_DETECT.lower() not in ("auto", "newchip"):
            logger.debug("NewChip detection is disabled by environment variable")
            return supported

        pci_devs = NewChipDetector.detect_pci_devices()
        if not pci_devs and not envs.GPUSTACK_RUNTIME_DETECT_NO_PCI_CHECK:
            logger.debug("No NewChip PCI devices found")
            return supported

        try:
            pynewlib.XXXmlInit()
            supported = True
        except pynewlib.XXXmlError:
            debug_log_exception(logger, "Failed to initialize XXXml")

        return supported

    @staticmethod
    @lru_cache(maxsize=1)
    def detect_pci_devices() -> dict[str, PCIDevice]:
        # TODO: Replace "0xNNNN" with the actual PCI vendor ID.
        # See https://pcisig.com/membership/member-companies.
        pci_devs = get_pci_devices(vendor="0xNNNN")
        if not pci_devs:
            return {}
        return {dev.address: dev for dev in pci_devs}

    def __init__(self):
        super().__init__(ManufacturerEnum.NEWCHIP)

    def detect(self) -> Devices | None:
        """
        Detect NewChip GPUs using libXXXml.

        Returns:
            A list of detected NewChip GPU devices,
            or None if not supported.

        Raises:
            If there is an error during detection.

        """
        if not self.is_supported():
            return None

        ret: Devices = []

        try:
            pynewlib.XXXmlInit()
            sys_driver_ver = pynewlib.XXXmlGetDriverVersion()
            dev_count = pynewlib.XXXmlGetDeviceCount()

            for dev_idx in range(dev_count):
                dev_name = pynewlib.XXXmlGetDeviceName(dev_idx)
                dev_uuid = pynewlib.XXXmlGetDeviceUUID(dev_idx)
                dev_cores = pynewlib.XXXmlGetDeviceCores(dev_idx)

                # Memory info (convert bytes to MiB).
                dev_mem = byte_to_mebibyte(
                    pynewlib.XXXmlGetDeviceMemTotal(dev_idx),
                )
                dev_mem_used = byte_to_mebibyte(
                    pynewlib.XXXmlGetDeviceMemUsed(dev_idx),
                )

                # Health check.
                dev_mem_status = DeviceMemoryStatusEnum.HEALTHY
                if not envs.GPUSTACK_RUNTIME_DETECT_NO_HEALTH_CHECK:
                    try:
                        ecc_errors = pynewlib.XXXmlGetDeviceEccErrors(dev_idx)
                        if ecc_errors > 0:
                            dev_mem_status = DeviceMemoryStatusEnum.UNHEALTHY
                    except pynewlib.XXXmlError:
                        debug_log_warning(
                            logger,
                            "Failed to get device %d ECC errors",
                            dev_idx,
                        )

                # Utilization, temperature, power.
                dev_cores_util = 0
                try:
                    dev_cores_util = pynewlib.XXXmlGetDeviceUtilization(dev_idx)
                except pynewlib.XXXmlError:
                    debug_log_warning(
                        logger,
                        "Failed to get device %d cores utilization, setting to 0",
                        dev_idx,
                    )

                dev_temp = None
                try:
                    dev_temp = pynewlib.XXXmlGetDeviceTemperature(dev_idx)
                except pynewlib.XXXmlError:
                    debug_log_warning(
                        logger,
                        "Failed to get device %d temperature",
                        dev_idx,
                    )

                dev_power_used = None
                try:
                    dev_power_used = pynewlib.XXXmlGetDevicePowerUsage(dev_idx)
                except pynewlib.XXXmlError:
                    debug_log_warning(
                        logger,
                        "Failed to get device %d power usage",
                        dev_idx,
                    )

                # PCI/BDF info.
                dev_bdf = ""
                try:
                    pci_info = pynewlib.XXXmlGetDevicePciInfo(dev_idx)
                    dev_bdf = f"{pci_info.segment:04x}:{pci_info.bus:02x}:{pci_info.device:02x}.0"
                except pynewlib.XXXmlError:
                    debug_log_warning(
                        logger,
                        "Failed to get device %d PCI info",
                        dev_idx,
                    )

                dev_numa = get_numa_node_by_bdf(dev_bdf) if dev_bdf else ""

                dev_appendix = {}
                if dev_bdf:
                    dev_appendix["bdf"] = dev_bdf
                if dev_numa:
                    dev_appendix["numa"] = dev_numa

                ret.append(
                    Device(
                        manufacturer=self.manufacturer,
                        index=dev_idx,
                        uuid=dev_uuid,
                        name=dev_name,
                        driver_version=sys_driver_ver,
                        cores=dev_cores,
                        cores_utilization=dev_cores_util,
                        memory=dev_mem,
                        memory_used=dev_mem_used,
                        memory_utilization=get_utilization(dev_mem_used, dev_mem),
                        memory_status=dev_mem_status,
                        temperature=dev_temp,
                        power_used=dev_power_used,
                        appendix=dev_appendix,
                    ),
                )

        except pynewlib.XXXmlError:
            debug_log_exception(logger, "Failed to fetch devices")
            raise
        except Exception:
            debug_log_exception(logger, "Failed to process devices fetching")
            raise

        return ret

    def get_topology(self, devices: Devices | None = None) -> Topology | None:
        """
        Get the Topology object between NewChip GPUs.

        Args:
            devices:
                The list of detected NewChip devices.
                If None, detect topology for all available devices.

        Returns:
            The Topology object, or None if not supported.

        """
        if devices is None:
            devices = self.detect()
            if devices is None:
                return None

        ret = Topology(
            manufacturer=self.manufacturer,
            devices_count=len(devices),
        )

        for i, dev in enumerate(devices):
            # Get NUMA and CPU affinities.
            ret.devices_numa_affinities[i] = (dev.appendix or {}).get("numa", "")
            ret.devices_cpu_affinities[i] = map_numa_node_to_cpu_affinity(
                ret.devices_numa_affinities[i],
            )

            # TODO: Implement device-to-device distance detection
            # using the vendor's topology API.
            # Populate ret.devices_distances[i][j] with TopologyDistanceEnum values.

        return ret
