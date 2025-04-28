const express = require("express");
const axios = require("axios");
const jwt = require("jsonwebtoken");
const jwksClient = require("jwks-rsa"); // ✅ JWKS Client for Token Verification
const path = require("path");
const fs = require("fs");
require("dotenv").config();

const app = express();
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(express.static("public"));  // Serve static files

// ✅ Load Config from .env
const KEYCLOAK_ISSUER = process.env.KEYCLOAK_ISSUER;
const REALM = process.env.REALM;
const CLIENT_ID = process.env.CLIENT_ID;
const CLIENT_SECRET = process.env.CLIENT_SECRET;
const JWKS_URL = `${KEYCLOAK_ISSUER}/realms/${REALM}/protocol/openid-connect/certs`; // ✅ JWKS URL for Public Keys

console.log("🔹 Keycloak Config:");
console.log(`  - ISSUER: ${KEYCLOAK_ISSUER}`);
console.log(`  - REALM: ${REALM}`);
console.log(`  - CLIENT_ID: ${CLIENT_ID}`);
console.log(`  - JWKS URL: ${JWKS_URL}`);

// ✅ Setup JWKS Client for JWT Verification
const client = jwksClient({ jwksUri: JWKS_URL });


// app.post("/register", async (req, res) => {
//     const { username, email, phone, externalId, first_name, last_name } = req.body;
//     const defaultPassword = "Temp@1234"; // Or any secure temp password
//     console.log(`🔹 Registering User: ${username}, Email: ${email}, ExternalID: ${externalId}`);

//     try {
//         const tokenResponse = await axios.post(
//             `${KEYCLOAK_ISSUER}/realms/${REALM}/protocol/openid-connect/token`,
//             new URLSearchParams({
//                 client_id: CLIENT_ID,
//                 client_secret: CLIENT_SECRET,
//                 grant_type: "client_credentials",
//             }),
//             { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
//         );

//         const adminToken = tokenResponse.data.access_token;
//         console.log("✅ Admin Token Received");

//         const createUserResponse = await axios.post(
//             `${KEYCLOAK_ISSUER}/admin/realms/${REALM}/users`,
//             {
//                 username,
//                 email,
//                 firstName: first_name || "User",
//                 lastName: last_name || "Test",
//                 enabled: true,
//                 emailVerified: true,
//                 attributes: { "phone":phone, "external-id": externalId },
//                 credentials: [{ type: "password", value: defaultPassword, temporary: true }],
//             },
//             { headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" } }
//         );

//         console.log("✅ User Created in Keycloak! Response Code:", createUserResponse.status);
//         res.json({ success: true, message: "Registration successful!" });

//     } catch (err) {
//         console.error("❌ Registration Error:", err.response?.data || err.message);
//         res.status(400).json({ success: false, error: err.response?.data || err.message });
//     }
    
// });

app.post("/register", async (req, res) => {
    const { username, email, phone, externalId, first_name, last_name } = req.body;
    const defaultPassword = "Temp@1234";

    console.log(`🔹 Registering User: ${username}, Email: ${email}, ExternalID: ${externalId}`);

    try {
        // Step 1: Get admin token from Keycloak
        const tokenResponse = await axios.post(
            `${KEYCLOAK_ISSUER}/realms/${REALM}/protocol/openid-connect/token`,
            new URLSearchParams({
                client_id: CLIENT_ID,
                client_secret: CLIENT_SECRET,
                grant_type: "client_credentials",
            }),
            { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
        );

        const adminToken = tokenResponse.data.access_token;
        console.log("✅ Admin Token Received");

        // Step 2: Create user in Keycloak
        const createUserResponse = await axios.post(
            `${KEYCLOAK_ISSUER}/admin/realms/${REALM}/users`,
            {
                username,
                email,
                firstName: first_name || "User",
                lastName: last_name || "Test",
                enabled: true,
                emailVerified: true,
                attributes: {"phone":phone, "external-id": externalId},
                credentials: [{type: "password",value: defaultPassword,temporary: true
                }]
            },
            { headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" } }
        );

        console.log("✅ User Created in Keycloak!");

        // Step 3: Fetch user ID from Keycloak (you must do this to get the `id`)
        const getUsersResponse = await axios.get(
            `${KEYCLOAK_ISSUER}/admin/realms/${REALM}/users?username=${encodeURIComponent(username)}`,
            { headers: { Authorization: `Bearer ${adminToken}` } }
        );

        const keycloakUser = getUsersResponse.data[0];
        const keycloakUserId = keycloakUser.id;

        console.log("🔹 Keycloak User ID:", keycloakUserId);

        // Step 4: Send data to Flask app (excluding external-id)
        const flaskResponse = await axios.post("http://localhost:5001/app_consumer/new", {
            tab: "app_consumer",
            type: "new",
            qry: {
                id: keycloakUserId,
                username,
                first_name,
                last_name,
                email,
                phone,
                password: defaultPassword
            }
        });

        console.log("✅ User Inserted in Flask DB:", flaskResponse.data);

        res.json({ success: true, message: "Registration successful!" });

    } catch (err) {
        console.error("❌ Registration Error:", err.response?.data || err.message);
        if (!res.headersSent) {
            res.status(400).json({ success: false, error: err.response?.data || err.message });
        }
    }
});


// ✅ Start Server
const PORT = process.env.PORT || 5016;
app.listen(PORT, () => console.log(`🚀 Server running on http://localhost:${PORT}`));
