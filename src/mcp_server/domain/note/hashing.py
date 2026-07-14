"""콘텐츠 해시(재현성 식별자).

동일 입력 → 동일 해시를 보장해 "같은 요청이 같은 산출물을 만든다"를 식별할 수 있게
한다. 비결정적 값(현재 시각 등)은 해시 입력에서 제외한다.
"""

from __future__ import annotations

import hashlib
import json

from .model import NoteRequest


def compute_content_hash(request: NoteRequest) -> str:
    """요청 내용의 SHA-256 앞 16자리를 반환한다(키 순서 고정으로 결정성 확보)."""
    payload = json.dumps(request.model_dump(), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
