from database import SessionLocal
from database.db_saver import get_memory_saver
from database.models import Message
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from typing import TypedDict, List
from typing_extensions import Annotated
from services.product_repository import ProductRepository
from tools.database_tools import get_product, create_product
from dotenv import load_dotenv
import os
import re

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
        self.tools = [get_product, create_product]
        self.llm = ChatOpenAI(model=model, temperature=temperature, api_key=api_key, streaming=False, max_tokens=250)
        self.agent = initialize_agent(tools=self.tools, llm=self.llm, agent=AgentType.OPENAI_FUNCTIONS, verbose=True)
        self.graph = self._build_graph()
        self.db_session = SessionLocal()  # sesión SQLite para guardar mensajes
        self.repo = ProductRepository()

 # --- Función para detectar si se debe usar RAG ---
    def _is_product_query(self, text: str) -> bool:
        keywords = [
            "remera", "pantalon", "jean", "zapatilla", "buzo",
            "camisa", "sweater", "talle", "precio", "stock", "color", "marca"
        ]
        pattern = r"\b(" + "|".join(keywords) + r")\b"
        return bool(re.search(pattern, text.lower()))
    
    # Nodo principal del grafo
    def _chatbot_node(self, state: State) -> State:
        # El último mensaje del user
        user_message = state['messages'][-1][1]

        context_text = ""
        # --- Integración RAG ---
        if self._is_product_query(user_message):
            results = self.repo.search_products(user_message)
            if results:
                bullets = []
                for r in results:
                    meta = r["metadata"]
                    text = r["text"]
                    bullet = f"- {meta.get('categoria','Producto')} {meta.get('descripcion','')} {meta.get('color','')} {meta.get('talle','')}, ${meta.get('precio','0')}, stock {meta.get('cantidad','0')}"
                    bullets.append(bullet)
                context_text = "Contexto de productos relevantes:\n" + "\n".join(bullets)

        # --- Construir input para LLM ---
        llm_input = user_message
        if context_text:
            llm_input = f"{context_text}\n\nUsuario pregunta: {user_message}"

        # Generar respuesta
        response = self.agent.invoke({"input": llm_input})

        content = (
            response["output"]
            if isinstance(response, dict) and "output" in response
            else str(response)
        )

        state['messages'].append(("assistant", content))

        # Guardar en la tabla messages
        thread_id = state.get('thread_id', "001")  # default si no existe
        # Guardar user
        self.db_session.add_all([
            Message(thread_id=thread_id, role="user", content=user_message),
            Message(thread_id=thread_id, role="assistant", content=content),
        ])
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
        return result['messages'][-1][1]
    # Obtener historial desde DB
    def get_history(self, thread_id: str):
        messages = (
            self.db_session.query(Message)
            .filter_by(thread_id=thread_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        return [{"role": m.role, "content": m.content} for m in messages]
