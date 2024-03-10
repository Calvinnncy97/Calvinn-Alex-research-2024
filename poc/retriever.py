from chromadb import EmbeddingFunction, PersistentClient
from langchain_community.vectorstores import Chroma
from langchain.load import dumps, loads
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

query_rephrasing_template = """You are an AI language model assistant. Your task is to generate five 
different versions of the given user question based on the conversation to retrieve relevant documents from a vector 
database. By generating multiple perspectives on the user question, your goal is to help
the user overcome some of the limitations of the distance-based similarity search. 
Provide these alternative questions separated by newlines. 

Conversation:
{chat_history}

User question: {query}"""


class Retriever:
    def __init__(self, chromadb_path: str, embedding_function: EmbeddingFunction) -> None:
        self.embedding_function = embedding_function
        persistent_client = PersistentClient(chromadb_path)
        vectorstore = Chroma(client=persistent_client, collection_name='jina_embeddings', embedding_function=embedding_function)
        self.retriever = vectorstore.as_retriever()

        prompt_perspectives = ChatPromptTemplate.from_template(query_rephrasing_template)
        self.generate_queries_chain = (
                    prompt_perspectives 
                    | ChatOpenAI(temperature=0) 
                    | StrOutputParser() 
                    | (lambda x: x.split("\n"))
                )
        self.retrieval_chain = self.generate_queries_chain | self.retriever.map() | self._get_unique_union

    def _get_unique_union(self, documents: list[list]):
        """ Unique union of retrieved docs """
        # Flatten list of lists, and convert each Document to string
        flattened_docs = [dumps(doc) for sublist in documents for doc in sublist]
        # Get unique documents
        unique_docs = list(set(flattened_docs))
        # Return
        return [loads(doc) for doc in unique_docs]

    # def retrieve(self, query: str):
    #     return self.retrieval_chain.invoke({'': query})
