import os
import sys

# Ensure infrastructure can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import PyPDF2
from infrastructure.doc_store import DocumentStore

def parse_pdf(file_path):
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Failed to read PDF {file_path}: {e}")
    return text

def chunk_text(text, chunk_size=1000, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks

def ingest_directory(directory_path, collection_name="npci_circulars"):
    store = DocumentStore(use_memory=False)
    store.initialize_collection(collection_name)
    
    for filename in os.listdir(directory_path):
        if filename.endswith(".pdf"):
            full_path = os.path.join(directory_path, filename)
            print(f"Parsing {filename}...")
            text = parse_pdf(full_path)
            if not text.strip():
                continue
                
            chunks = chunk_text(text)
            for i, chunk in enumerate(chunks):
                doc_id = f"{filename}_chunk_{i}"
                print(f"Ingesting chunk {i} for {filename}...")
                store.ingest_document(
                    doc_id=doc_id, 
                    text=chunk, 
                    metadata={"source_file": filename, "chunk_index": i},
                    collection_name=collection_name
                )
    print("Ingestion complete.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "." # Fallback to current directory meaning root of demo
    ingest_directory(directory)
