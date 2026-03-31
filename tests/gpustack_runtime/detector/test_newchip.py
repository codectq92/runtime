import pytest

from gpustack_runtime.detector.newchip import NewChipDetector


@pytest.mark.skipif(
    not NewChipDetector.is_supported(),
    reason="NewChip GPU not detected",
)
def test_detect():
    det = NewChipDetector()
    devs = det.detect()
    print(devs)


@pytest.mark.skipif(
    not NewChipDetector.is_supported(),
    reason="NewChip GPU not detected",
)
def test_get_topology():
    det = NewChipDetector()
    topo = det.get_topology()
    print(topo)
