from database import SessionLocal
from database.db_saver import get_memory_saver
from database.models import Message
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain.chat_models import ChatOpenAI
from typing import TypedDict, List
from typing_extensions import Annotated
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("API_KEY")

# Definición del estado
def append_messages(a: list, b: list) -> list:
    return a + b

class State(TypedDict):
    messages: Annotated[List, append_messages]

class ChatBot:
    def __init__(self, model="gpt-4o-mini", temperature=0.5, api_key=API_KEY, memory=get_memory_saver()):
        if memory is None:
            memory = MemorySaver()
            memory.setup()

        self.memory = memory
        self.llm = ChatOpenAI(model=model, temperature=temperature, api_key=api_key, streaming=False)
        self.graph = self._build_graph()
        self.db_session = SessionLocal()  # sesión SQLite para guardar mensajes

    # Nodo principal del grafo
    def _chatbot_node(self, state: State) -> State:
        # El último mensaje del user
        user_message = state['messages'][-1][1]
        # Generar respuesta
        response = self.llm.invoke(state['messages'])
        state['messages'].append(response)

        # Guardar en la tabla messages
        thread_id = state.get('thread_id', "001")  # default si no existe
        # Guardar user
        user_msg = Message(thread_id=thread_id, role="user", content=user_message)
        self.db_session.add(user_msg)
        # Guardar assistant
        bot_msg = Message(thread_id=thread_id, role="assistant", content=response.content)
        self.db_session.add(bot_msg)
        self.db_session.commit()

        return state

    # Construcción del grafo
    def _build_graph(self):
        graph_builder = StateGraph(State)
        graph_builder.add_node("chatbot", self._chatbot_node)
        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_edge("chatbot", END)
        return graph_builder.compile(checkpointer=self.memory)

    # Método público para enviar mensaje
    def chat(self, user_input: str, thread_id: str) -> str:
        config = {"configurable": {"thread_id": thread_id}}
        state = {"messages": [("user", user_input)], "thread_id": thread_id}
        result = self.graph.invoke(state, config=config)
        return result['messages'][-1].content

    # Obtener historial desde DB
    def get_history(self, thread_id: str):
        messages = (
            self.db_session.query(Message)
            .filter_by(thread_id=thread_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        return [{"role": m.role, "content": m.content} for m in messages]
