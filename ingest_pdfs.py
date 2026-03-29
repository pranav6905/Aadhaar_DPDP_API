import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEndpointEmbeddings 
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index_name = os.environ.get("PINECONE_INDEX_NAME")

if index_name not in pc.list_indexes().names():
    print(f"Creating index {index_name}...")
    pc.create_index(
        name=index_name,
        dimension=384,  
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

print("Loading PDFs...")
documents = []
for file in ["43.pdf", "dpdp_act_2023.pdf"]: 
    if os.path.exists(file):
        loader = PyPDFLoader(file)
        documents.extend(loader.load())
    else:
        print(f"Warning: {file} not found. Skipping.")

print("Chunking text...")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
chunks = text_splitter.split_documents(documents)

print("Generating Embeddings via Hugging Face API...")
# Using the API instead of local download
embeddings = HuggingFaceEndpointEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2",
    task="feature-extraction",
    huggingfacehub_api_token=os.environ.get("HF_TOKEN")
)

PineconeVectorStore.from_documents(chunks, embeddings, index_name=index_name)
print("Ingestion Complete! The database is ready.")