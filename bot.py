from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from dotenv import load_dotenv
import os
load_dotenv()
api_key = os.getenv("API_KEY")

#Clase de estado del chatbot
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Definicion del modelo LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5, api_key=api_key)

# Funcion principal del chatbot
def chatbot(state: State) -> State:
    """
    Función principal del chatbot que procesa los mensajes y genera una respuesta.
    
    Args:
        state (State): Estado actual del chatbot con mensajes.
    
    Returns:
        State: Nuevo estado con la respuesta generada.
    """
    response = llm.invoke(state['messages'])
    state['messages'].append(response)
    return state

# Construcción del grafo de estados para el chatbot
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

# Persistencia de memoria para el chatbot
memory = MemorySaver()

# Compilación del grafo con el checkpointer de memoria
graph = graph_builder.compile(checkpointer=memory)

def chat_with_memory(user_input, thread_id="001"):
    """
    Función para interactuar con el chatbot, guardando el estado en memoria.
    
    Args:
        user_input (str): Entrada del usuario.
        thread_id (str): Identificador del hilo de conversación.
    
    Returns:
        str: Respuesta del chatbot.
    """
    config = {"configurable": {"thread_id": thread_id}}

    result = graph.invoke(
        {"messages": [("user", user_input)]},
        config=config,
    )
    
    return result['messages'][-1].content


while True:
    user_input = input("Mensaje: ")
    if user_input.lower() == "exit":
        break
    response = chat_with_memory(user_input)
    print(f"Chatbot: {response}")
