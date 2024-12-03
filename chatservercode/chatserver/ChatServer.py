
import asyncio
import json

import os
from typing import Any, Dict, List
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
import httpx
import psycopg2
import redis
from websockets import connect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import requests
from datetime import datetime
from psycopg2.extras import RealDictCursor



app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change "*" to a specific domain for better security
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)
active_sessions = {}
agent_sessions = {}
map_agent_user={}

load_dotenv()
chatqueue=os.getenv("API_chatqueue")
redisagents=os.getenv("API_FETCH_REDIS_AGENTS")
skills=os.getenv("API_SKILLS")

redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_db = os.getenv("REDIS_DB")
print("redis_host,redis_port,redis_db are",redis_host,redis_port,redis_db)
r = redis.Redis(host=redis_host, port=redis_port, db=redis_db)


rejected_message = None

fetch_detail_cache = None


print("sessions in the active session in",agent_sessions,active_sessions)

@app.websocket("/ws/agent")
async def websocket_endpoint_agent(websocket: WebSocket):
    await websocket.accept()
    session_id = None
    print("sessions in the active session in ws/agent:",agent_sessions,active_sessions)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)  # Parse the JSON message
            print("message for agnet from user",message)
            
            # Handle typing and stop_typing events
            if 'event' in message:
                if message['event'] == 'typing':
                    print("typing event received here ...", message)
                    session_id = message.get('session_id', '')
                    print("checking session id",session_id)
                    if session_id in map_agent_user:
                        agent_id = map_agent_user[session_id]
                        if agent_id in agent_sessions:
                            for connection_id, agent_websocket in agent_sessions.items():
                                if str(connection_id) == agent_id:
                                    message["agent_id"] = agent_id
                                    await agent_websocket.send_text(json.dumps(message))
                    else:
                        print("typing session not present .....")
                    continue
                elif message['event'] == 'stop_typing':
                    print("stop typing event received here ...", message)
                    session_id = message.get('session_id', '')
                    if session_id in map_agent_user:
                        agent_id = map_agent_user[session_id]
                        if agent_id in agent_sessions:
                            for connection_id, agent_websocket in agent_sessions.items():
                                if str(connection_id) == agent_id:
                                    message["agent_id"] = agent_id
                                    await agent_websocket.send_text(json.dumps(message))
                    else:
                        print("stop_typing session not present .....")
                    continue
            
            # Handle other messages
            if 'event' not in message:
                metadata = message.get('metadata', {})
                session_id = metadata.get('session_id', '')
                name = message.get('name', '')
                phone = message.get('phone', '')
                user_input = message.get('userInput', '')
                print("message:", message)
                
                if 'rejectedMessage' in message and message['rejectedMessage']:
                    rejected_message = message['rejectedMessage']
                    print("rejected_message:", rejected_message)
                else:
                    rejected_message = False
                print("map_agent_user====>",map_agent_user)
                if session_id not in active_sessions or rejected_message:
                    active_sessions[session_id] = websocket
                    store_messages_in_redis(message)
                    agent = Get_Matched_Available_Agent(message)
                    
                    if agent:
                        agent_id = agent['agent_id']
                        print("here.............", agent_id)
                        map_agent_user[session_id] = agent_id
                        r.hdel("waiting_area", session_id)
                        print("agent_sessions: ", agent_sessions)
                        
                        if agent_id in agent_sessions:
                            for connection_id, agent_websocket in agent_sessions.items():
                                if str(connection_id) == agent_id:
                                    message['isFirstMessage'] = True
                                    message["agent_id"] = agent_id
                                    await agent_websocket.send_text(json.dumps(message))
                    else:
                        messages = await fetch_messages()
                        asyncio.create_task(send_messages(session_id, messages, message))
                else:
                    agent_id = map_agent_user[session_id]
                    if agent_id in agent_sessions:
                        for connection_id, agent_websocket in agent_sessions.items():
                            if str(connection_id) == agent_id:
                                message['isFirstMessage'] = False
                                message["agent_id"] = agent_id
                                await agent_websocket.send_text(json.dumps(message))
                
    except WebSocketDisconnect:
        print(f"Agent disconnected for session_id: {session_id}")
    except Exception as e:
        print(f"Unexpected error: {e}")




    
    
