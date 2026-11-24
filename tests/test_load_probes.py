from pathlib import Path

from self_awaken.fingerprint import load_probes


def test_load_probes_directory():
    probes = load_probes(Path("data/probes"))
    ids = {probe.id for probe in probes}
    assert "math-001" in ids
    assert "math-002" in ids
    assert len(probes) >= 50
