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
from utils.product_query_parser import parse_user_query
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
        self.db_session = SessionLocal()
        self.repo = ProductRepository()

    def _is_product_query(self, text: str) -> bool:
        """Detecta si la consulta es sobre productos usando keywords mejoradas"""
        keywords = [
            # Productos
            "remera", "pantalon", "jean", "zapatilla", "buzo", "camisa", "sweater", 
            "campera", "vestido", "short", "pollera", "medias", "ropa interior",
            # Atributos
            "talle", "precio", "stock", "color", "marca", "categoria", "material",
            # Acciones
            "busco", "tenés", "tenes", "hay", "mostrame", "quiero", "necesito",
            "entre", "hasta", "desde", "máximo", "minimo", "barato", "caro"
        ]
        pattern = r"\b(" + "|".join(keywords) + r")\b"
        return bool(re.search(pattern, text.lower()))

    def _handle_product_query(self, user_message: str) -> str:
        """
        Maneja consultas de productos usando el parser y RAG service
        """
        try:
            # 1. Parsear la consulta del usuario para extraer filtros estructurados #DEBUG (se puede eliminar luego)
            parsed_query = parse_user_query(user_message)
            print(f"DEBUG - Consulta parseada: {parsed_query}")
            
            # 2. Buscar productos usando el repository (que usa RAG internamente)
            search_results = self.repo.search_products(user_message)
            print(f"DEBUG - Resultados encontrados: {len(search_results)}")
            
            # 3. Construir contexto para el LLM
            if search_results:
                context_parts = []
                context_parts.append("🛍️ Productos encontrados:")
                
                for i, result in enumerate(search_results[:5], 1):  # Limitar a 5 resultados
                    meta = result["metadata"]
                    score = result["score"]
                    
                    product_info = f"""
                    {i}. {meta.get('descripcion', 'Producto sin descripción')}
                    - Categoría: {meta.get('categoria', 'N/A')}
                    - Color: {meta.get('color', 'N/A')}
                    - Talle: {meta.get('talle', 'N/A')}
                    - Marca: {meta.get('marca', 'N/A')}
                    - Precio: ${meta.get('precio', '0')}
                    - Stock: {meta.get('cantidad', '0')} unidades
                    - Relevancia: {score:.2f}
                    """
                    context_parts.append(product_info)
                
                context_text = "\n".join(context_parts)
                
                # Crear prompt enriquecido para el LLM
                enhanced_prompt = f"""
                {context_text}

                Pregunta del usuario: {user_message}

                Instrucciones: 
                - Responde de manera natural y amigable
                - Menciona los productos más relevantes
                - Si hay filtros específicos (talle, color, precio), enfócate en esos
                - Si no hay productos que coincidan exactamente, sugiere alternativas
                - Sé conciso pero informativo
                """
                
                # Generar respuesta usando el agent con contexto
                response = ChatOpenAI(
                    model=self.llm.model_name,
                    temperature=self.llm.temperature,
                    api_key=API_KEY,
                ).invoke(enhanced_prompt)
                
            else:
                # No se encontraron productos
                no_results_prompt = f"""
                El usuario preguntó: {user_message}

                No se encontraron productos que coincidan con la búsqueda.

                Responde de manera amigable explicando que no hay productos disponibles con esas características 
                y sugiere consultar por otros productos o modificar los criterios de búsqueda.
                """
                response = self.agent.invoke({"input": no_results_prompt})
            
            return (
                response["output"] 
                if isinstance(response, dict) and "output" in response 
                else str(response)
            )
            
        except Exception as e:
            print(f"ERROR en _handle_product_query: {e}")
            # Fallback: respuesta genérica
            fallback_prompt = f"""
            El usuario preguntó sobre productos: {user_message}
            Hubo un error técnico. Responde de manera amigable pidiendo que reformule la pregunta.
            """
            response = self.agent.invoke({"input": fallback_prompt})
            return (
                response["output"] 
                if isinstance(response, dict) and "output" in response 
                else str(response)
            )

    def _chatbot_node(self, state: State) -> State:
        """Nodo principal del grafo con toma de decisiones mejorada"""
        print("Estado actual del chat:", state)  # DEBUG
        
        # El último mensaje del user
        user_message = state['messages'][-1][1]
        
        # TOMA DE DECISIÓN: ¿Es una consulta de productos?
        if self._is_product_query(user_message):
            print("DEBUG - Detectada consulta de productos, usando RAG + Parser")
            content = self._handle_product_query(user_message)
        else:
            print("DEBUG - Consulta general, usando agent normal")
            # Para consultas generales, usar el agent sin contexto adicional
            response = self.agent.invoke({"input": user_message})
            content = (
                response["output"]
                if isinstance(response, dict) and "output" in response
                else str(response)
            )

        # Agregar respuesta al estado
        state['messages'].append(("assistant", content))

        # Guardar en la base de datos
        thread_id = state.get('thread_id', "001")
        self.db_session.add_all([
            Message(thread_id=thread_id, role="user", content=user_message),
            Message(thread_id=thread_id, role="assistant", content=content),
        ])
        self.db_session.commit()

        return state

    def _build_graph(self):
        """Construcción del grafo"""
        graph_builder = StateGraph(State)
        graph_builder.add_node("chatbot", self._chatbot_node)
        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_edge("chatbot", END)
        return graph_builder.compile(checkpointer=self.memory)

    def chat(self, user_input: str, thread_id: str) -> str:
        """Método público para enviar mensaje"""
        config = {"configurable": {"thread_id": thread_id}}
        state = {"messages": [("user", user_input)], "thread_id": thread_id}
        result = self.graph.invoke(state, config=config)
        return result['messages'][-1][1]

    def get_history(self, thread_id: str):
        """Obtener historial desde DB"""
        messages = (
            self.db_session.query(Message)
            .filter_by(thread_id=thread_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        return [{"role": m.role, "content": m.content} for m in messages]
