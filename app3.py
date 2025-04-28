# py -3 -m pip install Flask  (install libraries in python 3.9 syntax)

#from distutils.log import error

from flask import Flask, render_template, jsonify, request,redirect
from flask_cors import CORS 
from flask import *
import json
import random
import datetime 
from datetime import datetime, timedelta
import pymysql
from db_operations import * 
import requests
import jwt
from jwt.algorithms import RSAAlgorithm
from functools import wraps
import json
import os
from dotenv import load_dotenv

load_dotenv() 

app = Flask(__name__)
#CORS(app)
CORS(app, resources={r"/*": {"origins": "*"}})

################################################# Load environment variables #################################################

KEYCLOAK_ISSUER = os.environ.get("KEYCLOAK_ISSUER")
REALM = os.environ.get("REALM")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
JWKS_URL = f"{KEYCLOAK_ISSUER}/realms/{REALM}/protocol/openid-connect/certs"

print("🔹 Keycloak Config:")
print(f"  - ISSUER: {KEYCLOAK_ISSUER}")
print(f"  - REALM: {REALM}")
print(f"  - CLIENT_ID: {CLIENT_ID}")
print(f"  - JWKS URL: {JWKS_URL}")

# Load JWKS (only once)
jwks_keys = requests.get(JWKS_URL).json()['keys']

################################################## Keycloak APIs #############################################################

