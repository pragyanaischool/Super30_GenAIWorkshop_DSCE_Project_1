from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os
import streamlit as st
from groq import Groq

SCOPES = ['https://www.googleapis.com/auth/drive.file']
def get_drive_service():
    creds = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

def upload_to_drive(filename, content):
    service = get_drive_service()

    file_metadata = {'name': filename}
    media = {
        'mimeType': 'text/plain',
        'body': content
    }

    file = service.files().create(
        body=file_metadata,
        media_body=None,
        fields='id'
    ).execute()

    file_id = file.get('id')

    service.files().update(
        fileId=file_id,
        media_body=content
    ).execute()

    return file_id

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
