import streamlit as st
from groq import Groq
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# --- 1. Google Drive Helper Functions ---

def get_drive_service():
    """Authenticates using Streamlit Secrets."""
    creds_info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(
        creds_info, 
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)

def get_or_create_folder(service, folder_name):
    """Checks if a folder exists; if not, creates it."""
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])

    if items:
        return items[0]['id']
    else:
        # Create new folder
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        file = service.files().create(body=folder_metadata, fields='id').execute()
        return file.get('id')

def upload_to_drive(filename, text_content, folder_name, user_email):
    """Uploads file to specific folder and grants user permission."""
    service = get_drive_service()
    
    # 1. Get Folder ID
    folder_id = get_or_create_folder(service, folder_name)
    
    # 2. Upload File
    file_metadata = {
        'name': filename,
        'mimeType': 'text/plain',
        'parents': [folder_id]
    }
    
    fh = io.BytesIO(text_content.encode('utf-8'))
    media = MediaIoBaseUpload(fh, mimetype='text/plain', resumable=True)

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name'
    ).execute()
    file_id = file.get('id')

    # 3. Transfer/Grant Permission to your normal Google Account
    # This prevents the "Quota Exceeded" error by linking it to a real user
    permission = {
        'type': 'user',
        'role': 'writer',
        'emailAddress': user_email
    }
    service.permissions().create(fileId=file_id, body=permission).execute()

    return file_id, file.get('name')

# --- 2. PragyanAI App Interface ---

st.set_page_config(page_title="PragyanAI Marketing Gen", layout="wide")

# Ensure keys are present
if "GROQ_API_KEY" not in st.secrets or "gcp_service_account" not in st.secrets:
    st.error("Missing API keys in Streamlit Secrets!")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.title("📢 PragyanAI: Content Generator & Drive Exporter")

# Sidebar for Settings
with st.sidebar:
    st.header("Settings")
    user_email = st.text_input("Your Google Email", placeholder="your-email@gmail.com", help="Used to grant you access to the uploaded file.")
    target_folder = st.text_input("Drive Folder Name", value="PragyanAI_Uploads")
    target_filename = st.text_input("Filename", value="marketing_copy.txt")

# Main UI
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Generate Content")
    product = st.text_input("Product Name")
    audience = st.text_input("Target Audience")
    tone = st.selectbox("Tone", ["Professional", "Casual", "Exciting", "Urgent"])

    if st.button("Generate Strategy"):
        prompt = f"Create marketing content for {product} targeting {audience} in a {tone} tone. Provide a catchy headline, 3 bullet points, and a LinkedIn post."
        
        with st.spinner("AI is thinking..."):
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
            )
            st.session_state.gen_text = response.choices[0].message.content

with col2:
    st.subheader("Preview & Export")
    if 'gen_text' in st.session_state:
        output_text = st.text_area("Generated Output", st.session_state.gen_text, height=300)
        
        if st.button("🚀 Upload to Google Drive"):
            if not user_email:
                st.warning("Please enter your email in the sidebar first!")
            else:
                try:
                    with st.spinner("Uploading and setting permissions..."):
                        f_id, f_name = upload_to_drive(target_filename, output_text, target_folder, user_email)
                        st.success(f"✅ Uploaded Successfully!")
                        st.write(f"**File Name:** {f_name}")
                        st.write(f"**File ID:** `{f_id}`")
                        st.info("Check your 'Shared with me' or the specific folder in your Drive.")
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.info("Generate content on the left to see the preview here.") 
