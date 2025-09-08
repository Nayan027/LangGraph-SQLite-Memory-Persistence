from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from typing import TypedDict, Annotated

from langgraph.checkpoint.sqlite import SqliteSaver        # DataBase Memory saver
import sqlite3                                             # connector: creates a database Connection object used to interact with an SQLite database file or an in‑memory DB

from langchain_core.messages import BaseMessage
from langchain_perplexity import ChatPerplexity

from dotenv import load_dotenv
load_dotenv()



model = ChatPerplexity()                                             # LLModel instance 



connection_object = sqlite3.connect(database="chatbot_database", check_same_thread=False)     # creates a DB if it doesnt already exist.

checkpointer = SqliteSaver(conn=connection_object)                                         # Memory saver object




class ChatState(TypedDict):                                          # Defining state
    messages: Annotated[list[BaseMessage], add_messages]


def chat_node(state:ChatState):                                      # Define the only task
    messages = state['messages']

    llm_response = model.invoke(messages)

    return {"messages": llm_response}




graph = StateGraph(ChatState)           # Graph - workflow

graph.add_node("chat_node", chat_node)

graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

chatbot = graph.compile(checkpointer=checkpointer)



def retrieve_all_threads_from_DB():
    all_threads = set()                                       # A set to store unique thread-id's since one thread-id could have multiple checkpoints.    
                                                              # checkpointer.list() will consist many data one of which is "thread-id"
    for checkpoints in checkpointer.list(None):               # None - signifies no specific thread-id instead look for all
        all_threads.add(checkpoints.config["configurable"]["thread_id"])           # add thread-ids to the set and since it's a set it will have an element no more tan once. 
    return list(all_threads)                                  # convert into list - to use append operations.