async def fetch_messages():
    url = chatqueue#"http://10.16.7.113:8080/api/chat_queue_waiting_messages/"
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for bad status codes
    print("messages .",response.json())
    return response.json()    
    

async def send_messages(session_id, messages,message):
    start_time = time.time()
    last_message = None
    while True:
        # Check if the session is still active
        if session_id not in active_sessions:
            print(f"No active session for session_id: {session_id}")
            break
        print("print 1",message)
        websocket = active_sessions[session_id]
        current_time = time.time()
        elapsed_time = current_time - start_time
        # Check if an agent is available
        agents = Get_Matched_Available_Agent(message)
        print("print 2",agents)
        if agents:
            print("Agent available, stopping message sending...")
            
            
            agent_idl = agents['agent_id']
            map_agent_user[session_id] = agent_idl
            print(" agent_sessions ..",agent_sessions)
            print(" agent_idl  ",agent_idl)
            r.hdel("waiting_area", session_id)
            
            if agent_idl in agent_sessions:
                        print(".....")
                        for connection_id in agent_sessions.keys():
                            print("Key:", connection_id)
                            print(f"Type of connection_id: {type(connection_id)}, value: {connection_id}")
                            if str(connection_id) == agent_idl:  # Ensure comparison is between the same types
                                websocketn = agent_sessions[connection_id]
                                print(websocketn)
                                message['isFirstMessage']=True
                                message["agent_id"]=agent_idl
                                await websocketn.send_text(json.dumps(message))
                
                
            break
        
        print("print 3 ",messages)
        if messages:
            for messagem in messages[:]:  # Iterate over a copy of the list
                if elapsed_time >= messagem['time_interval']:
                    print(messagem['message_text'])
                    try:
                        await websocket.send_text(json.dumps(messagem))
                    except Exception as e:
                        print(f"Failed to send message: {e}")
                    messages.remove(messagem)  # Remove message after printing
            if not messages:  # Check if this was the last message
                last_message = messagem
        if last_message:
            print(last_message['message_text'])
            try:
                await websocket.send_text(json.dumps(last_message))
            except Exception as e:
                print(f"Failed to send last message: {e}")
        await asyncio.sleep(10)  # Use asyncio.sleep to prevent busy waiting

async def agent_dic(remsession_id):
        print("Calling remove function", remsession_id)
        message = {
            'message': 'Agent got disconnected. Please wait until the agent reconnects or connect to a new agent.',
            'sessionId': remsession_id,
            'agentName': '',  # Ideally, this should be dynamic
            'files': []
        }
        print("Disconnection message:", message)
        
        if remsession_id in active_sessions:
            ws = active_sessions[remsession_id]
            try:
                await ws.send_text(json.dumps(message))
                print("Removing active session", remsession_id, ws)
                del active_sessions[remsession_id]
            except Exception as e:
                print(f"Error sending message: {e}")
        else:
            print(f"Session ID {remsession_id} not found in active sessions.")


