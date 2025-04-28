from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

# Load .env config
load_dotenv()

KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER")
REALM = os.getenv("REALM")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
FLASK_BACKEND_URL = "http://localhost:5000/app_consumer/new"
DEFAULT_PASSWORD = "Temp@1234"
PORT = 5016

app = Flask(__name__)

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    phone = data.get("phone")
    external_id = data.get("externalId")
    first_name = data.get("first_name", "User")
    last_name = data.get("last_name", "Test")

    print(f"🔹 Registering User: {username}, Email: {email}, ExternalID: {external_id}")

    try:
        # Step 1: Get admin token from Keycloak
        token_resp = requests.post(
            f"{KEYCLOAK_ISSUER}/realms/{REALM}/protocol/openid-connect/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "client_credentials"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token_resp.raise_for_status()
        admin_token = token_resp.json()["access_token"]
        print("✅ Admin Token Received")

        # Step 2: Create user in Keycloak
        user_payload = {
            "username": username,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": True,
            "emailVerified": True,
            "attributes": {"phone": phone, "external-id": external_id},
            "credentials": [{
                "type": "password",
                "value": DEFAULT_PASSWORD,
                "temporary": True
            }]
        }

        user_create_resp = requests.post(
            f"{KEYCLOAK_ISSUER}/admin/realms/{REALM}/users",
            json=user_payload,
            headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        )
        user_create_resp.raise_for_status()
        print("✅ User Created in Keycloak!")

        
        user_search_resp = requests.get(
            f"{KEYCLOAK_ISSUER}/admin/realms/{REALM}/users?username={username}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        user_search_resp.raise_for_status()
        user_data = user_search_resp.json()[0]
        keycloak_user_id = user_data["id"]
        print(f"🔹 Keycloak User ID: {keycloak_user_id}")


        flask_payload={
        "requestor_id": "",
        "request_token": "",
        "type": "User Registration",
        "tab":"Entity Config",
        "qry": {
                "keycloak_user_id": keycloak_user_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "password": DEFAULT_PASSWORD}
        }

        flask_resp = requests.post(FLASK_BACKEND_URL, json=flask_payload)
        flask_resp.raise_for_status()
        print(f"✅ User Inserted in Flask DB: {flask_resp.text}")

        return jsonify({"success": True, "message": "Registration successful!"})

    except requests.exceptions.RequestException as e:
        print(f"❌ Registration Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400


if __name__ == "__main__":
    app.run(port=PORT)
