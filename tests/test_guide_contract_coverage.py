"""고정 가이드 coverage oracle과 executable contract의 일대일 대조."""

from __future__ import annotations

import json
from pathlib import Path

from mvp_mcp.domain.spec.guide_contract import DOCUMENT_CONTRACTS


def test_guide_coverage_manifest_matches_contract_counts() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "guide_coverage_manifest.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert fixture["source_sha256"] == (
        "2c4d944af733a37e4d6b4925695fb261cb30a0715087e26505ab35544702f96d"
    )
    assert fixture["documents"] == {
        name: len(contract.sections) for name, contract in DOCUMENT_CONTRACTS.items()
    }
    for contract in DOCUMENT_CONTRACTS.values():
        assert contract.purpose.strip()
        assert contract.owns.strip()
        assert contract.references.strip()
        assert contract.excludes.strip()
        assert all(section.strip() for section in contract.sections)
