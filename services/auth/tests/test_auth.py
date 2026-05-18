import pytest


pytestmark = pytest.mark.asyncio


# ─── Registration ──────────────────────────────────────────────

class TestRegister:
    async def test_register_success(self, client):
        resp = await client.post("/auth/register", json={
            "email": "new@example.com",
            "full_name": "New User",
            "password": "password123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    async def test_register_duplicate_email(self, client, registered_user):
        resp = await client.post("/auth/register", json={
            "email": "test@example.com",
            "full_name": "Another User",
            "password": "password123",
        })
        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"]

    async def test_register_short_password(self, client):
        resp = await client.post("/auth/register", json={
            "email": "short@example.com",
            "full_name": "Short Pass",
            "password": "abc",
        })
        assert resp.status_code == 422  # Validation error

    async def test_register_invalid_email(self, client):
        resp = await client.post("/auth/register", json={
            "email": "not-an-email",
            "full_name": "Bad Email",
            "password": "password123",
        })
        assert resp.status_code == 422


# ─── Login ─────────────────────────────────────────────────────

class TestLogin:
    async def test_login_success(self, client, registered_user):
        resp = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "securepassword123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client, registered_user):
        resp = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401
        assert "Invalid credentials" in resp.json()["detail"]

    async def test_login_unknown_email(self, client):
        resp = await client.post("/auth/login", json={
            "email": "nobody@example.com",
            "password": "password123",
        })
        assert resp.status_code == 401

    async def test_login_returns_different_tokens_each_time(self, client, registered_user):
        creds = {"email": "test@example.com", "password": "securepassword123"}
        r1 = await client.post("/auth/login", json=creds)
        r2 = await client.post("/auth/login", json=creds)
        # Access tokens should differ (different exp timestamps)
        assert r1.json()["refresh_token"] != r2.json()["refresh_token"]


# ─── Token Refresh ─────────────────────────────────────────────

class TestTokenRefresh:
    async def test_refresh_success(self, client, registered_user):
        resp = await client.post("/auth/refresh", json={
            "refresh_token": registered_user["refresh_token"]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New refresh token issued (rotation)
        assert data["refresh_token"] != registered_user["refresh_token"]

    async def test_refresh_token_rotation(self, client, registered_user):
        """Old refresh token must be invalidated after rotation"""
        old_rt = registered_user["refresh_token"]
        await client.post("/auth/refresh", json={"refresh_token": old_rt})
        # Using old token again should fail
        resp = await client.post("/auth/refresh", json={"refresh_token": old_rt})
        assert resp.status_code == 401

    async def test_refresh_invalid_token(self, client):
        resp = await client.post("/auth/refresh", json={
            "refresh_token": "totally-fake-token"
        })
        assert resp.status_code == 401

    async def test_logout_invalidates_token(self, client, registered_user):
        rt = registered_user["refresh_token"]
        logout = await client.post("/auth/logout", json={"refresh_token": rt})
        assert logout.status_code == 200
        # Refresh after logout should fail
        resp = await client.post("/auth/refresh", json={"refresh_token": rt})
        assert resp.status_code == 401


# ─── Protected Routes ──────────────────────────────────────────

class TestProtectedRoutes:
    async def test_get_me_success(self, client, auth_headers):
        resp = await client.get("/users/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert "hashed_password" not in data

    async def test_get_me_no_token(self, client):
        resp = await client.get("/users/me")
        assert resp.status_code == 403

    async def test_get_me_invalid_token(self, client):
        resp = await client.get("/users/me", headers={"Authorization": "Bearer fake"})
        assert resp.status_code == 401


# ─── Risk Profile ──────────────────────────────────────────────

class TestRiskProfile:
    VALID_PROFILE = {
        "risk_score": 7,
        "investment_horizon": 60,
        "monthly_income": 8000.0,
        "investable_assets": 75000.0,
        "questionnaire_data": {"goal": "growth"},
    }

    async def test_create_risk_profile(self, client, auth_headers):
        resp = await client.post("/users/me/risk-profile", json=self.VALID_PROFILE, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_score"] == 7
        assert data["risk_category"] == "moderate"

    async def test_risk_category_conservative(self, client, auth_headers):
        resp = await client.post("/users/me/risk-profile",
            json={**self.VALID_PROFILE, "risk_score": 2}, headers=auth_headers)
        assert resp.json()["risk_category"] == "conservative"

    async def test_risk_category_aggressive(self, client, auth_headers):
        resp = await client.post("/users/me/risk-profile",
            json={**self.VALID_PROFILE, "risk_score": 9}, headers=auth_headers)
        assert resp.json()["risk_category"] == "aggressive"

    async def test_risk_score_out_of_range(self, client, auth_headers):
        resp = await client.post("/users/me/risk-profile",
            json={**self.VALID_PROFILE, "risk_score": 11}, headers=auth_headers)
        assert resp.status_code == 422

    async def test_upsert_risk_profile(self, client, auth_headers):
        await client.post("/users/me/risk-profile", json=self.VALID_PROFILE, headers=auth_headers)
        # Update
        resp = await client.post("/users/me/risk-profile",
            json={**self.VALID_PROFILE, "risk_score": 3}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["risk_score"] == 3

    async def test_get_risk_profile_not_found(self, client, auth_headers):
        resp = await client.get("/users/me/risk-profile", headers=auth_headers)
        assert resp.status_code == 404

    async def test_get_risk_profile_after_create(self, client, auth_headers):
        await client.post("/users/me/risk-profile", json=self.VALID_PROFILE, headers=auth_headers)
        resp = await client.get("/users/me/risk-profile", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["risk_score"] == 7