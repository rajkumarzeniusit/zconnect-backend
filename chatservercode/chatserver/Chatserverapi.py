
from datetime import datetime
import json
import os
import uuid
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
import psycopg2
from psycopg2 import sql
from fastapi import FastAPI, HTTPException,UploadFile, File, Form, Query
from typing import List, Dict,Optional
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
import base64
from psycopg2.extras import RealDictCursor












app = FastAPI()
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://localhost:3004"
    # Add other origins if needed
]


# Add the CORS middleware to your FastAPI application
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)
load_dotenv()

#db config
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")


# Redis configuration
redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_db = os.getenv("REDIS_DB")
print("redis_host,redis_port,redis_db are",redis_host,redis_port,redis_db)

# Initialize Redis client
redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)

class Message(BaseModel):
    session_id: str
    sender: str
    timestamp: str
    content: str

class AgentMetadata(BaseModel):
    session_id: str

class Agent(BaseModel):
    metadata: AgentMetadata
    name: str
    phone: str
    userInput: str
    queues: str
    skills: str
    agentstate: Optional[str] = None
    isFirstMessage: bool
    timestamp: Optional[datetime] = None
    email:str
    agent_id:Optional[str] = None



# Database connection configuration
DB_CONFIG = {
    'dbname': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'host': DB_HOST,
    'port': DB_PORT
}



# Define the allowed origins
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002"
    # Add other origins if needed
]

# Add the CORS middleware to your FastAPI application
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)


