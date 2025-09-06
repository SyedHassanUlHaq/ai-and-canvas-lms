from sentence_transformers import SentenceTransformer
import numpy as np
import re


# Load embedding model once (cached in memory)
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

async def embed_course_doc(content: str, doc_name: str, module_name: str):
        
    text = content.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s\-\.]', '', text)
    
    text = text.strip()
    print('text: ', text)
    embedding = model.encode(text, convert_to_numpy=True, normalize_embeddings=True, device='cpu')
    
    return {
        "doc_name": doc_name,
        "module_name": module_name,
        "content": text,
        "embedding": embedding.tolist()  # for JSON/db storage
    }

# doc = embed_course_doc(
#     "Artificial Intelligence is the simulation of human intelligence in machines...",
#     "Intro_AI",
#     "Module 1"
# )

# print(doc.keys())