@app.websocket("/ws/user")
async def websocket_endpoint_user(websocket: WebSocket):
    await websocket.accept()
    print("sessions in the active session in ws/user:",agent_sessions,active_sessions)
    try:
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                print("message ---->",message)
                print("message for  user from agent",message)
                
                
                if 'event' in message:
                    if message['event'] == 'typing':
                        print("typing event received here ...", message)
                        session_id = message.get('session_id', '')
                        print("checking session id",session_id)
                        if session_id in active_sessions:
                            print("active_sessions :",active_sessions)
                            active_websocket = active_sessions[session_id]
                            try:
                                await active_websocket.send_text(json.dumps(message))
                            except Exception as e:
                                print(f"Error sending message to active session {session_id}: {e}")
                                if session_id in active_sessions:
                                    del active_sessions[session_id]
                        else:
                            print(f"Session ID {session_id} is not active.")
                        continue
                    
                    
                    elif message['event'] == 'stop_typing':
                        print("stop typing event received here ...", message)
                        session_id = message.get('session_id', '')
                        if session_id in active_sessions:
                            print("active_sessions :",active_sessions)
                            active_websocket = active_sessions[session_id]
                            try:
                                await active_websocket.send_text(json.dumps(message))
                            except Exception as e:
                                print(f"Error sending message to active session {session_id}: {e}")
                                if session_id in active_sessions:
                                    del active_sessions[session_id]
                        else:
                            print(f"Session ID {session_id} is not active.")
                        continue
                
                if 'event' not in message:
                    connection_id = message.get("agent_id")
                    session_id = message.get("sessionId")
                    if 'message' in message:
                        if session_id in active_sessions:
                            print("active_sessions :",active_sessions)
                            active_websocket = active_sessions[session_id]
                            try:
                                await active_websocket.send_text(json.dumps(message))
                            except Exception as e:
                                print(f"Error sending message to active session {session_id}: {e}")
                                if session_id in active_sessions:
                                    del active_sessions[session_id]
                        else:
                            print(f"Session ID {session_id} is not active.")
                    else:
                        if connection_id:
                            agent_sessions[connection_id] = websocket
                        response = {"message": "Data received successfully", "receivedData": message}
                        await websocket.send_text(json.dumps(response))
            except json.JSONDecodeError:
                print("Received invalid JSON.")
            except KeyError as e:
                print(f"Missing key in message: {e}")
    except WebSocketDisconnect:
        print("User disconnected",active_sessions.items())
        for session_id, ws in list(active_sessions.items()):
            #await agent_dic(session_id)
            if ws == websocket:
                del active_sessions[session_id]
        for connection_id, ws in list(agent_sessions.items()):
            if ws == websocket:
                del agent_sessions[connection_id]


                
        
        # message = {
        #     'message': 'agent got disconnected..please wait untill agent gets connected or connect to an new agent',
        #     'sessionId': disconnected_session,
        #     'agentName': 'ashokreddy',
        #     'files': []
        # }
        
        # print("dis message is", message)
        
        # if disconnected_session and disconnected_session in active_sessions:
        #     active_websocket = active_sessions[disconnected_session]
        #     await active_websocket.send_text(json.dumps(
        #         message
        #     ))
        # elif disconnected_connection and disconnected_connection in agent_sessions:
        #     agent_websocket = agent_sessions[disconnected_connection]
        #     await agent_websocket.send_text(json.dumps(
        #         message
        #     ))
        
        # if disconnected_session:
        #     del active_sessions[disconnected_session]
        # if disconnected_connection:
        #     del agent_sessions[disconnected_connection]


class SessionID(BaseModel):
    session_id: str
    agent_id:str
    agentName:str
load_dotenv()

#db config
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")

DB_CONFIG = {
    'dbname': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'host': DB_HOST,
    'port': DB_PORT
}

