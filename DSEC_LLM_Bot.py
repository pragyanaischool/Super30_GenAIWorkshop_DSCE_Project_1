import streamlit as st
from groq import Groq
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# =================================================
# CONFIG (DO NOT CHANGE UNLESS DRIVE NAME CHANGES)
# =================================================
SHARED_DRIVE_NAME = "PragyanAI_Automations"
TARGET_FOLDER_NAME = "Drive_Connect"

# =================================================
# GOOGLE DRIVE HELPERS (SHARED DRIVE ONLY)
# =================================================

def get_drive_service():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)


def get_shared_drive_id(service):
    drives = service.drives().list().execute().get("drives", [])
    for drive in drives:
        if drive["name"] == SHARED_DRIVE_NAME:
            return drive["id"]
    return None


def get_folder_id(service, drive_id):
    query = (
        f"name = '{TARGET_FOLDER_NAME}' "
        "and mimeType = 'application/vnd.google-apps.folder' "
        "and trashed = false"
    )

    result = service.files().list(
        q=query,
        corpora="drive",
        driveId=drive_id,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        fields="files(id, name)"
    ).execute()

    folders = result.get("files", [])
    if not folders:
        return None
    return folders[0]["id"]


def upload_text_file(filename, content):
    service = get_drive_service()

    drive_id = get_shared_drive_id(service)
    if not drive_id:
        raise Exception("❌ Shared Drive not found")

    folder_id = get_folder_id(service, drive_id)
    if not folder_id:
        raise Exception("❌ Folder not found inside Shared Drive")

    metadata = {
        "name": filename,
        "parents": [folder_id]
    }

    buffer = io.BytesIO(content.encode("utf-8"))
    media = MediaIoBaseUpload(buffer, mimetype="text/plain", resumable=True)

    file = service.files().create(
        body=metadata,
        media_body=media,
        supportsAllDrives=True,
        fields="id, name"
    ).execute()

    return file["id"], file["name"]

# =================================================
# STREAMLIT UI
# =================================================

st.set_page_config("PragyanAI Marketing Generator", layout="wide")

if "GROQ_API_KEY" not in st.secrets:
    st.error("Missing GROQ API Key")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.title("📢 PragyanAI – Marketing Content Generator")

with st.sidebar:
    st.header("🔐 Google Drive Status")
    st.success("Shared Drive Mode (Quota Safe)")
    st.write("Shared Drive:", SHARED_DRIVE_NAME)
    st.write("Folder:", TARGET_FOLDER_NAME)
    st.code(st.secrets["gcp_service_account"]["client_email"])

col1, col2 = st.columns(2)

with col1:
    st.subheader("✍️ Generate Content")
    product = st.text_input("Product / Program Name")
    audience = st.text_input("Target Audience")

    if st.button("Generate Content"):
        if not product or not audience:
            st.warning("Fill all fields")
        else:
            prompt = f"""
            Create high-conversion marketing content.

            Product: {product}
            Audience: {audience}

            Include:
            - Clear value proposition
            - 3 bullet benefits
            - Strong CTA
            """

            with st.spinner("Generating..."):
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}]
                )
                st.session_state.text = response.choices[0].message.content

with col2:
    st.subheader("📤 Preview & Upload")

    if "text" in st.session_state:
        edited_text = st.text_area(
            "Generated Content",
            st.session_state.text,
            height=320
        )

        filename = st.text_input(
            "File Name",
            value="marketing_copy.txt"
        )

        if st.button("🚀 Upload to Google Drive"):
            with st.spinner("Uploading to Shared Drive..."):
                try:
                    fid, fname = upload_text_file(filename, edited_text)
                    st.success("✅ Uploaded Successfully")
                    st.write("File:", fname)
                    st.balloons()
                except Exception as e:
                    st.error(str(e))
    else:
        st.info("Generate content first")

