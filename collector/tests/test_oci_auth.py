from __future__ import annotations

from types import SimpleNamespace

from oracle_collector.collectors.oci import auth
from oracle_collector.config import OciConfig


def test_session_token_uses_loaded_private_key_object(monkeypatch, tmp_path) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("session-token", encoding="utf-8")
    key_file = tmp_path / "key.pem"
    key_file.write_text("not-read-by-fake", encoding="utf-8")
    captured = {}

    class Config:
        @staticmethod
        def from_file(path, profile):
            return {
                "security_token_file": str(token_file),
                "key_file": str(key_file),
                "pass_phrase": None,
                "tenancy": "ocid.tenancy",
            }

    class SignerModule:
        @staticmethod
        def load_private_key_from_file(path, pass_phrase):
            captured["key_path"] = path
            return object()

    class SecurityTokenSigner:
        def __init__(self, token, private_key):
            captured["token"] = token
            captured["private_key"] = private_key

    fake_oci = SimpleNamespace(
        config=Config,
        signer=SignerModule,
        auth=SimpleNamespace(signers=SimpleNamespace(SecurityTokenSigner=SecurityTokenSigner)),
    )
    monkeypatch.setattr(auth, "_oci", lambda: fake_oci)

    values, signer = auth.auth_context(
        OciConfig(enabled=True, auth="session_token", regions=("sa-santiago-1",))
    )

    assert values["tenancy"] == "ocid.tenancy"
    assert isinstance(signer, SecurityTokenSigner)
    assert captured["token"] == "session-token"
    assert captured["key_path"] == str(key_file)
    assert not isinstance(captured["private_key"], str)

