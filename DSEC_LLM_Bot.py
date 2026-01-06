import streamlit as st
from groq import Groq
import io
import json

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials

# -------------------------------------------------
# GOOGLE OAUTH HELPERS
# -------------------------------------------------

def get_oauth_flow():
    client_config = {
        "web": {
            "client_id": st.secrets["google_oauth"]["client_id"],
            "client_secret": st.secrets["google_oauth"]["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    return Flow.from_client_config(
        client_config=client_config,
        scopes=["https://www.googleapis.com/auth/drive.file"],
        # Ensure this matches Google Cloud Console EXACTLY
        redirect_uri=st.secrets["google_oauth"]["redirect_uri"],
    )

def get_drive_service():
    creds = Credentials(**st.session_state["google_creds"])
    return build("drive", "v3", credentials=creds)

def upload_file_to_drive(filename, content):
    service = get_drive_service()
    metadata = {"name": filename}
    buffer = io.BytesIO(content.encode("utf-8"))
    media = MediaIoBaseUpload(buffer, mimetype="text/plain", resumable=True)

    file = service.files().create(
        body=metadata,
        media_body=media,
        fields="id, name"
    ).execute()

    return file["id"], file["name"]

# -------------------------------------------------
# STREAMLIT APP
# -------------------------------------------------

st.set_page_config("PragyanAI Marketing Generator", layout="wide")
st.title("📢 PragyanAI – Drive Exporter")

if "GROQ_API_KEY" not in st.secrets:
    st.error("Missing GROQ_API_KEY in secrets!")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# -------------------------------------------------
# OAUTH LOGIN FLOW
# -------------------------------------------------

if "google_creds" not in st.session_state:
    flow = get_oauth_flow()
    
    # 1. Check for the 'code' in URL after redirect
    if "code" in st.query_params:
        code = st.query_params["code"]
        flow.fetch_token(code=code)
        creds = flow.credentials
        st.session_state["google_creds"] = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes
        }
        # Clear the code from URL and refresh app
        st.query_params.clear()
        st.rerun()

    # 2. Show Login Button if not authenticated
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    st.info("🔐 Access to Google Drive is required.")
    st.link_button("🔑 Sign in with Google", auth_url)
    st.stop()

# -------------------------------------------------
# MAIN APP (LOGGED IN)
# -------------------------------------------------

with st.sidebar:
    st.success("✅ Logged in")
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

col1, col2 = st.columns(2)

with col1:
    st.subheader("✍️ Content Creation")
    product = st.text_input("Product Name")
    audience = st.text_input("Target Audience")

    if st.button("Generate Content"):
        with st.spinner("AI is working..."):
            prompt = f"Write marketing copy for {product} targeting {audience}."
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )
            st.session_state.text = response.choices[0].message.content

with col2:
    st.subheader("📤 Export to Drive")
    if "text" in st.session_state:
        edited_text = st.text_area("Final Copy", st.session_state.text, height=300)
        filename = st.text_input("Save As", value="marketing_copy.txt")

        if st.button("🚀 Upload"):
            try:
                fid, fname = upload_file_to_drive(filename, edited_text)
                st.success(f"✅ Uploaded! ID: {fid}")
                st.balloons()
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.info("Waiting for content generation...")
        
