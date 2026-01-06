import streamlit as st
from groq import Groq
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# -------------------------------------------------
# 1. GOOGLE DRIVE HELPERS (SHARED DRIVE SAFE)
# -------------------------------------------------

def get_drive_service():
    creds_info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)


def find_folder_id(service, folder_name):
    query = (
        f"name = '{folder_name}' "
        "and mimeType = 'application/vnd.google-apps.folder' "
        "and trashed = false"
    )

    response = service.files().list(
        q=query,
        corpora="allDrives",
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        fields="files(id, name, driveId)"
    ).execute()

    folders = response.get("files", [])
    if not folders:
        return None

    return folders[0]["id"]


def upload_to_drive(filename, text_content, folder_name):
    service = get_drive_service()

    folder_id = find_folder_id(service, folder_name)
    if not folder_id:
        raise Exception(
            f"Folder '{folder_name}' not found in Shared Drive. "
            "Ensure it exists and is shared with the service account."
        )

    file_metadata = {
        "name": filename,
        "parents": [folder_id],
        "mimeType": "text/plain"
    }

    fh = io.BytesIO(text_content.encode("utf-8"))
    media = MediaIoBaseUpload(fh, mimetype="text/plain", resumable=True)

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name",
        supportsAllDrives=True
    ).execute()

    return file["id"], file["name"]

# -------------------------------------------------
# 2. STREAMLIT APP UI
# -------------------------------------------------

st.set_page_config(
    page_title="PragyanAI Marketing Generator",
    layout="wide"
)

# Validate secrets
if "GROQ_API_KEY" not in st.secrets or "gcp_service_account" not in st.secrets:
    st.error("❌ Missing GROQ or Google Service Account credentials")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
sa_email = st.secrets["gcp_service_account"]["client_email"]

st.title("📢 PragyanAI – AI Marketing Content Generator")

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------

with st.sidebar:
    st.header("🔐 Google Drive Config")
    st.info("Using **Shared Drive (Quota Safe)**")

    st.write("Service Account Email:")
    st.code(sa_email)

    st.divider()
    target_folder = st.text_input(
        "Target Folder Name",
        value="Drive_Connect"
    )
    target_filename = st.text_input(
        "Output File Name",
        value="marketing_copy.txt"
    )

# -------------------------------------------------
# MAIN UI
# -------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    st.subheader("✍️ Generate Marketing Content")

    product = st.text_input("Product / Program Name")
    audience = st.text_input("Target Audience")

    if st.button("⚡ Generate Content"):
        if not product or not audience:
            st.warning("Please fill in all fields.")
        else:
            prompt = f"""
            Create high-conversion marketing content for:
            Product: {product}
            Target Audience: {audience}

            Include:
            - Clear value proposition
            - 3 key benefits
            - Strong CTA
            """

            with st.spinner("AI is generating content..."):
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}]
                )

                st.session_state.generated_text = (
                    response.choices[0].message.content
                )

with col2:
    st.subheader("📤 Preview & Upload")

    if "generated_text" in st.session_state:
        output_text = st.text_area(
            "Generated Content",
            st.session_state.generated_text,
            height=320
        )

        if st.button("🚀 Upload to Google Drive"):
            with st.spinner("Uploading to Shared Drive..."):
                try:
                    file_id, file_name = upload_to_drive(
                        target_filename,
                        output_text,
                        target_folder
                    )
                    st.success("✅ File uploaded successfully!")
                    st.write("File Name:", file_name)
                    st.balloons()
                except Exception as e:
                    st.error(str(e))
    else:
        st.info("Generate content first to preview and upload.")