def connect_to_db():
    """Connect to the PostgreSQL database and return the connection and cursor."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        return conn, cursor
    except Exception as error:
        print(f"Error connecting to database: {error}")
        return None, None

def fetch_agents():
    """Retrieve all agents data."""
    conn, cursor = connect_to_db()
    if conn is None or cursor is None:
        return None

    try:
        cursor.execute("SELECT * FROM public.agents")
        agents = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        agents = [dict(zip(columns, row)) for row in agents]
        return agents
    except Exception as error:
        print(f"Error fetching agents data: {error}")
        return None
    finally:
        cursor.close()
        conn.close()




def fetch_messages():
    """Retrieve all messages data from Redis."""
    try:
        # Connect to Redis
        r = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db)

        # Assuming 'conversation' is the key containing the JSON data
        conversation_key = 'conversation'

        # Get all session IDs stored under the 'conversation' key
        session_ids = r.hkeys(conversation_key)

        all_messages = []

        # Iterate through each session ID and retrieve conversation data
        for session_id in session_ids:
            # Retrieve the JSON string from Redis for the current session_id
            conversation_json = r.hget(conversation_key, session_id)
            
            if conversation_json:
                # Decode bytes to string (assuming Python 3)
                conversation_str = conversation_json.decode('utf-8')
                
                # Parse JSON string to Python object (list of dictionaries)
                conversation_data = json.loads(conversation_str)
                
                # Extend all_messages with conversation_data
                all_messages.extend(conversation_data)

        return all_messages

    except Exception as error:
        print(f"Error fetching messages data from Redis: {error}")
        return None




def get_last_message(session_id: str) -> dict:
    print("checking session_id", session_id)
    messages = fetch_messages()
    print("Fetched messages:", messages)
    
    # Debugging print statement to check session_id
    print("Session ID:", session_id)
    
    # Filter messages for the given session_id
    filtered_messages = [msg for msg in messages if msg["session_id"] == session_id]
    print("Filtered messages:", filtered_messages)
    
    if not filtered_messages:
        print("No messages found for the given session_id.")
        return None
    
    # Find the message with the latest timestamp
    last_message = max(filtered_messages, key=lambda msg: msg["timestamp"])
    print("Last message:", last_message)
    
    return last_message


@app.get("/last_message")
def get_last_session_message(session_id: str = Query(..., description="Session ID")):
    """API endpoint to retrieve the last message for a specific session ID."""
    print("session====>", session_id)
    last_message = get_last_message(session_id)
    if last_message is None:
        raise HTTPException(status_code=404, detail=f"No messages found for session ID '{session_id}'")
    return {"session_id": session_id, "last_message": last_message}



def fetch_accepted_chats():
    """Retrieve all accepted chats data."""
    conn, cursor = connect_to_db()
    if conn is None or cursor is None:
        return None

    try:
        cursor.execute("SELECT * FROM public.accepted_chats")
        accepted_chats = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        accepted_chats = [dict(zip(columns, row)) for row in accepted_chats]
        return accepted_chats
    except Exception as error:
        print(f"Error fetching accepted chats data: {error}")
        return None
    finally:
        cursor.close()
        conn.close()

@app.get("/agents", response_model=List[Dict])
def get_agents():
    """API endpoint to retrieve all agents data."""
    agents = fetch_agents()
    if agents is None:
        raise HTTPException(status_code=500, detail="Error fetching agents data")
    return agents




@app.get("/messages", response_model=List[Dict])
def get_messages():
    """API endpoint to retrieve all messages data."""
    try:
        messages = fetch_messages()
        if messages is None:
            raise HTTPException(status_code=500, detail="Error fetching messages data")
        return messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")



@app.get("/accepted_chats", response_model=List[Dict])
def get_accepted_chats():
    """API endpoint to retrieve all accepted chats data."""
    accepted_chats = fetch_accepted_chats()
    if accepted_chats is None:
        raise HTTPException(status_code=500, detail="Error fetching accepted chats data")
    return accepted_chats



@app.post("/messages", response_model=Dict)
def post_message(message: Message):
    """API endpoint to post a new message."""
    

    try:
       
        conversation_key = message.session_id
        previous_messages_json = redis_client.hget("conversation", conversation_key)
        
        # If there are previous messages, decode JSON and append the new message
        if previous_messages_json:
            previous_messages = json.loads(previous_messages_json)
            previous_messages.append(message.dict())
        else:
            previous_messages = [message.dict()]
        
        # Store updated messages back into Redis
        redis_client.hset("conversation", conversation_key, json.dumps(previous_messages))
        
        
        print("testing......",message.session_id, message.sender, message.timestamp, message.content)
        return {"message": "Message inserted successfully"}
    except Exception as error:
        print(f"Error inserting message: {error}")
        raise HTTPException(status_code=500, detail="Error inserting message")
    # finally:
    #     cursor.close()
    #     conn.close()


@app.put("/agents", response_model=Dict)
def update_agents(agents: List[Agent]):
    print("agents:::",agents)
    """API endpoint to update agent data."""
    conn, cursor = connect_to_db()
    if conn is None or cursor is None:
        raise HTTPException(status_code=500, detail="Error connecting to the database")

    try:
        for agent in agents:
            cursor.execute(
                """
                UPDATE public.agents
                SET name = %s, phone = %s, user_input = %s, queues = %s, skills = %s,  is_first_message = %s,email= %s,timestamp =%s,agent_id = %s
                WHERE session_id = %s
                """,
                (agent.name, agent.phone, agent.userInput, agent.queues, agent.skills,  agent.isFirstMessage,agent.email,agent.timestamp,agent.agent_id, agent.metadata.session_id)
            )
        conn.commit()
        return {"message": "Agents updated successfully"}
    except Exception as error:
        print(f"Error updating agents: {error}")
        raise HTTPException(status_code=500, detail="Error updating agents")
    finally:
        cursor.close()
        conn.close()


@app.post("/agents", response_model=Dict)
def post_agent(agent: Agent):
    """API endpoint to insert or update a new agent."""
    print("agent.........", agent)
    conn, cursor = connect_to_db()
    if conn is None or cursor is None:
        raise HTTPException(status_code=500, detail="Error connecting to the database")

    try:
        cursor.execute(
            """
            INSERT INTO public.agents (session_id, name, phone, user_input, queues, skills, is_first_message, email, timestamp, agent_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id) DO UPDATE
            SET name = EXCLUDED.name,
                phone = EXCLUDED.phone,
                user_input = EXCLUDED.user_input,
                queues = EXCLUDED.queues,
                skills = EXCLUDED.skills,
                is_first_message = EXCLUDED.is_first_message,
                email = EXCLUDED.email,
                timestamp = EXCLUDED.timestamp,
                agent_id = EXCLUDED.agent_id
            """,
            (agent.metadata.session_id, agent.name, agent.phone, agent.userInput, agent.queues, agent.skills, agent.isFirstMessage, agent.email, agent.timestamp, agent.agent_id)
        )
        conn.commit()
        return {"message": "Agent inserted/updated successfully"}
    except psycopg2.IntegrityError as e:
        if 'duplicate key value violates unique constraint "agents_session_id_key"' in str(e):
            # Handle the duplicate key error (e.g., log it, return an error response)
            print(f"Duplicate session_id found: {agent.metadata.session_id}")
            raise HTTPException(status_code=400, detail="Duplicate session_id")
        else:
            # Handle other IntegrityError cases
            print(f"IntegrityError occurred: {e}")
            raise HTTPException(status_code=500, detail="Error inserting/updating agent")
    except Exception as error:
        print(f"Error inserting/updating agent: {error}")
        raise HTTPException(status_code=500, detail="Error inserting/updating agent")
    finally:
        cursor.close()
        conn.close()













class AcceptedChat(BaseModel):
    session_id: str
    accepted: bool

@app.post("/accepted_chats", response_model=Dict)
def post_accepted_chat(chat: AcceptedChat):
    """API endpoint to post an accepted chat."""
    conn, cursor = connect_to_db()
    if conn is None or cursor is None:
        raise HTTPException(status_code=500, detail="Error connecting to the database")

    try:
        cursor.execute(
            """
            INSERT INTO public.accepted_chats (session_id, accepted)
            VALUES (%s, %s)
            ON CONFLICT (session_id) DO UPDATE SET accepted = EXCLUDED.accepted
            """,
            (chat.session_id, chat.accepted)
        )
        conn.commit()
        return {"message": "Accepted chat status inserted/updated successfully"}
    except Exception as error:
        print(f"Error inserting/updating accepted chat: {error}")
        raise HTTPException(status_code=500, detail="Error inserting/updating accepted chat")
    finally:
        cursor.close()
        conn.close()



@app.put("/agents/{session_id}", response_model=Dict)
def update_agent(session_id: str, userInput: str, timestamp: datetime):
    """API endpoint to update agent userInput for a specific session_id."""
    conn, cursor = connect_to_db()
    if conn is None or cursor is None:
        raise HTTPException(status_code=500, detail="Error connecting to the database")

    try:
        cursor.execute(
            """
            UPDATE public.agents
            SET user_input = %s,
                timestamp = %s
            
            WHERE session_id = %s
            """,
            (userInput,timestamp, session_id)
        )
        conn.commit()
        return {"message": "Agent updated successfully"}
    except Exception as error:
        print(f"Error updating agent: {error}")
        raise HTTPException(status_code=500, detail="Error updating agent")
    finally:
        cursor.close()
        conn.close()



class SessionID(BaseModel):
    session_id: str
    agent_id:str
    agentName:str



@app.post("/remove-session/")
async def remove_session(session: SessionID):
    session_id_to_remove = session.session_id
    print("remove key is",session_id_to_remove)
    print("after function",session_id_to_remove)

    # Fetch data from Redis
    previous_messages = redis_client.hget("conversation", session_id_to_remove)

    if not previous_messages:
        raise HTTPException(status_code=404, detail="Session not found")

    # Print the key and value before deletion
    print(f"Key to be deleted: conversation:{session_id_to_remove}")
    print(f"Value: {previous_messages.decode('utf-8')}")  # Decode bytes to string for printing

    conn, cursor = connect_to_db()
    
    if conn:
        try:
            cursor.execute(
                'SELECT phone, name, email ,queues FROM agents WHERE session_id = %s',
                (session_id_to_remove,)
            )
            agent_info = cursor.fetchone()
            if agent_info:
                phone, name, email,queues = agent_info
                agent_name = session.agentName
                user_name = name
                queues=queues
                print("agentID:", session.agent_id)
                print("agentName:", agent_name)
                print(f"user Name: {user_name}, Phone Number: {phone}, Email: {email}, Queue : {queues}")
            else:
                print(f"No agent found with session ID {session_id_to_remove}.")
                agent_name = "Unknown"
                user_name = "Unknown"
                phone = "Unknown"
                email = "Unknown"

            # Deserialize JSON, modify the sender fields, and serialize it back
            messages = json.loads(previous_messages.decode('utf-8'))
            print("messages :::",messages)
            for message in messages:
                if message['sender'] == 'agent':
                    message['sender'] = f"{user_name}"
                    message['recevier'] = f"{agent_name}"
                    del message['session_id']
                elif message['sender'] == 'user':
                    message['sender'] = f"{agent_name}"
                    message['recevier'] = f"{user_name}"
                    del message['session_id']
                
            modified_messages = json.dumps(messages)
                        
            # Insert data into PostgreSQL
            cursor.execute(
                '''
                INSERT INTO conversations (session_id, username, phone, queues, email, agentname, agent_id, messages)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (session_id_to_remove, user_name, phone, queues, email, agent_name, session.agent_id, modified_messages)
            )
            conn.commit()
            print(f"Session {session_id_to_remove} inserted into PostgreSQL.")
            
            # Delete session from agents table
            cursor.execute(
                'DELETE FROM agents WHERE session_id = %s',
                (session_id_to_remove,)
            )
            conn.commit()
            print(f"Session {session_id_to_remove} deleted from agents table.")
            
        except Exception as e:
            print(f"Error inserting into PostgreSQL: {e}")
        finally:
            # Close the database connection
            cursor.close()
            conn.close()
    else:
        print("Failed to connect to PostgreSQL.")

    # Remove the session from Redis
    redis_client.hdel("conversation", session_id_to_remove)
    
    return {"message": f"Session {session_id_to_remove} removed"}

@app.post("/attachments")
async def upload_attachment(
    session_id: str = Form(...),
    reference_id: str = Form(...),
    extracted_file: str = Form(...)
):
    conn = None
    cur = None
    try:
        print(f"Received upload request with session_id: {session_id} and reference_id: {reference_id}")
        
        # Parse the JSON string
        file_info = json.loads(extracted_file)
        file_data = base64.b64decode(file_info['data'])  # Decode the base64-encoded file data
        file_name = file_info.get('name')
        file_type = file_info.get('type')

        print(f"File data read successfully: {len(file_data)} bytes")
        print(f"File name: {file_name}, File type: {file_type}")

        # Connect to the database
        conn, cur = connect_to_db()
        if conn is None or cur is None:
            print("Failed to connect to the database.")
            return JSONResponse(status_code=500, content={"message": "Could not connect to the database"})

        print("Connected to database")
        with conn:
            print("Inserting attachment into database")
            cur.execute(
                """
                INSERT INTO attachments (reference_id, attachment_data, file_name, file_type)
                VALUES (%s, %s, %s, %s)
                """,
                (reference_id, psycopg2.Binary(file_data), file_name, file_type)
            )
            conn.commit()
            print("Attachment inserted successfully")

        return JSONResponse(status_code=200, content={"message": "Attachment saved successfully", "reference_id": reference_id})

    except Exception as e:
        print(f"Error occurred: {e}")
        return JSONResponse(status_code=500, content={"message": "An error occurred while saving the attachment", "error": str(e)})

    finally:
        if cur:
            cur.close()
            print("Cursor closed")
        if conn:
            conn.close()
            print("Database connection closed")

class AttachmentResponse(BaseModel):
    reference_id: str
    attachment_data: str
    file_name: str
    file_type: str

@app.get("/attachments/{reference_id}", response_model=AttachmentResponse)
def get_attachment(reference_id: str):
    print(f"Received request for reference_id: {reference_id}")
    conn, cursor = connect_to_db()
    if conn is None or cursor is None:
        print("Database connection error")
        raise HTTPException(status_code=500, detail="Database connection error")
    try:
        print("Executing query to fetch attachment...")
        cursor.execute(
            "SELECT reference_id, attachment_data, file_name, file_type FROM attachments WHERE reference_id = %s", 
            (reference_id,)
        )
        attachment = cursor.fetchone()
        print(f"Query executed. Result: {attachment}")
    except Exception as error:
        print(f"Error executing query: {error}")
        raise HTTPException(status_code=500, detail="Query execution error")
    finally:
        conn.close()
        print("Database connection closed.")

    if attachment is None:
        print("Attachment not found")
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Create a dictionary from the tuple and encode the attachment_data in base64
    attachment_dict = {
        'reference_id': attachment[0],
        'attachment_data': base64.b64encode(attachment[1]).decode('utf-8'),
        'file_name': attachment[2],
        'file_type': attachment[3]
    }
    print(f"Converted attachment data to base64: {attachment_dict['attachment_data']}")

    return attachment_dict




#####################################################################################
##keyupdate.py


class AgentState(BaseModel):
    agent_id: str
    # queue: str  # Comma-separated string
    # skills: str  # Comma-separated string
    agentState: str
    dateTime: str
    # maxConcurrentInteraction:int
    
    
class Metadata(BaseModel):
    session_id: str

class DataItem(BaseModel):
    metadata: Metadata
    name: str
    phone: str
    userInput: str
    queues: str
    skills: str
    isFirstMessage: bool
    rejectedMessage:bool
    agent_id:str
    email:str
    emailtranscript:bool
    timestamp:str



@app.post("/log_state_change")
async def log_state_change(agent_state: AgentState):
    try:
        # Print the agent state data
        print("agent_state",agent_state)
        print(f"Agent ID: {agent_state.agent_id}")
        # print(f"Agent queues: {agent_state.queue}")
        # print(f"Agent skills: {agent_state.skills}")
        print(f"Agent state changed to: {agent_state.agentState}")
        print(f"Time: {agent_state.dateTime}")
        
        redis_client.hset('agent:' + str(agent_state.agent_id), 'agent_id', agent_state.agent_id)
        # redis_client.hset('agent:' + str(agent_state.id), 'queue', agent_state.queue)
        # redis_client.hset('agent:' + str(agent_state.id), 'skills', agent_state.skills)
        redis_client.hset('agent:' + str(agent_state.agent_id), 'current_state', agent_state.agentState)
        redis_client.hset('agent:' + str(agent_state.agent_id), 'last_state_change', agent_state.dateTime)
        # redis_client.hset('agent:' + str(agent_state.id), 'maxConcurrentInteraction', agent_state.maxConcurrentInteraction)
        
        
       

        return {"message": "Agent state change logged and stored in Redis hash"}

    except redis.RedisError as e:
        raise HTTPException(status_code=500, detail=f"Redis error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    
    
    
    



@app.get("/fetch_redis_agents")
async def get_all_agents():
    try:
        # Retrieve all keys that match the pattern 'agent:*'
        keys = redis_client.keys('agent:*')
        
        if not keys:
            raise HTTPException(status_code=404, detail="No agents found")
        
        agents = {}
        for key in keys:
            # Use HGETALL to retrieve all fields and values of the hash
            agent_data = redis_client.hgetall(key)
            agents[key] = agent_data
        
        return agents
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/rejected_message")
async def rejected_message(item: DataItem):
    print("Received data:", item.dict())
    r = redis.Redis(host=redis_host, port=redis_port, db=redis_db)

    # Store each message using session_id as the key with a delay of 10 seconds
    session_id = item.metadata.session_id  # Accessing 'metadata' using dot notation
    r.hset("agent_rejected_message", session_id, json.dumps(item.dict()))
    print(f"Message for session_id {session_id} stored in Redis.")
   
    return {"message": "Data received successfully"}





############################################
##details.py



class AgentList(BaseModel):
    id: int
    agent_id: str
    queues: List[str]
    skills: List[str]
    max_chat_concurrent_interactions: int
    max_call_concurrent_interactions: int
    max_email_concurrent_interactions: int

# agents = [
#     {
#         "id": 1,
#         "agent_id": "bharat123@gmail.com",
#         "queues": ["technicalsupportqueue@1","customer_servicequeue@123", "business_queue@1"],
#         "skills": ["networking_skill","troubleshooting_skill", "communication_skill"],
#         "max_chat_concurrent_interactions": 3,
#         "max_call_concurrent_interactions": 1,
#         "max_email_concurrent_interactions": 1
#     },
#     {
#         "id": 2,
#         "agent_id": "Gopi@gamil.com",
#         "queues": ["Business_supportqueue@1"],
#         "skills": ["Business_supportskill@1"],
#         "max_chat_concurrent_interactions": 1,
#         "max_call_concurrent_interactions": 3,
#         "max_email_concurrent_interactions": 1
#     },
#     {
#         "id": 3,
#         "agent_id": "suresh@gmail.com",
#         "queues": ["technicalsupportqueue@1", "customer_servicequeue@123", "business_queue@1"],
#         "skills": ["networking_skill", "troubleshooting_skill", "communication_skill"],
#         "max_chat_concurrent_interactions": 3,
#         "max_call_concurrent_interactions": 1,
#         "max_email_concurrent_interactions": 1
#     },{
#         "id": 4,
#         "agent_id": "ashokreddy@gmail.com",
#         "queues": ["technicalsupportqueue@1"],
#         "skills": ["networking_skill"],
#         "max_chat_concurrent_interactions": 3,
#         "max_call_concurrent_interactions": 1,
#         "max_email_concurrent_interactions": 1
#     }
# ]

# @app.get("/api/agent_queues", response_model=List[AgentList])
# def get_agents_queueus():
#     return agents

# @app.post("/api/agent_queues", response_model=AgentList)
# def add_agent(agent: AgentList):
#     for existing_agent in agents:
#         if existing_agent["id"] == agent.id:
#             raise HTTPException(status_code=400, detail="Agent with this ID already exists")
#     agents.append(agent.dict())
#     return agent







##########chatphrases

class Phrase(BaseModel):
    phrase_id: int
    queue_id: int
    queue_name: str
    shortcut: str
    phrase_text: List[str]

phrases = [
    Phrase(
        phrase_id=1,
        queue_id=25,
        queue_name="technicalsupportqueue@1",
        shortcut="greeting",
        phrase_text=[
            "Hello!", "Hi there!", "Greetings!", "Welcome!", "Good day!",
            "Hello, how can I assist you?", "Hi, what can I do for you?",
            "Hey, how's it going?", "Hi, how may I help you?",
            "Hello, what can I help you with today?"
        ]
    ),
    Phrase(
        phrase_id=2,
        queue_id=27,
        queue_name="customer_servicequeue@123",
        shortcut="farewell",
        phrase_text=[
            "Goodbye!", "See you later!", "Take care!", "Bye!", "Have a great day!",
            "Farewell!", "See you soon!", "Catch you later!", "Goodbye, take care!",
            "Have a nice day!"
        ]
    ),
    Phrase(
        phrase_id=3,
        queue_id=28,
        queue_name="business_queue@1",
        shortcut="thanks",
        phrase_text=[
            "Thank you!", "Thanks!", "I appreciate it!", "Many thanks!", "Thank you so much!",
            "Thanks a lot!", "Thank you, I appreciate it!", "Thanks for your help!",
            "Much appreciated!", "Thank you very much!"
        ]
    ),
    Phrase(
        phrase_id=4,
        queue_id=29,
        queue_name="Business_supportqueue@1",
        shortcut="thanks",
        phrase_text=[
            "Thank you!", "Thanks!", "I appreciate it!", "Many thanks!", "Thank you so much!",
            "Thanks a lot!", "Thank you, I appreciate it!", "Thanks for your help!",
            "Much appreciated!", "Thank you very much!"
        ]
    )
]

@app.get("/api/chat_phrases/queue", response_model=List[Phrase])
async def get_all_phrases():
    return phrases

@app.get("/api/chat_phrases/queue/{queue_name}", response_model=List[Phrase])
async def get_phrases_by_queue(queue_name: str):
    filtered_phrases = [phrase for phrase in phrases if phrase.queue_name == queue_name]
    if not filtered_phrases:
        raise HTTPException(status_code=404, detail="Queue not found")
    return filtered_phrases







if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
    
    
    
    
    
    
