import streamlit as st
import io

from groq import Groq
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
REDIRECT_URI = st.secrets["google_oauth"]["redirect_uri"]

# --------------------------------------------------
# GOOGLE OAUTH FLOW
# --------------------------------------------------
def get_flow():
    client_config = {
        "web": {
            "client_id": st.secrets["google_oauth"]["client_id"],
            "client_secret": st.secrets["google_oauth"]["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

def get_drive_service():
    creds = Credentials(**st.session_state["google_creds"])
    return build("drive", "v3", credentials=creds)

def upload_to_drive(filename, content):
    service = get_drive_service()
    media = MediaIoBaseUpload(
        io.BytesIO(content.encode("utf-8")),
        mimetype="text/plain",
        resumable=True,
    )
    file = service.files().create(
        body={"name": filename},
        media_body=media,
        fields="id,name",
    ).execute()
    return file["name"]

# --------------------------------------------------
# STREAMLIT UI
# --------------------------------------------------
st.set_page_config("PragyanAI – Streamlit OAuth", layout="wide")
st.title("📢 PragyanAI – Google OAuth Streamlit App")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --------------------------------------------------
# AUTHENTICATION
# --------------------------------------------------
if "google_creds" not in st.session_state:
    flow = get_flow()

    if "code" in st.query_params:
        flow.fetch_token(code=st.query_params["code"])
        creds = flow.credentials

        st.session_state["google_creds"] = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }

        st.query_params.clear()
        st.rerun()

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )
    st.info("🔐 Sign in with Google to continue")
    st.link_button("🔑 Sign in with Google", auth_url)
    st.stop()

# --------------------------------------------------
# LOGGED-IN UI
# --------------------------------------------------
with st.sidebar:
    st.success("✅ Logged in with Google")
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

col1, col2 = st.columns(2)

with col1:
    st.subheader("✍️ Generate Content")
    product = st.text_input("Product")
    audience = st.text_input("Audience")

    if st.button("Generate"):
        prompt = f"Write marketing content for {product} targeting {audience}."
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
        )
        st.session_state.text = response.choices[0].message.content

with col2:
    st.subheader("📤 Upload to Google Drive")
    if "text" in st.session_state:
        text = st.text_area("Content", st.session_state.text, height=280)
        filename = st.text_input("Filename", "marketing_copy.txt")

        if st.button("Upload"):
            name = upload_to_drive(filename, text)
            st.success(f"✅ Uploaded: {name}")
            st.balloons()
    else:
        st.info("Generate content first")

