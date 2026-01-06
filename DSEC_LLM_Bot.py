import streamlit as st
import io
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials

# 1. Define the permissions your app needs
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_oauth_flow():
    """Configures the OAuth flow using secrets."""
    client_config = {
        "web": {
            "client_id": st.secrets["google_oauth"]["client_id"],
            "client_secret": st.secrets["google_oauth"]["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=st.secrets["google_oauth"]["redirect_uri"]
    )

def upload_to_drive(creds, filename, content):
    """Uploads a simple text file to the user's Drive."""
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': filename}
    
    media_content = io.BytesIO(content.encode('utf-8'))
    media = MediaIoBaseUpload(media_content, mimetype='text/plain', resumable=True)
    
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    return file.get('id')

# --- STREAMLIT UI ---
st.title("🔑 PragyanAI: Sign in to Export")

# Check if user is already logged in
if "google_creds" not in st.session_state:
    flow = get_oauth_flow()
    
    # Handle the redirect from Google
    if "code" in st.query_params:
        flow.fetch_token(code=st.query_params["code"])
        creds = flow.credentials
        # Save credentials in session state
        st.session_state.google_creds = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes
        }
        st.query_params.clear()
        st.rerun()

    # If no code in URL, show the Login Button
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    st.info("Log in to authorize Drive access.")
    st.link_button("🔵 Sign in with Google", auth_url)
    st.stop()

# --- IF LOGGED IN ---
creds = Credentials(**st.session_state.google_creds)

with st.sidebar:
    st.success("Connected to Google")
    if st.button("Logout"):
        del st.session_state.google_creds
        st.rerun()

st.subheader("Create & Upload Content")
file_name = st.text_input("Filename", value="my_content.txt")
text_data = st.text_area("Content to save in Drive")

if st.button("🚀 Upload to My Drive"):
    if text_data:
        try:
            file_id = upload_to_drive(creds, file_name, text_data)
            st.success(f"File uploaded! ID: {file_id}")
        except Exception as e:
            st.error(f"Upload failed: {e}")
            
