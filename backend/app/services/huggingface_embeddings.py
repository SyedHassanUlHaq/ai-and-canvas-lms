import re
from array import array

# import vertexai
# from vertexai.language_models import TextEmbeddingModel

# initialize vertexai
from app.core.config import embedding_model

async def embed_course_doc(content: str, doc_name: str, module_name: str):
    text = content.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s\-\.]', '', text)
    text = text.strip()
    print("text:", text)

    # The API expects an input object or list of inputs
    embeddings = embedding_model.get_embeddings([text])
    # embeddings is a list of embedding objects; get the `.values`
    embedding = array("f", embeddings[0].values)

    return {
        "doc_name": doc_name,
        "module_name": module_name,
        "content": text,
        "embedding": embedding.tolist()
    }
