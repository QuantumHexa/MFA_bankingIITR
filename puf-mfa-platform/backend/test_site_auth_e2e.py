"""Test site-to-user authentication flow (in-process, no live server required)."""

from fastapi.testclient import TestClient

from app.database import SessionLocal, SiteAuthChallenge, User, init_db
from app.main import app
from app.services.auth_service import hash_password

client = TestClient(app)


def _ensure_test_user():
    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "hwec355706c037").first()
        if user:
            user.site_auth_phrase = "fine for me"
            db.commit()
            return
        user = User(
            username="site_test_user",
            email="site_test@example.com",
            phone="9111111111",
            full_name="Site Test",
            dob="2000-01-01",
            account_number="999999999991",
            password_hash=hash_password("TestPass123"),
            site_auth_phrase="fine for me",
            puf_enabled=False,
            puf_mode="off",
        )
        db.add(user)
        db.commit()
    finally:
        db.close()


def test_site_to_user_flow():
    _ensure_test_user()
    username = "hwec355706c037"

    # Challenge returns phrase
    r = client.post("/api/auth/site-challenge", json={"username": username})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["phrase"] == "fine for me"
    cid = data["challenge_id"]

    # Login blocked without site challenge
    r2 = client.post("/api/auth/login/start", json={"username": username, "password": "SecurePass123"})
    assert r2.status_code == 400

    # Login blocked if challenge not confirmed
    r3 = client.post(
        "/api/auth/login/start",
        json={"username": username, "password": "SecurePass123", "site_challenge_id": cid},
    )
    assert r3.status_code == 403

    # Confirm phrase
    r4 = client.post("/api/auth/site-challenge/confirm", json={"challenge_id": cid})
    assert r4.status_code == 200

    # Login proceeds to OTP
    r5 = client.post(
        "/api/auth/login/start",
        json={"username": username, "password": "SecurePass123", "site_challenge_id": cid},
    )
    assert r5.status_code == 200, r5.text
    assert r5.json().get("next_step") == "verify_otp"

    print("ALL SITE-TO-USER TESTS PASSED")


if __name__ == "__main__":
    test_site_to_user_flow()
