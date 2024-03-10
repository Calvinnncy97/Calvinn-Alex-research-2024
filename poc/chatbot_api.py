from fastapi import FastAPI
from pydantic import BaseModel
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
import chromadb
from transformers import AutoModel
from typing import List
from chromadb import Documents, EmbeddingFunction, Embeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain.load import dumps, loads
from operator import itemgetter
from langchain_openai import ChatOpenAI
from retriever import Retriever
from chatbot import ChatBot

class RAGQueryInput(BaseModel):
    text: str

class JinaEmbedder(EmbeddingFunction):
    model = AutoModel.from_pretrained('jinaai/jina-embeddings-v2-base-en', trust_remote_code=True)

    def __call__(self, input: Documents) -> Embeddings:
        # embed the documents somehow
        return self.model.encode(input)

    def embed_query(self, text: str) -> List[float]:
        return self.model.encode([text])[0].tolist()

retriever = Retriever(chromadb_path="/home/calvinnncy/Projects/MarketGPT/rag-from-scratch/jina_chroma",
                      embedding_function=JinaEmbedder())

chatbot = ChatBot()

app = FastAPI(
    title="Pew Research Chatbot",
    description="Endpoints for Pew Research RAG chatbot",
)

@app.get("/")
async def get_status():
    return {"status": "running"}


@app.post("/pew-research-rag-agent")
async def ask_rag_agent(query: RAGQueryInput):
    # docs = retriever.retrieve(query.text)
    response, docs = chatbot.get_response(user_input=query.text)
    response = response.content
    return {'response': response, 'docs': docs}