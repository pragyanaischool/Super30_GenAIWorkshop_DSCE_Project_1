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

def upload_to_drive(filename, text_content, folder_id):
    """
    Uploads file to a pre-existing folder shared with the service account.
    This avoids the 'Storage Quota Exceeded' error.
    """
    service = get_drive_service()
    
    # File metadata pointing to your shared folder
    file_metadata = {
        'name': filename,
        'mimeType': 'text/plain',
        'parents': [folder_id]
    }
    
    # Convert string to byte stream
    fh = io.BytesIO(text_content.encode('utf-8'))
    media = MediaIoBaseUpload(fh, mimetype='text/plain', resumable=True)

    # Create the file in the parent folder
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
service_account_email = st.secrets["gcp_service_account"]["client_email"]

st.title("📢 PragyanAI: Content Generator & Drive Exporter")

# Sidebar for Settings
with st.sidebar:
    st.header("Drive Configuration")
    st.info(f"**Step 1:** Share your Drive folder with this email as 'Editor': \n`{service_account_email}`")
    
    target_folder_id = st.text_input(
        "Step 2: Enter Folder ID", 
        placeholder="The ID from the folder URL",
        help="Example: In 'drive.google.com/drive/folders/1abc123...', the ID is '1abc123...'"
    )
    
    target_filename = st.text_input("Filename", value="marketing_copy.txt")

# Main UI
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Generate Content")
    product = st.text_input("Product Name", placeholder="e.g. PragyanAI Learning Platform")
    audience = st.text_input("Target Audience", placeholder="e.g. Engineering Students")
    tone = st.selectbox("Tone", ["Professional", "Casual", "Exciting", "Urgent"])

    if st.button("Generate Strategy"):
        if not product or not audience:
            st.warning("Please fill in the product and audience fields.")
        else:
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
            if not target_folder_id:
                st.error("Please provide a Folder ID in the sidebar!")
            else:
                try:
                    with st.spinner("Uploading to your shared folder..."):
                        f_id, f_name = upload_to_drive(target_filename, output_text, target_folder_id)
                        st.success(f"✅ Uploaded Successfully!")
                        st.write(f"**File Name:** {f_name}")
                        st.write(f"**File ID:** `{f_id}`")
                except Exception as e:
                    if "storageQuotaExceeded" in str(e):
                        st.error("Quota Error: You must share the folder with the Service Account email and ensure you have space in your personal Drive.")
                    else:
                        st.error(f"Error: {e}")
    else:
        st.info("Generate content on the left to see the preview here.")
