import requests
import platform
from datetime import datetime

# ==========================================
# PASTE YOUR SUPABASE KEYS HERE
# ==========================================
SUPABASE_URL = "https://jvqdnndrnzsmdiekosad.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp2cWRubmRybnpzbWRpZWtvc2FkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgwNjc3NzMsImV4cCI6MjA5MzY0Mzc3M30.-sXhSsX3z4QDCZaR2H1g_IZM9DsSoYjxYiVHBailUNQ"

# Supabase REST API Endpoints
AUTH_URL = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
SIGNUP_URL = f"{SUPABASE_URL}/auth/v1/signup"
DB_URL = f"{SUPABASE_URL}/rest/v1/user_tracking"

def check_internet():
    try:
        requests.get("https://8.8.8.8", timeout=3)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False

def get_oauth_url(provider):
    """Returns the Supabase OAuth URL for Google or GitHub."""
    return f"{SUPABASE_URL}/auth/v1/authorize?provider={provider}"

def sign_up_user(email, password, name):
    """Creates a new user account via Supabase GoTrue API."""
    if not check_internet():
        return {"error": "NGI Offline Mode: No Internet Connection."}
    
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "email": email,
        "password": password,
        "data": {
            "full_name": name,
            "sourceWebsite": "NGI Desktop App"
        }
    }
    
    try:
        response = requests.post(SIGNUP_URL, json=payload, headers=headers)
        data = response.json()
        
        if response.status_code not in [200, 201]:
            error_msg = data.get("msg", data.get("error_description", "Signup Failed"))
            return {"error": error_msg}
            
        return {
            "success": True,
            "access_token": data.get("access_token", ""),
            "uid": data.get("user", {}).get("id", ""),
            "email": email,
            "message": "Account created! Please check your email to verify if required, or try logging in."
        }
    except Exception as e:
        return {"error": str(e)}

def sign_in_user(email, password):
    """Authenticates the user with Supabase GoTrue API."""
    if not check_internet():
        return {"error": "NGI Offline Mode: No Internet Connection."}
    
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(AUTH_URL, json=payload, headers=headers)
        data = response.json()
        
        if response.status_code != 200:
            error_msg = data.get("error_description", data.get("msg", "Authentication Failed"))
            return {"error": error_msg}
            
        return {
            "success": True,
            "access_token": data["access_token"],
            "uid": data["user"]["id"],
            "email": data["user"]["email"]
        }
    except Exception as e:
        return {"error": str(e)}

def update_user_tracking(uid, access_token):
    """Updates Supabase with the app accessed, timestamp, and platform."""
    if not check_internet() or not access_token:
        return False
        
    sys_platform = platform.system()
    if "android" in sys_platform.lower():
        sys_platform = "Android"
        
    current_time = datetime.utcnow().isoformat()
    
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates" 
    }
    
    payload = {
        "id": uid,
        "apps_accessed": {"MMN_APP": True},
        "last_login_timestamp": current_time,
        "platform": sys_platform
    }
    
    try:
        response = requests.post(DB_URL, json=payload, headers=headers)
        if response.status_code in [200, 201]:
            return True
        return False
    except Exception as e:
        return False