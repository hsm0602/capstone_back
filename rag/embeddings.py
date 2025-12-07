import os
from dotenv import load_dotenv

load_dotenv()
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

EMBED_MODEL_NAME = os.getenv("HF_EMBED_MODEL", "BAAI/bge-m3")
VECTORSTORE_DIR = os.getenv("VECTORSTORE_DIR", "data/chroma_plan")

embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL_NAME)

def get_vectorstore() -> Chroma:
    return Chroma(
        persist_directory=VECTORSTORE_DIR,
        embedding_function=embeddings,
    )
