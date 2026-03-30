import streamlit as st
import requests
from PIL import Image
import io

# --- Page Configuration ---
st.set_page_config(
    page_title="Aadhaar Privacy & DPDP Guard",
    page_icon="🛡️",
    layout="wide"
)

# --- Backend API URLs ---
# Make sure your FastAPI server is running on this port!
API_URL_MASK = "http://127.0.0.1:8000/api/v1/mask-aadhaar-image"
API_URL_POLICY = "http://127.0.0.1:8000/api/v1/check-policy"

# --- Main Dashboard UI ---
st.title("🛡️ DPDP Act & Aadhaar Compliance Engine")
st.markdown("""
This platform acts as an automated "Privacy Guard." It enforces the Supreme Court's 
**Puttaswamy** guidelines and the **DPDP Act 2023** by masking sensitive biometric identifiers 
and auditing corporate data policies in real-time.
""")
st.divider()

# Create two tabs for the two different features
tab1, tab2 = st.tabs(["📸 Visual Aadhaar Masking (OCR)", "⚖️ Legal Policy Auditor (RAG)"])

# ==========================================
# TAB 1: IMAGE MASKING
# ==========================================
with tab1:
    st.header("Visual Data Minimization")
    st.write("Upload an Aadhaar card image. The system will use OCR to locate the 12-digit number and apply a redaction mask over the first 8 digits.")
    
    uploaded_file = st.file_uploader("Upload Aadhaar Image (JPG/PNG)", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        col1, col2 = st.columns(2)
        
        # Display the original image
        with col1:
            st.subheader("Original Upload")
            image = Image.open(uploaded_file)
            st.image(image, use_container_width=True)
            
        with col2:
            st.subheader("DPDP Compliant Output")
            if st.button("Apply Privacy Mask", type="primary"):
                with st.spinner("Running OCR and applying mask..."):
                    # Reset file pointer to beginning before sending
                    uploaded_file.seek(0)
                    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                    
                    try:
                        # Send image to your FastAPI backend
                        response = requests.post(API_URL_MASK, files=files)
                        
                        if response.status_code == 200:
                            # Read the returned masked image bytes
                            masked_image = Image.open(io.BytesIO(response.content))
                            st.image(masked_image, use_container_width=True)
                            st.success("Data Minimization Applied! First 8 digits redacted.")
                        else:
                            st.error(f"API Error: {response.status_code}")
                    except requests.exceptions.ConnectionError:
                        st.error("Could not connect to the Backend API. Is your FastAPI server running?")

# ==========================================
# TAB 2: POLICY CHECKER
# ==========================================
with tab2:
    st.header("Corporate Policy Compliance Checker")
    st.write("Paste a proposed corporate data policy. The AI will cross-reference it against the **Puttaswamy Judgment** and **DPDP Act** vector database.")
    
    policy_text = st.text_area(
        "Enter Proposed Data Policy:", 
        height=150,
        placeholder="e.g., We will indefinitely store user biometric data collected during Aadhaar authentication to improve our machine learning models."
    )
    
    if st.button("Run Legal Audit", type="primary"):
        if policy_text.strip() == "":
            st.warning("Please enter a policy to audit.")
        else:
            with st.spinner("Querying Legal Vector Database (Pinecone)..."):
                payload = {"proposed_policy": policy_text}
                
                try:
                    # Send policy to your FastAPI backend
                    response = requests.post(API_URL_POLICY, json=payload)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Display results nicely
                        st.subheader("Audit Results")
                        
                        # Use markdown to render the bolding and bullet points from Gemini
                        st.markdown(result["legal_analysis"])
                        
                    else:
                        st.error(f"API Error: {response.status_code}")
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to the Backend API. Is your FastAPI server running?")