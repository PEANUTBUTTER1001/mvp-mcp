"""순수 도메인 계층(프레임워크 의존 없음).

이 패키지의 어떤 모듈도 mcp/pydantic-settings/DB 드라이버 등 프레임워크를 import
하지 않는다. 이 규칙은 ``tests/test_scaffolding.py`` 가 강제한다.
"""
