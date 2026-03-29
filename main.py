import os
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

import cv2
import numpy as np
import pytesseract
from fastapi import UploadFile, File
from fastapi.responses import Response
import re

# IMPORTANT: Point pytesseract to your Windows installation path
# (You will remove/change this line later when deploying to a Linux cloud server)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Simplified Langchain imports (No 'chains' required)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEndpointEmbeddings 
from langchain_pinecone import PineconeVectorStore

load_dotenv()

app = FastAPI(title="Aadhaar & DPDP Compliance API Engine")

# Initialize Gemini
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)

# Initialize Hugging Face Embeddings via API
embeddings = HuggingFaceEndpointEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2",
    task="feature-extraction",
    huggingfacehub_api_token=os.environ.get("HF_TOKEN")
)

# Connect to Pinecone
index_name = os.environ.get("PINECONE_INDEX_NAME")
vectorstore = PineconeVectorStore(index_name=index_name, embedding=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

# API Data Models
class DataPayload(BaseModel):
    user_text: str

class PolicyPayload(BaseModel):
    proposed_policy: str

@app.post("/api/v1/mask-data")
async def mask_pii_data(payload: DataPayload):
    """
    Endpoint 1: Uses Gemini to detect and mask PII and Aadhaar data.
    """
    system_prompt = (
        "You are a strict data-masking algorithm complying with the DPDP Act. "
        "Your only job is to output the exact text provided by the user, but replace any "
        "Aadhaar numbers (12 digits), names of people, and biometric identifiers (e.g., fingerprints, iris scans) "
        "with the string '[MASKED]'. Do not add any conversational text or explanations. Just return the masked text."
    )
    
    messages = [
        ("system", system_prompt),
        ("human", payload.user_text),
    ]
    response = llm.invoke(messages)
    
    return {
        "status": "success",
        "dpdp_rule_applied": "Data Minimization & PII Masking",
        "sanitized_data": response.content.strip()
    }

@app.post("/api/v1/check-policy")
async def check_legal_compliance(payload: PolicyPayload):
    """
    Endpoint 2: Custom RAG Pipeline bypassing Langchain's chain wrappers.
    """
    # 1. Retrieve the relevant legal chunks directly from Pinecone
    docs = retriever.invoke(payload.proposed_policy)
    
    # Combine the retrieved text into a single string
    context_text = "\n\n".join([doc.page_content for doc in docs])
    
    # 2. Inject the context directly into the system prompt
    system_prompt = f"""You are an expert Indian data privacy auditor. 
Evaluate the user's proposed data policy using ONLY the retrieved context from the Puttaswamy Aadhaar judgment and the DPDP Act below. 
Determine if the policy is 'Compliant' or 'Non-Compliant' and provide a brief, strict legal justification citing the provided context.

Context:
{context_text}"""
    
    messages = [
        ("system", system_prompt),
        ("human", f"Proposed Policy: {payload.proposed_policy}"),
    ]
    
    # 3. Generate the AI response
    response = llm.invoke(messages)
    
    return {
        "status": "evaluation_complete",
        "policy_analyzed": payload.proposed_policy,
        "legal_analysis": response.content.strip()
    }

@app.post("/api/v1/mask-aadhaar-image")
async def mask_image_endpoint(file: UploadFile = File(...)):
    # 1. Read the uploaded image
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 2. Preprocess: Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 3. OCR Configuration
    custom_config = r'--oem 3 --psm 6'
    ocr_data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT, config=custom_config)
    
    n_boxes = len(ocr_data['text'])
    
    # --- NEW LOGIC: Sequence Detection ---
    # First, filter out the empty strings Tesseract creates for blank spaces
    valid_blocks = []
    for i in range(n_boxes):
        text = ocr_data['text'][i].strip()
        if text != '':
            valid_blocks.append((i, text))
            
    # Now, use a sliding window to look for three 4-digit numbers in a row
    for j in range(len(valid_blocks) - 2):
        idx1, text1 = valid_blocks[j]
        idx2, text2 = valid_blocks[j+1]
        idx3, text3 = valid_blocks[j+2]
        
        # Check if all three consecutive words are exactly 4 digits
        if re.fullmatch(r'\d{4}', text1) and re.fullmatch(r'\d{4}', text2) and re.fullmatch(r'\d{4}', text3):
            print(f"✅ SUCCESS! Found Aadhaar sequence: {text1} {text2} {text3}")
            
            # Mask the first 8 digits (which correspond to idx1 and idx2)
            for mask_idx in [idx1, idx2]:
                x = ocr_data['left'][mask_idx]
                y = ocr_data['top'][mask_idx]
                w = ocr_data['width'][mask_idx]
                h = ocr_data['height'][mask_idx]
                
                # Draw a solid black rectangle slightly larger than the text box
                cv2.rectangle(img, (x-2, y-2), (x + w + 2, y + h + 2), (0, 0, 0), -1)

    # 4. Convert and return the masked image
    _, encoded_img = cv2.imencode('.png', img)
    return Response(content=encoded_img.tobytes(), media_type="image/png")