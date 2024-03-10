import os
import requests
import streamlit as st
import json
from chatbot import ChatBot

CHATBOT_URL = os.getenv(
    "CHATBOT_URL", "http://localhost:8000/pew-research-rag-agent"
)

chatbot = ChatBot()

with st.sidebar:
    st.header("About")
    st.markdown(
        """
        This chatbot interfaces with a
        [LangChain](https://python.langchain.com/docs/get_started/introduction)
        agent designed to answer questions about the hospitals, patients,
        visits, physicians, and insurance payers in  a fake hospital system.
        The agent uses retrieval-augment generation (RAG) over both
        structured and unstructured data that has been synthetically generated.
        """
    )


st.title("Pew Research RAG Chatbot")
st.info(
    """Ask me questions about patients, visits, insurance payers, hospitals,
    physicians, reviews, and wait times!"""
)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if "output" in message.keys():
            st.markdown(message["output"])

        if "explanation" in message.keys():
            with st.status("Docs behind the answer", state="complete"):
                st.info(message["explanation"])

if prompt := st.chat_input("What do you want to know?"):
    st.chat_message("user").markdown(prompt)

    st.session_state.messages.append({"role": "user", "output": prompt})

    data = {"text": prompt}

    with st.spinner("Searching for an answer..."):
        # response = requests.post(CHATBOT_URL, json=data)

        # if response.status_code == 200:
        #     output_text = response.json()["response"]
        #     explanation = json.dumps(response.json()["docs"], indent=2).replace('\n', '\n\n')

        # else:
        #     output_text = """An error occurred while processing your message.
        #     Please try again or rephrase your message."""
        #     explanation = output_text

        response, docs = chatbot.get_response(user_input=prompt)
        output_text = response.content
        explanation = json.dumps(docs, indent=2).replace('\n', '\n\n')

    st.chat_message("assistant").markdown(output_text)
    st.status("Docs behind the answer", state="complete").info(explanation)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "output": output_text,
            "explanation": explanation
        }
    )
