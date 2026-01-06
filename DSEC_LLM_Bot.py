import streamlit as st
from groq import Groq
import io

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
REDIRECT_URI = st.secrets["google_oauth"]["redirect_uri"]

# -------------------------------------------------
# GOOGLE OAUTH
# -------------------------------------------------

def get_oauth_flow():
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
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )


def get_drive_service():
    creds = Credentials(**st.session_state["google_creds"])
    return build("drive", "v3", credentials=creds)


def upload_file_to_drive(filename, content):
    service = get_drive_service()

    file_metadata = {"name": filename}
    buffer = io.BytesIO(content.encode("utf-8"))
    media = MediaIoBaseUpload(buffer, mimetype="text/plain", resumable=True)

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name"
    ).execute()

    return file["id"], file["name"]

# -------------------------------------------------
# STREAMLIT APP
# -------------------------------------------------

st.set_page_config(
    page_title="PragyanAI – LLM Marketing Bot",
    layout="wide"
)

st.title("📢 PragyanAI – LLM Marketing Content Generator")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# -------------------------------------------------
# LOGIN FLOW
# -------------------------------------------------

if "google_creds" not in st.session_state:
    flow = get_oauth_flow()

    # Handle redirect back from Google
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
            "scopes": creds.scopes,
        }

        st.query_params.clear()
        st.rerun()

    auth_url, _ = flow.authorization_url(
        prompt="consent",
        access_type="offline",
    )

    st.info("🔐 Sign in with Google to upload files to your Drive")
    st.link_button("🔑 Sign in with Google", auth_url)
    st.stop()

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------

with st.sidebar:
    st.success("✅ Google Login Successful")
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

# -------------------------------------------------
# MAIN UI
# -------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    st.subheader("✍️ Generate Marketing Content")

    product = st.text_input("Product / Program Name")
    audience = st.text_input("Target Audience")

    if st.button("Generate Content"):
        if not product or not audience:
            st.warning("Please fill all fields")
        else:
            prompt = f"""
            Create high-conversion marketing content.

            Product: {product}
            Audience: {audience}

            Include:
            - Clear value proposition
            - 3 key benefits
            - Strong CTA
            """

            with st.spinner("Generating content..."):
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}]
                )
                st.session_state.text = response.choices[0].message.content

with col2:
    st.subheader("📤 Export to Google Drive")

    if "text" in st.session_state:
        edited_text = st.text_area(
            "Final Content",
            st.session_state.text,
            height=300
        )

        filename = st.text_input(
            "File Name",
            value="marketing_copy.txt"
        )

        if st.button("🚀 Upload to Drive"):
            with st.spinner("Uploading..."):
                try:
                    fid, fname = upload_file_to_drive(filename, edited_text)
                    st.success("✅ Uploaded Successfully")
                    st.write("File Name:", fname)
                    st.balloons()
                except Exception as e:
                    st.error(str(e))
    else:
        st.info("Generate content to enable export")


