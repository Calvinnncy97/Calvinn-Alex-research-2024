from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import json
from typing import List
from chromadb import Documents
from retriever import Retriever
from chromadb import Documents, EmbeddingFunction, Embeddings
from transformers import AutoModel


class JinaEmbedder(EmbeddingFunction):
    model = AutoModel.from_pretrained('jinaai/jina-embeddings-v2-base-en', trust_remote_code=True)

    def __call__(self, input: Documents) -> Embeddings:
        # embed the documents somehow
        return self.model.encode(input)

    def embed_query(self, text: str) -> List[float]:
        return self.model.encode([text])[0].tolist()

answer_template = """You are a professional Market Research. 
Whenever you answer a question, you cite your answers based on the source of the provided information.
You cite your answer by putting the id of the source in square brackets beside the answer. 
Answer the following question based on this context:

{context}

Question: {question}
"""

system_prompt = """"""



# response = openai.ChatCompletion.create(
#                         api_key=self.__openai_key,
#                         model="gpt-3.5-turbo-0301",
#                         messages=incoming_message,
#                         temperature=0.2,
#                         top_p=1,
#                         frequency_penalty=1,
#                         presence_penalty=0.2
#                     )
#             return response['choices'][0]['message']['content']


class ChatBot:
    def __init__(self) -> None:
        self.prompt = ChatPromptTemplate.from_template(answer_template)
        self.llm = ChatOpenAI(temperature=0)
        self.chat_history = [
                {
                    "role": "system", 
                    "content": system_prompt
                }
            ]
        self.retriever = Retriever(chromadb_path="/home/calvinnncy/Projects/MarketGPT/rag-from-scratch/jina_chroma",
                      embedding_function=JinaEmbedder())
    
    def _check_if_need_rag(self, chat_history: List[dict]):
        prompt = """"""

    def get_rag_response(self, query: str, context: List[dict]):
        context = json.dumps(
                            context,
                            indent=2
                        )
        print(context)
        return self.llm.invoke(
                    self.prompt.format(
                        context=context, 
                        question=query)
                    )

    def get_response(self, user_input: str):
        chat_context = []
        for chat in reversed(self.chat_history):
            # Exclude system prompt from query generation and only include 6 messages
            if chat['role'] != 'system' and len(chat) <=6 :
                chat_context.append(chat)
                continue
            break
        chat_context = reversed(chat_context)
        chat_context = "\n\n".join([f"Role: {c['role']}\nContent: {c['content']}" for c in chat_context])

        retrieved_documents = self.retriever.retrieval_chain.invoke({"chat_history" : chat_context, "query" : user_input})
        context = [{'id': i, 'content': d.page_content, 'source': d.metadata['source']} for i, d in enumerate(retrieved_documents)]
        response = self.get_rag_response(query=user_input, context=context)
        self.chat_history.append({
            "role" : "user",
            "content" : user_input
        })
        self.chat_history.append({
            "role" : "assistant",
            "content" : response
        })

        return response, context
       