def connect_to_db():
    """Connect to the PostgreSQL database and return the connection and cursor."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        return conn, cursor
    except Exception as error:
        print(f"Error connecting to database: {error}")
        return None, None


# Redis configuration
redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_db = os.getenv("REDIS_DB")
print("redis_host,redis_port,redis_db are",redis_host,redis_port,redis_db)

# Initialize Redis client
redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)

@app.post("/remove-session1/")
async def remove_session(session: SessionID):
    session_id_to_remove = session.session_id
    print("remove key is",session_id_to_remove)
    await removeactivesession(session_id_to_remove)
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


async def removeactivesession(remsession_id):
    print("callimng remove function",remsession_id)
    message = {
            'message': 'agent closed the conversation.If you have any quries,please connect to an agent again.Thank you',
            'sessionId': remsession_id,
            'agentName': '',
            'files': []
        }
    if remsession_id in active_sessions:
        ws = active_sessions[remsession_id]
        await ws.send_text(json.dumps(message))
        print("removing active session", remsession_id, ws)
        del active_sessions[remsession_id]
    else:
        print(f"Session ID {remsession_id} not found in active sessions.")
    
    



def fetch_details(api_url):
    response = requests.get(api_url)
    response.raise_for_status()  # Raise an error for bad status codes
    return response.json()

def fetch_queue_skills():
    global fetch_detail_cache
    #testurl='http://127.0.0.1:8005/api/agent_queues'
    testurl=skills #'http://localhost:8000/skills'
    fetch_detail=fetch_details(testurl)
    print("fetch_detail ====>:",fetch_detail)
    fetch_detail_cache=fetch_detail



def Get_Matched_Available_Agent(message):
    api_url = redisagents#'http://127.0.0.1:8005/fetch_redis_agents'
    agents_data = fetch_agents(api_url)
    print("agents_data =====>",agents_data)
    
   
    
    for agent in fetch_detail_cache:
        agent_key = f"agent:{agent['agent_id']}"
        if agent_key in agents_data and agents_data[agent_key]['agent_id'] == str(agent['agent_id']):
            agents_data[agent_key].update({
                'queues': agent['queues'],
                'skills': agent['skills'],
                'max_chat_concurrent_interactions': agent['max_chat_concurrent_interactions'],
                'max_call_concurrent_interactions': agent['max_call_concurrent_interactions'],
                'max_email_concurrent_interactions': agent['max_email_concurrent_interactions']
            })

    # Print updated data
    print("Updated agents_data =====>", agents_data)
    
    matched_agent = find_matched_ready_agent(agents_data, message)
    if matched_agent:
        print(f"Matched ready agent: {matched_agent}")
    else:
        print("No agents are currently in the 'Ready' state matching the required queue and skills.")
    return matched_agent

def fetch_agents(api_url):
    response = requests.get(api_url)
    response.raise_for_status()  # Raise an error for bad status codes
    return response.json()



def find_matched_ready_agent(agents_data, message):
    print("checking :::====>agents ",agents_data)
    print("checking :::====>message",message)
    queues = message['queues']
    skills = message['skills']
    print("find_matched_ready_agent:", message)
    
    if 'rejectedMessage' in message and message['rejectedMessage']:
        print("Rejected message handling...")
        rejected_id = str(message['agent_id'])  # Ensure the rejected_id is a string
        ready_agents = [
            agent for agent in agents_data.values()
            if agent['current_state'] == 'Available' and 
               any(q in queues for q in agent['queues']) and 
               any(s in skills for s in agent['skills']) #and 
               #agent['agent_id'] != rejected_id
        ]
    else:
        print("Regular message handling...")
        ready_agents = [
            agent for agent in agents_data.values()
            if agent['current_state'] == 'Available' and 
               any(q in queues for q in agent['queues']) and 
               any(s in skills for s in agent['skills'])
        ]
    print("Ready agents:", ready_agents)
    
    if not ready_agents:
        return None
    


    best_agent = min(
    ready_agents,
    key=lambda x: datetime.strptime(x['last_state_change'], '%d/%m/%Y, %I:%M:%S %p')
)
    return best_agent
    # best_agent = min(
    #    ready_agents,
    #    key=lambda x: datetime.strptime(x['last_state_change'], '%m/%d/%Y, %I:%M:%S %p')
    #    )
    # return best_agent
 



            
            
def store_messages_in_redis(message):
    # Connect to Redis
    r = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
    # Store each message using session_id as the key with a delay of 10 seconds
    session_id = message['metadata']['session_id']
    r.hset("waiting_area", session_id, json.dumps(message))
    print(f"Message for session_id {session_id} stored in Redis.")
    # Delay of 10 seconds



@app.on_event("startup")
async def startup_event():
    asyncio.create_task(get_data())
    
async def get_data():
    while True:
        agent_rejected_message = r.hgetall('agent_rejected_message')
        if agent_rejected_message:
            print("Raw data from Redis:", agent_rejected_message)
            for key, value in agent_rejected_message.items():
                session_data = json.loads(value)
                session_id = session_data['metadata']['session_id']
                print(f"Session ID: {session_data['metadata']['session_id']}")
                print(f"User Input: {session_data['userInput']}")
                print("agent_sessions :",agent_sessions)
                print("session_data :",session_data)
                
                agent=Get_Matched_Available_Agent(session_data)
                print("agent :",agent)
                session_data['agent_id']=agent['agent_id']
                
                
                if agent:
                    agent_idl = agent['agent_id']
                    map_agent_user[session_id] = agent_idl
                    # r.hdel("waiting_area", session_id)
                    if agent_idl in agent_sessions:
                        for connection_id, agent_websocket in agent_sessions.items():
                            if str(connection_id) == agent_idl:
                               
                                await agent_websocket.send_text(json.dumps(session_data))
                else:
                    messages = await fetch_messages()
                    asyncio.create_task(send_messages(session_id, messages, session_data))
                
                r.hdel("agent_rejected_message", key)
        await asyncio.sleep(10)  # Check every 10 seconds


            
if __name__ == "__main__":
    
    fetch_queue_skills()
    import uvicorn
    uvicorn.run(app, host="localhost", port=9000)
