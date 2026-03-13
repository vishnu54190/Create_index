from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
import time
import os

load_dotenv()

def chunk_data(docs, chunk_size=500, chunk_overlap=150):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return splitter.split_documents(docs)

def create_index(index_name: str, pc: Pinecone):
    existing = [i.name for i in pc.list_indexes()]

    if index_name in existing:
        print(f"Index '{index_name}' already exists. Skipping creation.")
        return

    print(f"Creating index '{index_name}'...")
    pc.create_index(
        name=index_name,
        dimension=384,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

    while not pc.describe_index(index_name).status["ready"]:
        print("Waiting for index to be ready...")
        time.sleep(1)
    print(f"Index '{index_name}' is ready.")

def index_documents(folder_path: str, index_name: str):
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist.")
        return

    pdf_files = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]
    if not pdf_files:
        print(f"Error: No PDFs found in '{folder_path}'.")
        return

    print(f"Found {len(pdf_files)} PDF(s): {pdf_files}")

    print("Loading PDFs...")
    loader = PyPDFDirectoryLoader(folder_path)
    documents = loader.load()
    print(f"Loaded {len(documents)} pages")

    print("Chunking...")
    chunks = chunk_data(documents)
    print(f"Created {len(chunks)} chunks")

    print("Loading embedding model...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/multi-qa-MiniLM-L6-cos-v1"
    )

    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    create_index(index_name, pc)

    print(f"Uploading vectors to '{index_name}'...")
    PineconeVectorStore.from_documents(
        chunks,
        embeddings,
        index_name=index_name
    )
    print(f"Done. Index '{index_name}' is ready to query.")

if __name__ == "__main__":
    folder_path = input("Enter folder path: ").strip()
    index_name  = input("Enter index name (lowercase, hyphens only): ").strip()
    index_documents(folder_path, index_name)