def get_signing_key(kid):
    key = next((k for k in jwks_keys if k['kid'] == kid), None)
    if not key:
        raise Exception("Public key not found for given kid")
    return RSAAlgorithm.from_jwk(json.dumps(key))

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    print(f"🔹 Logging in User: {username}")

    try:
        response = requests.post(
            f"{KEYCLOAK_ISSUER}/realms/{REALM}/protocol/openid-connect/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "password",
                "username": username,
                "password": password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        keycloak_token = response.json()["access_token"]
        print("✅ Keycloak Token Received", keycloak_token)
        return jsonify({"success": True, "keycloakToken": keycloak_token})

    except Exception as e:
        print("❌ Login Error:", str(e))
        return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route("/verify-token", methods=["POST"])
def verify_token():
    print("🔹 Full Request Headers:", dict(request.headers))
    data = request.get_json()
    token = data.get("token") or request.headers.get("Authorization", "").replace("Bearer ", "")

    if not token:
        print("❌ Token is missing in request")
        return jsonify({"error": "Token is required"}), 400

    try:
        unverified_header = jwt.get_unverified_header(token)
        print("🔹 Fetching JWKS Key for KID:", unverified_header["kid"])
        signing_key = get_signing_key(unverified_header["kid"])
        print(signing_key)
        decoded = jwt.decode(token, signing_key, algorithms=["RS256"], audience=["myclient","app2"])
        #audience=CLIENT_ID
        print("✅ Token Verified:", decoded)
        return jsonify({"valid": True, "userInfo": decoded})
    except Exception as e:
        print("❌ JWT Verification Failed:", str(e))
        return jsonify({"success": False, "error": "Invalid Keycloak token"}), 401

@app.route("/app1-details", methods=["GET"])
def app1_details():
    with open("app1.json", "r") as f:
        data = json.load(f)
    return jsonify(data.get("app1", {}))

######################################################### TESTING ############################################################

@app.route('/alive')
def alive():
    return jsonify({"ack":"hello,  welcome"}) 

@app.route('/')
def login_page():
    return render_template('index.html') 

@app.route("/app1")
def app1():
    token = request.args.get("token")
    return render_template("app1.html",token=token)
    
@app.route('/app')
def home_page():
    return render_template('index3.html') 

@app.route('/qr')
def qr_decode():
    return render_template('qr_decoder.html') 
    

@app.route('/options', methods=['POST'])
def get_helper_data():
    data = request.get_json()  # Use request.get_json() instead of json.loads(request.data)
    print("Received Data:", data)

    f=open('config/new/get_DB_data.json');  json_data = json.load(f)
    print("db name: ",json_data)
    data = json.loads(request.data); print(data)
    
    try:
        myresult=get_data(json_data['db_name'],json_data[data['tab']][data['type']], data['qry']['select_fields'],data['qry']['where_data']) 
        print(myresult);    return jsonify(myresult)
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500
        
@app.route('/get_user_tabs',methods=['POST','GET'])
def get_user_tabs():
    data = request.data 
    y = json.loads(data) 
    print(y['role'])    # the result is a Python dictionary:
    f=open('config/new/user_tabs.json')
    tab_data = json.load(f)
    if (y['role']=="Admin"):
        response=tab_data['Admin']
    elif (y['role']=="User"):
        response=tab_data['User']
    elif (y['role']=="Finance_admin"):
        response=tab_data['Finance_admin']
    elif (y['role']=="Campaign_admin"):
        response=tab_data['Campaign_admin']
    else:
        response=jsonify("role not defined")
    print(response)
    return jsonify(response)


######################################################  ENTITY  APIs  ####################################################################

def stream_json():
    """ Reads request stream in chunks and returns parsed JSON data """
    data_chunks = []
    for chunk in request.stream:
        data_chunks.append(chunk.decode('utf-8'))
    full_data = ''.join(data_chunks)
    return json.loads(full_data) if full_data else {}

@app.route('/entity/new', methods=['POST'])
def insert_entity():
    json_data = json.load(open('config/new/get_DB_data.json')) 
    data = stream_json()  # Receiving data in chunks
    
    if not data:
        return jsonify({'error': 'Invalid or missing data'}), 400
    
    required_columns = ['entity_id', 'entity_name', 'entity_type', 'created_at', 'updated_at', 'entry_status', 'archive']
    
    # Check for missing columns
    missing_columns = [col for col in required_columns if col not in data.get("qry", {})]
    if missing_columns:
        return jsonify({'error': f'Missing columns: {missing_columns}'}), 400

    success, message = insert_ignore(json_data['db_name'], json_data[data['tab']][data['type']], data.get("qry"))
    
    if success:
        return jsonify({'message': message}), 201
    else:
        return jsonify({'error': message}), 400

@app.route('/entity/modifications', methods=['PUT'])
def update_entry_api():
    json_data = json.load(open('config/new/get_DB_data.json'))
    data = stream_json()  # Receiving data in chunks
    
    update_data = data.get("qry")
    where_data = {"entity_id": data.get('entity_id')}

    if not update_data or not where_data.get("entity_id"):
        return jsonify({"error": "Missing entity_id or update_data"}), 400

    success = update_entry(json_data['db_name'], json_data[data['tab']][data['type']], update_data, where_data)
    
    if success:
        return jsonify({"message": "Entry updated successfully"}), 200
    else:
        return jsonify({"error": "Failed to update entry"}), 500

@app.route('/entity', methods=['DELETE'])
def delete_entry_api():
    json_data = json.load(open('config/new/get_DB_data.json'))
    data = stream_json()  # Receiving data in chunks
    entity_id = data.get('entity_id')

    if not entity_id:
        return jsonify({"error": "Missing entity_id"}), 400

    success = delete_entry(json_data['db_name'], json_data[data['tab']][data['type']], {"entity_id": entity_id})
    
    if success:
        return jsonify({"message": "Entry deleted successfully"}), 200
    else:
        return jsonify({"error": "Failed to delete entry"}), 500
    
@app.route('/entity/list_details', methods=['POST', 'GET'])
def entity_get_data():
    json_data = json.load(open('config/new/get_DB_data.json'))
    data = stream_json()  # Receiving data in chunks
    
    try:
        myresult = get_data(
            json_data['db_name'],
            json_data[data['tab']][data['type']],
            data['qry']['select_fields'],
            data['qry']['where_data']
        )
        
        return jsonify(myresult if data['qry']['where_data'] else [myresult])
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


######################### -- EGOV API -- ######################################

@app.route('/app_consumer/new', methods=['POST'])
def insert_app_consumer():
    json_data = json.load(open('config/new/get_DB_data.json')) 
    data = stream_json()  # Receiving data in chunks
    print("➡️ Received Payload:", data)
    
    if not data:
        return jsonify({'error': 'Invalid or missing data'}), 400
    
    db_name = json_data.get('db_name')
    table_config = json_data.get(data.get('tab', ''), {}).get(data.get('type', ''), {})
    print("🗂 DB Name:", db_name)
    print("📁 Table Config:", table_config)

    success, message = insert_ignore(json_data['db_name'], json_data[data['tab']][data['type']], data.get("qry"))
    print("✅ insert_ignore result:", success, message)
    if success:
        return jsonify({'message': message}), 201
    else:
        return jsonify({'error': message}), 400

@app.route('/app_consumer/modifications', methods=['PUT'])
def update_app_consumer():
    json_data = json.load(open('config/new/get_DB_data.json'))
    data = stream_json()  # Receiving data in chunks
    
    update_data = data.get("qry")
    where_data = {"entity_id": data.get('entity_id')}

    if not update_data or not where_data.get("entity_id"):
        return jsonify({"error": "Missing entity_id or update_data"}), 400

    success = update_entry(json_data['db_name'], json_data[data['tab']][data['type']], update_data, where_data)
    
    if success:
        return jsonify({"message": "Entry updated successfully"}), 200
    else:
        return jsonify({"error": "Failed to update entry"}), 500

@app.route('/app_consumer', methods=['DELETE'])
def delete_app_consumer():
    json_data = json.load(open('config/new/get_DB_data.json'))
    data = stream_json()  # Receiving data in chunks
    entity_id = data.get('entity_id')

    if not entity_id:
        return jsonify({"error": "Missing entity_id"}), 400

    success = delete_entry(json_data['db_name'], json_data[data['tab']][data['type']], {"entity_id": entity_id})
    
    if success:
        return jsonify({"message": "Entry deleted successfully"}), 200
    else:
        return jsonify({"error": "Failed to delete entry"}), 500

@app.route('/app_consumer/list_details', methods=['POST', 'GET'])
def entity_app_consumer():
    json_data = json.load(open('config/new/get_DB_data.json'))
    data = stream_json()  # Receiving data in chunks
    
    try:
        myresult = get_data(
            json_data['db_name'],
            json_data[data['tab']][data['type']],
            data['qry']['select_fields'],
            data['qry']['where_data']
        )
        
        return jsonify(myresult if data['qry']['where_data'] else [myresult])
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#################################################################################
#new
@app.route('/config/new', methods=['POST'])
def entityConfig_new():
    f=open('config/new/get_DB_data.json');  json_data = json.load(f)
    print("db name: ",json_data)
    data = request.json
    print(data.get("qry"))
    # Insert data into the entity table
    print(">>",json_data['db_name'],json_data[data['tab']][data['type']], data.get("qry") )
    success, message = insert_ignore(json_data['db_name'],json_data[data['tab']][data['type']], data.get("qry") )
    
    if success:
        return jsonify({'message': message}), 201
    else:
        return jsonify({'error': message}), 400

# List
@app.route('/config/list_details', methods=['POST', 'GET'])
def entityConfig_list():
    f=open('config/new/get_DB_data.json');  json_data = json.load(f)
    print("db name: ",json_data)
    data = json.loads(request.data); print("DATA:",data)
    
    try:
        myresult=get_data(json_data['db_name'],json_data[data['tab']][data['type']], data['qry']['select_fields'],data['qry']['where_data']) 
        print(myresult)
        if(data['qry']['where_data']=={}):
            return jsonify(myresult,data['type'])
        else:
            return jsonify(myresult,data['type'])
     
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

# Update 
@app.route('/config/modifications', methods=['PUT'])
def entityConfig_update():
    f=open('config/new/get_DB_data.json');  json_data = json.load(f)
    print("db name: ",json_data['db_name'])
    data = request.json
    qry = data.get('qry', {})
    update_data = qry.get('update', {})
    where_data = qry.get('where_data', {})
    print(">>",update_data,where_data) 

    if not update_data or not where_data:
        return jsonify({"error": "Missing table_name, update_data or where_data"}), 400
    success = update_entry(json_data['db_name'],json_data[data['tab']][data['type']], update_data,where_data,)
    if success:
        return jsonify({"message": "Entry updated successfully"}), 200
    else:
        return jsonify({"error": "Failed to update entry"}), 500

# Delete
@app.route('/config', methods=['DELETE'])
def entityConfig_delete():
    f=open('config/new/get_DB_data.json');  json_data = json.load(f)
    print("db name: ",json_data['db_name'])
    data = json.loads(request.data)
    qry = data.get('qry', {})

    print("Query Received:", qry)
    print("Query Received:", type(qry['where_data']))

     # Ensure 'where_data' is always a dictionary
    where_data = qry.get('where_data', {})
    for key in where_data.keys():
        print(key)

    if isinstance(where_data, str):  
        try:
            where_data = json.loads(where_data)  # Convert string to dictionary
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid format for where_data'}), 400

    if not isinstance(where_data, dict):  
        return jsonify({'error': 'where_data must be a dictionary'}), 400

    print("Processed Where Data:", where_data)
    #success = delete_entry(json_data['db_name'],json_data['entity_config'][data['type']], {"entity_id":entity_id} )
    success = delete_entry(json_data['db_name'],json_data[data['tab']][data['type']], where_data)
    if success:
        return jsonify({"message": "Entry deleted successfully"}), 200
    else:
        return jsonify({"error": "Failed to delete entry"}), 500


if __name__ == '__main__':
   app.run(host='0.0.0.0', port=5000, debug=True)
   