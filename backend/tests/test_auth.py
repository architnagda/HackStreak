import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api"

def test_auth_flow():
    email = f"testuser_{int(time.time())}@documind.ai"
    password = "SecretPassword123!"
    full_name = "Dr. Jane Doe"

    print(f"1. Testing Registration for {email}...")
    reg_res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "password": password,
        "full_name": full_name
    })
    print(f"Registration response code: {reg_res.status_code}")
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == email
    token = reg_data["access_token"]
    print("Registration successful! Token received.")

    print("\n2. Testing Login with correct credentials...")
    login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": password
    })
    print(f"Login response code: {login_res.status_code}")
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    login_data = login_res.json()
    token = login_data["access_token"]
    print("Login successful! Token received.")

    print("\n3. Testing GET /api/auth/me with Bearer token...")
    me_res = requests.get(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Me response code: {me_res.status_code}")
    assert me_res.status_code == 200, f"Me endpoint failed: {me_res.text}"
    me_data = me_res.json()
    assert me_data["email"] == email
    assert me_data["full_name"] == full_name
    print(f"Me profile verified: {me_data}")

    print("\n4. Testing Login with incorrect password...")
    wrong_login = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": "WrongPassword!"
    })
    print(f"Wrong password response code: {wrong_login.status_code}")
    assert wrong_login.status_code == 401
    print("Correctly rejected unauthorized login.")

    print("\nALL AUTHENTICATION TESTS PASSED!")

if __name__ == "__main__":
    test_auth_flow()
