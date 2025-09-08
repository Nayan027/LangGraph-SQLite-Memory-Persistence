import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from backend import chatbot, retrieve_all_threads_from_DB              # importing out chatbot and funcn to get unique thread-ids from DB
import uuid



# ---------------------------- UTILITY FUNCTIONS -----------------------------------

def generate_thread_id():
    thread_id = uuid.uuid4()                            # Generates a random UUID.
    return thread_id



def reset_chat():
    thread_id = generate_thread_id()
    st.session_state["thread_id"] = thread_id          # Generates new thread id when chat is reset/new-chat
    add_thread(st.session_state["thread_id"])          # Adds current thread-id to list of "chat_threads"
    st.session_state["msg_history"] = []               # Empties message history for new chat as well as clears UI for new fresh chat



def add_thread(thread_id):                             # Adds thread-id to a list i.e. "chat_threads"
    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)

        session_number = len(st.session_state["chat_threads"])         
        st.session_state["thread_name_map"][thread_id] = f"session-{session_number}"   # Assign a name: "session-{index}", index starts from 1



def load_convo_history(thread_id):                    # Loads entire convo done for each unique thread-id
    state = chatbot.get_state(config={"configurable":{"thread_id": thread_id}})
    return state.values.get("messages", [])          # Checks if messages key exists in state values, returns empty list if not




# **************************************** Session Setup ******************************

if "msg_history" not in st.session_state:
    st.session_state["msg_history"] = []                            # list will contain multiple dicts



if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()


# Earlier when we used InMemorySaver(), we initiated an empty list and therefore everytime the program was restart chat-threads started with an empty list
# But with DB integration, memory is persistent even if application is refresed or turned on again after turning off.
# Thus we'll need to look into the DB for previous thread-ids to retrieve old conversations.

if "chat_threads" not in st.session_state:                         # list will consist of all unique thread-ids 
    st.session_state["chat_threads"] = retrieve_all_threads_from_DB()



                                   
if "thread_name_map" not in st.session_state:                      # Initialize mapping dict if not present
    st.session_state["thread_name_map"] = {}                     # no special use in this repo - since everything is stored on thread-id's basis here.



add_thread(st.session_state["thread_id"])




# ---------------------------- SIDEBAR - UI -----------------------------------

st.title("Your Personalized Chatbot")


st.sidebar.title("Chat History")


if st.sidebar.button("New Chat"):
    reset_chat()


st.sidebar.header("My Conversations")


for thread_id in st.session_state["chat_threads"][::-1]:                                  # loop to Display all thread-id-corresponding sessions in sidebar
    display_name = st.session_state["thread_name_map"].get(thread_id, str(thread_id))     # maps thread_id -> display name
    if st.sidebar.button(display_name):                                                   # Find the thread_id-session by clicking on display name
        
        st.session_state["thread_id"] = thread_id                         # current session is now the thread-id we clicked

        messages = load_convo_history(thread_id=thread_id)                # conversation history of that thread-id is stored in "messages"

# messages here have a different format w.r.t the msg_history where msgs are stored in form of dict with 2 keys - "role" & "content"
# this piece of code - transforms conversation history objects into a simple list of role–content dictionaries thus solving formatting & compatibility issues. 

        temp_messages = []                                  

        for msg in messages:                                # Iterates through each message i.e. HumanMessage & AIMessage
            if isinstance(msg, HumanMessage):               # if it’s a human message (HumanMessage) → assign role "user".
                role = "user"
            else:
                role = "assistant"                          # Otherwise (likely an AI message) → assign role "assistant"

            temp_messages.append({"role":role, "content":msg.content})

# At the end, temp_messages will look like this:
# [
#   {"role": "user", "content": "Hello, how are you?"},
#   {"role": "assistant", "content": "I’m good, thanks! How can I help you today?"}
# ]
# Exiting loop with "temp_messages" having same structure as "msg_history" i.e. list of dicts

        st.session_state["msg_history"] = temp_messages     # updating current session's msg history so it holds entire convo history of a particular thread-id when it's button is pressed. 





# **************************************** Main UI ************************************

# loading the conversation history

for msg in st.session_state['msg_history']:
    with st.chat_message(msg['role']):
        st.text(msg['content'])




user_input = st.chat_input("Ask your chatbot")

if user_input:                                                           # meaning when user hits "Enter" button.
    st.session_state["msg_history"].append({"role":"user",               # adding the user message to message_history
                                            "content":user_input})
    with st.chat_message("user"):                                        # opens a chat bubble for user test
        st.text(user_input)                                              # the actual text is filled in that chat-bubble





    CONFIG = {"configurable":{"thread_id": st.session_state["thread_id"]}}

                                                                       # This creates a chat message block labeled as from the assistant (the AI). 
    with st.chat_message("assistant"):                                 # Everything inside this block will be shown as the assistant's message in the UI.
        def ai_only_stream():                                          # Defines a generator function that will yield only the assistant's response text chunks as they come.
            for message_chunk, metadata in chatbot.stream(             # Calls the chatbot's .stream() method to send the user's input (user_input) as a HumanMessage.
                {"messages": [HumanMessage(content=user_input)]},      # This stream method returns an iterator of response chunks (partial messages) and metadata in streaming mode, 
                config=CONFIG,                                         # so the assistant's reply is streamed as it arrives rather than waiting for the full response.
                stream_mode="messages"
            ):
                if isinstance(message_chunk, AIMessage):               # Filters the streamed chunks so that only those from the assistant (type AIMessage) are yielded i.e.
                    yield message_chunk.content                        # i.e. (sent out from this generator), extracting just the text content.

        chatbot_response = st.write_stream(ai_only_stream())           # Passes the generator ai_only_stream() to st.write_stream()


    st.session_state['msg_history'].append({'role': 'assistant', 'content': chatbot_response})







# NOTE: st.write_stream() expects a  Generator/LangChain Stream/etc. 