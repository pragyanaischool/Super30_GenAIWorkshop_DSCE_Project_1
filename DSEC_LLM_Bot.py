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

def find_folder_id(service, folder_name):
    """Searches for the Folder ID by its name."""
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    
    if not items:
        return None
    return items[0]['id']

def upload_to_drive(filename, text_content, folder_name):
    """Finds folder ID and uploads file into YOUR storage space."""
    service = get_drive_service()
    
    # 1. Look up the ID for "Drive_Connect"
    folder_id = find_folder_id(service, folder_name)
    
    if not folder_id:
        raise Exception(f"Folder '{folder_name}' not found. Did you share it with the service account?")

    # 2. Set metadata. Specifying the 'parents' is what fixes the 403 error.
    file_metadata = {
        'name': filename,
        'mimeType': 'text/plain',
        'parents': [folder_id] 
    }
    
    # 3. Stream the content
    fh = io.BytesIO(text_content.encode('utf-8'))
    media = MediaIoBaseUpload(fh, mimetype='text/plain', resumable=True)

    # 4. Upload
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name'
    ).execute()
    
    return file.get('id'), file.get('name')

# --- 2. PragyanAI App Interface ---

st.set_page_config(page_title="PragyanAI Marketing Gen", layout="wide")

# Ensure keys are present
if "GROQ_API_KEY" not in st.secrets or "gcp_service_account" not in st.secrets:
    st.error("Missing API keys in Streamlit Secrets!")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
sa_email = st.secrets["gcp_service_account"]["client_email"]

st.title("📢 PragyanAI: Content Generator & Drive Exporter")

# Sidebar for Settings
with st.sidebar:
    st.header("Drive Settings")
    st.write("**Mandatory Step:**")
    st.write(f"1. Go to your Google Drive folder **Drive_Connect**.")
    st.write(f"2. Click 'Share' and add this email as **Editor**:")
    st.code(sa_email)
    
    st.divider()
    
    target_folder = st.text_input("Drive Folder Name", value="Drive_Connect")
    target_filename = st.text_input("Save As (Filename)", value="marketing_copy.txt")

# Main UI
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Generate Content")
    product = st.text_input("Product Name")
    audience = st.text_input("Target Audience")
    tone = st.selectbox("Tone", ["Professional", "Casual", "Exciting", "Urgent"])

    if st.button("Generate Strategy"):
        if product and audience:
            prompt = f"Create marketing content for {product} targeting {audience} in a {tone} tone."
            with st.spinner("AI is thinking..."):
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                )
                st.session_state.gen_text = response.choices[0].message.content
        else:
            st.warning("Enter product and audience.")

with col2:
    st.subheader("Preview & Export")
    if 'gen_text' in st.session_state:
        output_text = st.text_area("Generated Output", st.session_state.gen_text, height=300)
        
        if st.button("🚀 Upload to Google Drive"):
            try:
                with st.spinner(f"Uploading to '{target_folder}'..."):
                    f_id, f_name = upload_to_drive(target_filename, output_text, target_folder)
                    st.success(f"✅ Successfully uploaded to Drive_Connect!")
                    st.balloons()
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.info("Generate content on the left first.")
        
