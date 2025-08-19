from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from dotenv import load_dotenv
import sqlite3
import os

load_dotenv()
api_key = os.getenv("API_KEY")

class State(TypedDict):
    messages: Annotated[list, add_messages]

class ChatBot:
    def __init__(self, db_path="bot_memory.sqlite", model="gpt-4o-mini", temperature=0.5, api_key=None):
        # Conexión SQLite
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.memory = SqliteSaver(self.conn)

        # LLM síncrono, invoke únicamente
        self.llm = ChatOpenAI(model=model, temperature=temperature, api_key=api_key, streaming=False)

        # Construccion del grafo
        self.graph = self._build_graph()

    # Nodo principal del grafo
    def _chatbot_node(self, state: State) -> State:
        response = self.llm.invoke(state['messages'])
        state['messages'].append(response)
        return state

    # Construccion del grafo
    def _build_graph(self):
        graph_builder = StateGraph(State)
        graph_builder.add_node("chatbot", self._chatbot_node)
        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_edge("chatbot", END)
        return graph_builder.compile(checkpointer=self.memory)

    def chat(self, user_input: str, thread_id="001") -> str:
        config = {"configurable": {"thread_id": thread_id}}
        result = self.graph.invoke({"messages": [("user", user_input)]}, config=config)
        return result['messages'][-1].content

    def get_history(self, thread_id="001"):
        checkpoint = self.memory.get(thread_id)
        if checkpoint and "messages" in checkpoint:
            return [(msg.type, msg.content) for msg in checkpoint["messages"]]
        return []
