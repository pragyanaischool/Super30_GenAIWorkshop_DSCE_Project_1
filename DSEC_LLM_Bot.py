from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import streamlit as st
from groq import Groq
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import os

# --- 1. Google Drive Logic (Service Account) ---
def get_drive_service():
    # Fetch credentials from Streamlit Secrets
    creds_info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(
        creds_info, 
        scopes=['https://www.googleapis.com/auth/drive.file']
    )
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(filename, text_content):
    service = get_drive_service()
    
    # Metadata for the file
    file_metadata = {
        'name': filename,
        'mimeType': 'text/plain'
    }
    
    # Convert string content to a byte stream for upload
    fh = io.BytesIO(text_content.encode('utf-8'))
    media = MediaIoBaseUpload(fh, mimetype='text/plain', resumable=True)

    # Create the file in Drive
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name'
    ).execute()

    return file.get('id'), file.get('name')
 # --- 2. Groq AI Setup ---
st.set_page_config(page_title="PragyanAI GenAI → Google Drive Export")
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 3. UI Implementation ---
st.title("📢 PragyanAI Marketing Content Generator")
st.info("Files will be uploaded to the Service Account's Drive. Make sure to share your target folder with the service account email.")

# Sidebar/Inputs
product = st.text_input("Product / Service Name")
audience = st.text_input("Target Audience")
tone = st.selectbox("Tone", ["Professional", "Casual", "Exciting"])

# Use Session State to keep the text alive after clicking upload
if 'generated_text' not in st.session_state:
    st.session_state.generated_text = ""

if st.button("Generate Content"):
    prompt = f"Create marketing content for:\nProduct: {product}\nAudience: {audience}\nTone: {tone}\n\nGenerate: 1. Ad copy 2. Email subject 3. LinkedIn post"
    
    with st.spinner("Brainstorming..."):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
        )
        st.session_state.generated_text = response.choices[0].message.content

# Display Generated Content
if st.session_state.generated_text:
    st.subheader("✨ Generated Content")
    st.text_area("Preview", st.session_state.generated_text, height=200)

    # Upload Section
    file_name = st.text_input("File name for Google Drive", value="pragyan_content.txt")
    
    if st.button("Upload to Google Drive"):
        if not file_name.strip():
            st.error("❌ Please enter a valid file name")
        else:
            try:
                with st.spinner("Uploading..."):
                    file_id, name = upload_to_drive(file_name, st.session_state.generated_text)
                    st.success(f"✅ File '{name}' uploaded successfully!")
                    st.write(f"**Drive File ID:** `{file_id}`")
            except Exception as e:
                st.error(f"Upload failed: {e}")   
'''
groq_key = st.secrets["GROQ_API_KEY"]
st.write("Keys loaded successfully ✅")

client = Groq(
    api_key=groq_key
)

st.set_page_config(page_title="PragyanAI GenAI → Google Drive Export")
st.title("📢 PragyanAI Marketing Content Generator (Export to Google Drive)")

product = st.text_input("Product / Service Name")
audience = st.text_input("Target Audience")
tone = st.selectbox("Tone", ["Professional", "Casual", "Exciting"])

generated_text = ""

if st.button("Generate Content"):
    prompt = f"""
    Create marketing content for:
    Product: {product}
    Audience: {audience}
    Tone: {tone}

    Generate:
    1. One-line ad copy
    2. Email subject line
    3. LinkedIn post
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )

    generated_text = response.choices[0].message.content
    st.subheader("✨ Generated Content")
    st.write(generated_text)

file_name = st.text_input(
    "Enter file name to save in Google Drive",
    value="generated_content.txt"
)
if st.button("Upload to Google Drive"):
    if not file_name.strip():
        st.error("❌ Please enter a valid file name")
    else:
        file_id, name = upload_to_drive(file_name, generated_text)
        st.success(f"✅ File '{name}' uploaded successfully!")
        st.write("Drive File ID:", file_id)
'''
