import pytest
import time
from unittest.mock import patch
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret", "DATABASE_URL": "sqlite+aiosqlite:///:memory:"}):
    from security import (
        hash_password, verify_password,
        create_access_token, create_refresh_token, decode_access_token
    )


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        assert hash_password("mypassword") != "mypassword"

    def test_verify_correct_password(self):
        hashed = hash_password("correct")
        assert verify_password("correct", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_two_hashes_differ(self):
        # bcrypt uses random salt
        assert hash_password("same") != hash_password("same")

    def test_verify_against_wrong_hash(self):
        assert verify_password("password", "not-a-valid-hash") is False


class TestJWT:
    def test_create_and_decode_access_token(self):
        token, expires_in = create_access_token("user-123", "user@example.com")
        assert isinstance(token, str)
        assert expires_in > 0
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"
        assert payload["email"] == "user@example.com"
        assert payload["type"] == "access"

    def test_invalid_token_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            decode_access_token("totally.fake.token")
        assert exc.value.status_code == 401

    def test_tampered_token_raises(self):
        from fastapi import HTTPException
        token, _ = create_access_token("user-123", "user@example.com")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(HTTPException):
            decode_access_token(tampered)

    def test_token_expires_in_is_correct(self):
        _, expires_in = create_access_token("u", "u@u.com")
        # Should be close to 30 min = 1800 seconds
        assert 1700 < expires_in <= 1800


class TestRefreshToken:
    def test_refresh_token_is_urlsafe_string(self):
        raw, hashed = create_refresh_token()
        assert isinstance(raw, str)
        assert len(raw) > 32

    def test_raw_and_hash_differ(self):
        raw, hashed = create_refresh_token()
        assert raw != hashed

    def test_hash_is_deterministic(self):
        import hashlib
        raw, hashed = create_refresh_token()
        expected = hashlib.sha256(raw.encode()).hexdigest()
        assert hashed == expected

    def test_two_refresh_tokens_unique(self):
        raw1, _ = create_refresh_token()
        raw2, _ = create_refresh_token()
        assert raw1 != raw2