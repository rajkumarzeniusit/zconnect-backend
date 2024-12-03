import asyncio
import copy
import asyncpg
from aiohttp import ClientSession, ClientError
from fastapi import FastAPI, HTTPException
from email.mime.image import MIMEImage
import imaplib
import email
import email.utils
import base64
import json
import os
import re
import threading
import time
import smtplib
from uuid import uuid4
import uuid
from fastapi.responses import StreamingResponse
import psycopg2  # PostgreSQL driver
from email.message import EmailMessage
import redis
import requests
from fastapi import APIRouter, BackgroundTasks, FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, List, Dict, Optional, Union
import concurrent.futures
from fastapi_socketio import SocketManager
from datetime import datetime
import socketio
# from sockets import sio_app
# from sockets import sio_Server
# sio = socketio.Client()

# Initialize the AsyncServer with logger
sio_Server = socketio.AsyncServer(
    async_mode="asgi",
    logger=True,
    cors_allowed_origins=["http://localhost:3000"]
)

# Initialize ASGIApp with correct parameters
sio_app = socketio.ASGIApp(
    socketio_server=sio_Server,
    socketio_path=""
)
message = {}
fetch_detail_cache = None
global_session_id = None
#----------------------------- fast api setting---------------------------------------#
app = FastAPI()
app.mount('/sockets',app=sio_app)
# socket_manager = SocketManager(app=app)
# socket_manager = SocketManager(app=app)

# sio = SocketManager(app=app, cors_allowed_origins="*")
# sio = SocketManager(app, cors_allowed_origins="*") 

# class EmailEvent:
#     def __init__(self, subject: str, sender: str):
#         self.subject = subject
#         self.sender = sender

# listeners = []
class EmailObject(BaseModel):
    to_email: str
    sender: str 
    recipient: str 
    subject: str  
    date: str  
    body: str
    # attachments: List[str]
class postEmailObject(BaseModel):
    to_email: str
    sender: str 
    recipient: str 
    subject: str  
    date: str
    body: str
    session_id: str
    attachments: Optional[List[dict]]=[]
    cc: Optional[Any] = None
    message_id: str
class ReplyAllEmailObject(BaseModel):
    to_email: str
    sender: str 
    recipient: str 
    subject: str  
    date: str
    body: str
    session_id: str
    attachments: Optional[List[dict]]=[]
    cc: Optional[Any] = None
    message_id: str

class ForwardEmailObject(BaseModel):
    to_email: list[str]
    sender: str 
    recipient: str 
    subject: str  
    date: str
    body: str
    session_id: str
    attachments: Optional[List[dict]]=[]
    cc: Optional[Any] = None
    message_id: str

# class AgentState(BaseModel):
#     agentId: str
#     agentState:str
#     dateTime: str
class accept_Email(BaseModel):
    message_id: str
    session_id: str
    sender: str
    recipient: Any
    cc: Optional[Any] = None
    subject: str
    date: str
    body: str
    attachments: List[dict]

class Rejected_Email(BaseModel):
    message_id: str
    session_id: str
    sender: str
    recipient: Any
    cc_email: Optional[Any] = None
    subject: str
    date: str
    body: str
    attachments: List[dict]

class reply_mail(BaseModel):
    message_id: str
    session_id: str
    sender: str
    recipient: Any
    cc: Optional[Any] = None
    subject: str
    date: str
    body: str
    attachments: List[dict]

origins = [
    "*"
    # "http://localhost.tiangolo.com",
    # "https://localhost.tiangolo.com",
    # "http://localhost:3000",
    # "http://localhost:8080",
    # "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
polling_active = True
email_data :{} # type: ignore
mail_username:any=None
mailbox_password:str
filtered_attachments = [] 
# @app.get("/")
# def root():
#     return {
#         "Success": True,
#         "message": "Hello, welcome to the first API"
#     }
# @sio.event
# def connect():
#     print("Socket.IO connected!")

# @sio.event
# def disconnect():
#     print("Socket.IO disconnected!")
try:
    redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
    print("redis data base connected susscefully")
except redis.RedisError as e:
    raise HTTPException(status_code=500, detail=f"Redis connection error: {str(e)}")
agent_details =[
     {
    "id": 1,
    "agent_id": "ashokreddy@gmail.com",
    "queues": [
      "technicalsupportqueue@1"
    ],
    "skills": [
      "networking_skill"
    ],
    "max_chat_concurrent_interactions": 1,
    "max_call_concurrent_interactions": 3,
    "max_email_concurrent_interactions": 1
  },
  {
    "id": 2,
    "agent_id": "Gopi@gamil.com",
    "queues": [
      "technicalsupportqueue@1",
      "customer_servicequeue@123"
    ],
    "skills": [
      "networking_skill",
      "troubleshooting_skill"
    ],
    "max_chat_concurrent_interactions": 1,
    "max_call_concurrent_interactions": 3,
    "max_email_concurrent_interactions": 1
  }
]

@sio_Server.event
async def connect(sid, environ, auth):
    print("Socket connected:", sid)

# @sio_Server.event
# async def onNewEmail(sid, data):
#     print("we are entering the onnew email values")
#     await sio_Server.emit('new_email', {
#         'sender': "ashok",
#         'subject': "reddy",
#         'body': "werftgh23e4r5t"
#     })

@sio_Server.event
async def disconnect(sid):
    print("Socket disconnected:", sid)
@app.get("/")
def root():
    return {
        "Success": True,
        "message": "Hello, welcome to the first API"
    }

# @app.get("/mails")
# async def fetch_all_threads():
#     conn=connect_to_database()
#     cursor=conn.cursor()
#     try:
#         fetch_query="SELECT * FROM emails ORDER BY session_id, timestamp ASC"
#         cursor.execute(fetch_query)
#         emails=cursor.fetchall()
#         threads={}
#         def parse_json_field(field):
#             if isinstance(field,memoryview):
#                 return json.loads(field.tobytes().decode('utf-8'))
#             elif isinstance(field,str):
#                 return json.loads(field)
#             return None
#         for email in emails:
#             session_id=email[2]
#             if session_id not in threads:
#                 threads[session_id]=[]
#             email_data={
#                 "account_id":email[0],
#                 "message_id":email[1],
#                 "session_id":email[2],
#                 "direction":email[3],
#                 "sender":email[4],
#                 "recipient":parse_json_field(email[5]),#Handle both memoryview and string
#                 "cc_emails":parse_json_field(email[6]),#Handle both memoryview and string
#                 "subject":email[7],
#                 "timestamp":email[8],
#                 "body":email[9],
#                 "attachments":parse_json_field(email[10])#Handle both memoryview and string
#             }
#             threads[session_id].append(email_data)
#         all_threads=[{"session_id":session_id,"emails":emails}for session_id,emails in threads.items()]
#         return{"threads":all_threads}
#     except Exception as e:
#         raise HTTPException(status_code=500,detail=f"Error fetching email threads from database:{str(e)}")
#     finally:
#         conn.close()



@app.get("/mails/{agent}")
async def fetch_all_threads(agent: str):
    conn = connect_to_database()
    cursor = conn.cursor()
    try:
        fetch_query = """
       select * from emails order by TIMESTAMP DESC
        """
        cursor.execute(fetch_query, (agent, agent))
        emails = cursor.fetchall()
        threads = {}
        
        def parse_json_field(field):
            if isinstance(field, memoryview):
                return json.loads(field.tobytes().decode('utf-8'))
            elif isinstance(field, str):
                return json.loads(field)
            return None
        
        for email in emails:
            session_id = email[2]
            if session_id not in threads:
                threads[session_id] = []
            email_data = {
                "account_id": email[0],
                "message_id": email[1],
                "session_id": email[2],
                "direction": email[3],
                "sender": email[4],
                "recipient": parse_json_field(email[5]),  # Handle both memoryview and string
                "cc_emails": parse_json_field(email[6]),  # Handle both memoryview and string
                "subject": email[7],
                "timestamp": email[8],
                "body": email[9],
                "attachments": parse_json_field(email[10])  # Handle both memoryview and string
            }
            threads[session_id].append(email_data)
        
        all_threads = [{"session_id": session_id, "emails": emails} for session_id, emails in threads.items()]
        return {"threads": all_threads}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching email threads from database: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()



@app.get("/emails")
async def get_email():
    if email_data is None:
        raise HTTPException(status_code=400, detail="No email data available")
    return email_data
# @app.post("/agentStatus")
# async def agent_status(item:AgentState):
#     try:
#        return {
#                 "Success":True,
#                 "Message":'',
#                 "data":item
#             }
#     except Exception as e :
#      raise HTTPException(status_code=500,detail=str(e))
# @app.post("/log_state_change")
# async def log_state_change(agent_state: AgentState):
#     try:
#         # Print the agent state data
#         print("agent_state",agent_state)
#         print(f"Agent ID: {agent_state.agentId}")
#         # print(f"Agent queues: {agent_state.queue}")
#         # print(f"Agent skills: {agent_state.skills}")
#         print(f"Agent state changed to: {agent_state.agentState}")
#         print(f"Time: {agent_state.dateTime}")
       
#         redis_client.hset('agent:' + str(agent_state.agentId), 'agent_id', agent_state.agentId)
#         # redis_client.hset('agent:' + str(agent_state.id), 'queue', agent_state.queue)
#         # redis_client.hset('agent:' + str(agent_state.id), 'skills', agent_state.skills)
#         redis_client.hset('agent:' + str(agent_state.agentId), 'current_state', agent_state.agentState)
#         redis_client.hset('agent:' + str(agent_state.agentId), 'last_state_change', agent_state.dateTime)
#         # redis_client.hset('agent:' + str(agent_state.id), 'maxConcurrentInteraction', agent_state.maxConcurrentInteraction)
#         return {"message": "Agent state change logged and stored in Redis hash"}
 
#     except redis.RedisError as e:
#         raise HTTPException(status_code=500, detail=f"Redis error: {str(e)}")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")



@app.post("/sendemail")
def send_email (item: postEmailObject):
    try:
        print("send email object",item)
        send_email(item)
        storemail(item)
        return{
            "Success":True,
            "Message":"mail send sucessfully",
            "data":item,
            "emailusername":mail_username,
            "emailpassword":mailbox_password
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def storemail(email:postEmailObject):
    print("store email",email)
    conn = connect_to_database()
    cursor = conn.cursor()

    try:
        account_query = "SELECT id, routing_group FROM account_configurations WHERE username = 'itzenius@gmail.com'"
        cursor.execute(account_query)
        result = cursor.fetchone()
        account_id, routing_group = result if result else (None, None)
        print("account_id ,routing_group",account_id,routing_group)

        # Check if an email with the same session_id exists
        # check_query = get_session_id(cursor, email.message_id)
        # print("check_query",check_query)
        sender_email = extract_email_addresses(email.sender)
        recipient_emails = extract_email_addresses(email.recipient)
        print("sender and receiver is",sender_email,recipient_emails)
        print("email object is",email.cc,email.to_email,email.recipient)
        print("email body in before storing is", email.body)
       
        exists=True
        insert_query = """
                INSERT INTO emails (account_id, message_id, session_id, direction, sender, recipient, cc_emails, subject, timestamp, body, attachments)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        cursor.execute(insert_query, (
                account_id, email.message_id, email.session_id, 'outgoing', email.sender, 
                json.dumps(email.recipient), json.dumps(email.cc), email.subject, 
                email.date, email.body, json.dumps(email.attachments)
            ))
        message = "Email inserted successfully"
       

        # if exists:
        #     print("enetred")

        #     # Update the existing email
        #     update_query = """
        #         UPDATE emails
        #         SET message_id = %s, sender = %s, recipient = %s, cc_emails = %s, subject = %s, timestamp = %s, body = %s, attachments = %s
        #         WHERE session_id = %s
        #     """
        #     cursor.execute(update_query, (
        #         email.message_id, sender_email, json.dumps(recipient_emails), 
        #         json.dumps(email.cc), email.subject, email.date, email.body, 
        #         json.dumps(email.attachments), email.session_id
        #     ))
        #     rows_affected = cursor.rowcount
        #     print("Rows affected by update:", rows_affected)
        #     message = "Email updated successfully"
        # else:

        #     print("there is no session id")

        conn.commit()
        return {"message": message}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error inserting/updating email in database: {str(e)}")

    finally:
        conn.close()




    
@app.post("/replyall")
def reply_all_email(item: ReplyAllEmailObject):
    try:
        print("reply all object",item)
        send_email(item)
        storemail(item)
        # reply_all_internal(item)
        
        return {
            "Success": True,
            "Message": "Reply all email sent successfully"
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
@app.post("/forward")
def forward_email(item: ForwardEmailObject):
    try:
        print("ForwardEmailObject object",item)
        send_email(item)
        storemail(item)
        # forward_email_internal(item)
        return {
            "Success": True,
            "Message": "Email forwarded successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/agents")
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
@app.get("/agents_details")
async def get_all_agent_details():
     return agent_details

# @app.post("/store_emails")
# async def receive_email(email:accept_Email):
#     conn = connect_to_database()
#     cursor = conn.cursor()

#     try:
#         account_query = "SELECT id, routing_group FROM account_configurations WHERE username = 'itzenius@gmail.com'"
#         cursor.execute(account_query)
#         result = cursor.fetchone()
#         account_id, routing_group = result if result else (None, None)

#         insert_query = """
#             INSERT INTO emails (account_id, message_id, session_id, direction, sender, recipient, cc_emails, subject, timestamp, body, attachments)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#         """

#         if isinstance(email.cc, list):
#             cc_emails_str = ', '.join(email.cc)
#         elif isinstance(email.cc, str):
#             cc_emails_str = email.cc
#         else:
#             cc_emails_str = ''

#         if isinstance(email.recipient, list):
#             recipient_str = ', '.join(email.recipient)
#         elif isinstance(email.recipient, str):
#             recipient_str = email.recipient
#         else:
#             recipient_str = str(email.recipient)
        
#         cursor.execute(insert_query, (
#             account_id, email.message_id, email.session_id, 'incoming', email.sender, recipient_str, 
#             cc_emails_str, email.subject, email.date, email.body, json.dumps(email.attachments)
#         ))

#         conn.commit()
#         return {"message": "Email inserted successfully"}

#     except Exception as e:
#         conn.rollback()
#         raise HTTPException(status_code=500, detail=f"Error inserting email into database: {str(e)}")

#     finally:
#         conn.close()

# def extract_email_addresses(text):
#     # Regular expression to find email addresses
#     email_regex = r'[\w\.-]+@[\w\.-]+'
#     return list(set(re.findall(email_regex, text))) 

# @app.on_event("startup")
# async def startup_event():
#     asyncio.create_task(get_rejected_data())

# async def get_rejected_data():
#     conn = connect_to_database()
#     cursor = conn.cursor()

#     while True:
#         try:
#             # rows = await asyncio.to_thread(fetch_rejected_messages, conn)
#             account_query = "SELECT * FROM rejected_emails"
#             cursor.execute(account_query)
#             rows = cursor.fetchone()

#             if rows:
#                 print("Raw data from PostgreSQL:", rows)

#             message ={
#             "queues": 
#       "technicalsupportqueue@1"
#     ,
#     "skills": 
#       "networking_skill"
#     ,
#         }
#             agent = Get_Matched_Available_Agent(message)
#             print("agents in the getmatched_available for rejected messages",agent)




#         except Exception as e:
#             print(f"Error fetching or processing data: {str(e)}")

#         await asyncio.sleep(10)  # Check every 10 seconds

  



@app.post("/store_rejected_emails")
async def receive_rejected_email(email: Rejected_Email):
    print("store rejected email", email)
    print("store rejected email", email.session_id)
    conn = connect_to_database()
    cursor = conn.cursor()

    try:
        account_query = "SELECT id, routing_group FROM account_configurations WHERE username = 'itzenius@gmail.com'"
        cursor.execute(account_query)
        result = cursor.fetchone()
        account_id, routing_group = result if result else (None, None)

        sender_email = extract_email_addresses(email.sender)
        recipient_emails = extract_email_addresses(email.recipient)
        print("sender and receiver", sender_email, recipient_emails)

        # Insert a new rejected email
        insert_query = """
            INSERT INTO rejected_emails (account_id, message_id, session_id, direction, sender, recipient, cc_emails, subject, timestamp, body, attachments)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            account_id, email.message_id, email.session_id, 'rejected', email.sender,
            json.dumps(email.recipient), json.dumps(email.cc_email), email.subject,
            email.date, email.body, json.dumps(email.attachments)
        ))

        conn.commit()
        return {"message": "Rejected email inserted successfully"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error inserting rejected email in database: {str(e)}")

    finally:
        conn.close()

def extract_email_addresses(text):
    # Regular expression to find email addresses
    email_regex = r'[\w\.-]+@[\w\.-]+'
    matches = re.findall(email_regex, text)
    return matches[0] if matches else None

@app.post("/store_emails")
async def receive_email(email:accept_Email):
    print("store email",email)
    print("store email",email.session_id)
    conn = connect_to_database()
    cursor = conn.cursor()

    try:
        account_query = "SELECT id, routing_group FROM account_configurations WHERE username = 'itzenius@gmail.com'"
        cursor.execute(account_query)
        result = cursor.fetchone()
        account_id, routing_group = result if result else (None, None)

        # Check if an email with the same session_id exists
        # check_query = "SELECT COUNT(*) FROM emails WHERE session_id = %s"
        # cursor.execute(check_query, (email.session_id,))
        # exists = cursor.fetchone()[0] > 0
        sender_email = extract_email_addresses(email.sender)
        recipient_emails = extract_email_addresses(email.recipient)
        print("to check to",email.recipient)
        print("to check cc",email.cc)
        print("sender and receiver",sender_email,recipient_emails)

        insert_query = """
                INSERT INTO emails (account_id, message_id, session_id, direction, sender, recipient, cc_emails, subject, timestamp, body, attachments)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        cursor.execute(insert_query, (
                account_id, email.message_id, email.session_id, 'incoming', email.sender, 
                json.dumps(email.recipient), json.dumps(email.cc), email.subject, 
                email.date, email.body, json.dumps(email.attachments)
            ))
        message = "Email inserted successfully"


        # if exists:
        #     # Update the existing email
        #     update_query = """
        #         UPDATE emails
        #         SET message_id = %s, sender = %s, recipient = %s, cc_emails = %s, subject = %s, timestamp = %s, body = %s, attachments = %s
        #         WHERE session_id = %s
        #     """
        #     cursor.execute(update_query, (
        #         email.message_id, sender_email, json.dumps(recipient_emails), 
        #         json.dumps(email.cc), email.subject, email.date, email.body, 
        #         json.dumps(email.attachments), email.session_id
        #     ))
        #     message = "Email updated successfully"
        # else:
        #     # Insert a new email
        #     insert_query = """
        #         INSERT INTO emails (account_id, message_id, session_id, direction, sender, recipient, cc_emails, subject, timestamp, body, attachments)
        #         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        #     """
        #     cursor.execute(insert_query, (
        #         account_id, email.message_id, email.session_id, 'incoming', sender_email, 
        #         json.dumps(recipient_emails), json.dumps(email.cc), email.subject, 
        #         email.date, email.body, json.dumps(email.attachments)
        #     ))
        #     message = "Email inserted successfully"

        conn.commit()
        return {"message": message}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error inserting/updating email in database: {str(e)}")

    finally:
        conn.close()
def fetch_details(api_url):
    response = requests.get(api_url)
    print("we are entering into the fect_details urlmethods for checking responce")
    response.raise_for_status()  # Raise an error for bad status codes
    return response.json()
 
def fetch_queue_skills():
    global fetch_detail_cache
    testurl='http://127.0.0.1:8000/agents_details'
    print("we are entering before fecth deatils =====>123456")
    fetch_detail=fetch_details(testurl)
    print("we are entering after fecth deatils")
    print("fetch_detail ====>:",fetch_detail)
    fetch_detail_cache=fetch_detail
def Get_Matched_Available_Agent(message):
    print("matched method")
    api_url = 'http://127.0.0.1:8000/agents'
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
    print("fetch agents",api_url)
    response = requests.get(api_url)
    print("response",response)
    response.raise_for_status()  # Raise an error for bad status codes
    print("response.json()",response.json())
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
               any(s in skills for s in agent['skills']) and
               agent['agentId'] != rejected_id
        ]
    else:
        print("Regular message handling...")
        print("agents_daata_values",agents_data.values())
        ready_agents = [
            agent for agent in agents_data.values()
            if agent['current_state'] == 'Available' and
               any(q in queues for q in agent['queues']) and
               any(s in skills for s in agent['skills'])
        ]
    print("Ready agents:", ready_agents)
   
    if not ready_agents:
        return None
   
    # best_agent = min(
    #     ready_agents,
    #     key=lambda x: datetime.strptime(x['last_state_change'], '%d/%m/%Y, %H:%M:%S')
    # )
    best_agent = min(
    ready_agents,
    key=lambda x: datetime.strptime(x['last_state_change'], '%d/%m/%Y, %I:%M:%S %p')
)
    return best_agent
# @app.get("/start-fetching-emails")
# async def start_fetching_emails(background_tasks: BackgroundTasks):
#     background_tasks.add_task(check_new_emails)
#     return {"message": "Email fetching started."}
# @app.get("/subscribe-email-events")
# async def subscribe_email_events(response: Response):
#     async def event_stream():
#         while True:
#             event = await get_next_event() 
#             print("events is getting displayed in the section of subscribe method",event)
#              # Implement this function to get the next email event
#             if event:
#                 yield f"data: {json.dumps(event.__dict__)}\n\n"
#             await asyncio.sleep(1)

#     response.headers["Content-Type"] = "text/event-stream"
#     response.headers["Cache-Control"] = "no-cache"
#     response.headers["Connection"] = "keep-alive"
#     return StreamingResponse(event_stream())

async def get_next_event():
    # Implement this function to get the next email event
    pass
# ------------------------- Authentication and Connection Functions ---------------------
 
def get_oauth2_token(account_type):
    """Handles OAuth2 authentication for Microsoft accounts (Office 365)."""
 
    if account_type == "office365":
        # TODO: Integrate the 'msgraph-core' library for obtaining an OAuth2 token
        print("OAuth2 setup required for Office 365. Please refer to the following resources:")
        print(" * Register an app in Azure AD: https://learn.microsoft.com/en-us/graph/auth-register-app-v2")
        print(" * Grant IMAP.AccessAsUser.All permissions: https://learn.microsoft.com/en-us/graph/auth-v2-user")
        return None  # Placeholder
 
    else:
        print("OAuth2 not implemented for Gmail. Please use an app password.")
        return None
#SAVE_DIRECTORY = r'C:\Users\rajkumar\OneDrive - Zenius IT Services Private Limited\zconnect'
SAVE_DIRECTORY = r'C:\Users\rajkumar\Desktop\email\images'
BASE_URL = 'http://localhost:8037/images/'
# C:\Users\ashok.reddy\Desktop\ZeniusCTC\attachments/

def connect_to_mailbox(account_type, username, password):
    """Connects to the mailbox using either IMAP4_SSL or OAuth2"""
    conn = connect_to_database()
    cursor = conn.cursor()
    global mail_username
    mail_username = username
    global mailbox_password
    mailbox_password = password
    # Fetch mailbox configuration
    config_query = """
        SELECT imap_server, imap_port, imap_use_ssl, smtp_server, smtp_port, smtp_use_ssl
        FROM account_configurations
        WHERE username = %s
    """
    cursor.execute(config_query, (username,))
    result = cursor.fetchone()
    if not result:
        print(f"Error: No mailbox configuration found for user {username}")
        return None
 
    imap_server, imap_port, imap_use_ssl, smtp_server, smtp_port, smtp_use_ssl = result
 
    try:
        if account_type == "office365":
            oauth2_token = get_oauth2_token(account_type)
            if oauth2_token:
                mailbox = imaplib.IMAP4_SSL(imap_server, imap_port)  # Adjust if not using SSL
                mailbox.authenticate('XOAUTH2', lambda x: oauth2_token)
            else:
                print("Error: Could not obtain OAuth2 token")
                return None
        else:  
            if imap_use_ssl:
                mailbox = imaplib.IMAP4_SSL(imap_server, imap_port)
            else:
                mailbox = imaplib.IMAP4(imap_server, imap_port)
            mailbox.login(username, password)
            return mailbox
 
    except (imaplib.IMAP4.error, Exception) as e:
        print(f"Connection error: {e}")
        return None
    
async def connect_to_database1():
    try:
        conn = await asyncpg.connect(
            database="zconnect",
            user="postgres",
            password="123456789",
            host="127.0.0.1",
            port="9999"
        )
        print("Database connected successfully")
        return conn
    except Exception as e:
        print(f"Error: {e}")
        return None
 
def connect_to_database():
    # db_config = {  # Replace with your actual database settings
    #     'database': 'postgres',
    #     'user': 'fusionpbx',
    #     'password': 'fusionpbx',
    #     'host': '127.0.0.1',  #10.16.8.132
    # }

    # conn = psycopg2.connect(**db_config)
    # return conn
    try:
        conn = psycopg2.connect(
          dbname= "zconnect",
          user="postgres",
          password= "123456789",
          host= "127.0.0.1",
          port="9999"
        )
        print("data base connected successfully")
        return conn
    except psycopg2.OperationalError as e:
         print(f"Error : {e}")
         return None
# --------------------------------- Attachment Handling Functions ---------------------------------
# def process_email_attachments(email_message):
#    for part in email_message.walk():
#         if part.get_content_maintype() == 'multipart':
#             continue
#         if part.get('Content-Disposition') is None:
#             continue
#         filename = part.get_filename()
#         if filename:
#             save_attachment(part, filename)
#         else:
#             print("No filename found in the attachment part.")
# def process_attachments(email_message, email_id):
#     """Processes email attachments."""
#     attachments = []
#     if email_message.is_multipart():
#         for part in email_message.walk():
#             content_type = part.get_content_type()
#             if content_type in ['application/octet-stream', 'image/jpeg', 'image/png', 'application/zip','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
#                                 'application/vnd.openxmlformats-officedocument.wordprocessingml.document','application/x-zip-compressed'
#                                 'application/vnd.ms-excel', 'application/pdf', 'application/msword','application/docx']:  # Adjust based on your needs
#                 filepath = save_attachment(part, email_id)
#                 cid = part.get('Content-ID')
#                 if cid:
#                     cid = cid.strip('<>')
#                 if filepath:
#                     attachments.append({
#                         'filepath': filepath,
#                         'cid': cid
#                     })
#                 print("filepath-in attachments method==>", filepath)
#     return attachments

def process_attachments(email_message, email_id):
    """Processes email attachments."""
    attachments = []
    try:
        print("message is",email_message)
        if email_message.is_multipart():
            for part in email_message.walk():
                try:
                    print("part is",part)
                    content_type = part.get_content_type()
                    print("content type is",content_type)
                    if content_type in [
                        'application/octet-stream', 'image/jpeg', 'image/png', 'application/zip',
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        'application/x-zip-compressed', 'application/vnd.ms-excel', 'application/pdf',
                        'application/msword', 'application/docx', 'application/vnd.oasis.opendocument.text','text/plain','text/csv'
                    ]:
                        filepath = save_attachment(part, email_id)
                        cid = part.get('Content-ID')
                        if cid:
                            cid = cid.strip('<>')
                        if filepath:
                            attachments.append({
                                'filepath': filepath,
                                'cid': cid
                            })
                        print(f"Attachment saved: {filepath}")
                except Exception as e:
                    print(f"Error processing part: {e}")
                    continue
    except Exception as e:
        print(f"Error processing attachments: {e}")

    return attachments


def save_attachment(part, email_id):
    """Saves attachments to disk."""
    print("details for part",part)
    filename = part.get_filename()
    if filename:
        # folder_name = f"attachments/{email_id}"
        # if not os.path.exists(folder_name):
        #     os.makedirs(folder_name)
        # filepath = os.path.join(folder_name, filename)
        # folder_name = f"static/attachments/{email_id}"
        # if not os.path.exists(folder_name):
        #     os.makedirs(folder_name)
        # filepath = os.path.join(folder_name, filename)
        # if filename.startswith('http:') or filename.startswith('https:'):
        #     print("Invalid filename:", filename)
        #     return None
        
        # filename = sanitize_filename(filename)
        if not os.path.exists(SAVE_DIRECTORY):
         os.makedirs(SAVE_DIRECTORY)
        filepath = os.path.join(SAVE_DIRECTORY, filename)
        with open(filepath, "wb") as f:
            f.write(part.get_payload(decode=True))
        return filepath
    print("filepath-in  save attachments method==>", filepath)
    return None
# def save_attachment(attachment, filename):
#     try:
#         if not os.path.exists(SAVE_DIRECTORY):
#             os.makedirs(SAVE_DIRECTORY)
#         filepath = os.path.join(SAVE_DIRECTORY, filename)
#         with open(filepath, 'wb') as f:
#             f.write(attachment.get_payload(decode=True))
#         print(f"Attachment saved in the name of : {filename}")
#     except Exception as e:
#         print(f"Failed to save attachment {filename}: {e}")
# ------------------------------- Email Handling Functions ------------------------------
def filtered_attaacthments(filterattachments):
    # filtered_attachments = [
    #         attachment for attachment in filterattachments
    #         if not attachment['filepath'].lower().endswith(('.png', '.jpg', '.jpeg'))
    #     ]
    filtered_attachments = [
            attachment for attachment in filterattachments
            if not attachment['filepath'].lower().endswith(('.png', '.jpg', '.jpeg'))
        ]

        # Replace file path with the desired URL
    for attachment in filtered_attachments:
        attachment['filepath'] = attachment['filepath'].replace(SAVE_DIRECTORY, BASE_URL)
        attachment['filepath'] = attachment['filepath'].replace('\\', '')
    print("Filtered and Updated Attachments:", filtered_attachments)
    return filtered_attachments
def update_email_data(sender, recipient, to_email, cc_email,subject, date,body,attachmentss):
    # attachment_urls = [os.path.join(SAVE_DIRECTORY, os.path.basename(attachment['filepath'])) for attachment in attachments if attachment['filepath']]
    # print("attachments in the update_email_data", attachmentss)

   
    # filtered_attachments =  filtered_attaacthments(attachmentss)
    filtered_attachments = [
        attachment for attachment in attachmentss
        if not attachment['filepath'].lower().endswith(('.png', '.jpg', '.jpeg'))
    ]

    # Replace file path with the desired URL
    for attachment in filtered_attachments:
        attachment['filepath'] = attachment['filepath'].replace(SAVE_DIRECTORY, BASE_URL)
        attachment['filepath'] = attachment['filepath'].replace('\\', '')

        print("Filtered Attachments:", filtered_attachments)
    global email_data
    email_data = {
        "sender": sender,
        "recipient": recipient,
        "to_email": to_email,
        "cc_email":cc_email,
        "subject": subject,
        "date": date,
        "body":body,
        "attachments":filtered_attachments
     
    }
# def add_listener(listener):
#     listeners.append(listener)
def get_session_id(cursor, messages_id):
    print(f"Querying for message_id: {messages_id}")
    query = "SELECT session_id FROM emails WHERE message_id = %s"
    cursor.execute(query, (messages_id,))
    result = cursor.fetchone()
    print("Result from query:", result)
    return result[0] if result else None
def update_body_with_attachments(body, attachments):
    """Replace CID references in the body with URLs to the attachments."""
    print("attachemtns in the body update_body_with_attachments",body)
    # print("attachemtns in the body update_body_with_attachments ====>123455",attachments)
    for attachment in attachments:
        cid = attachment['cid']
        filepath = attachment['filepath']
        # Extract the filename from the filepath
        filename = os.path.basename(filepath)
        print("filename when we sending the data",filename)
        # Replace the local file path prefix with the base URL
        relative_filepath = filepath.replace(
            SAVE_DIRECTORY,
            BASE_URL
        )
        relative_filepath = relative_filepath.replace('\\', '')
        # print("relative_filepath in the email",relative_filepath)
        # Construct the URL
        url = f"{relative_filepath}"
        # print("after modifing urls in the emai/",url)
        # Replace the CID reference with the URL
        body = body.replace(f"cid:{cid}", url)
    return body

##### imp #######################################################################


# async def check_new_emails(mailbox):
#     global global_session_id
#     mailbox.select("INBOX")
#     result, data = mailbox.search(None, "UNSEEN")
#     if result != 'OK':
#         print("Error checking for new emails.")
#         return
#     conn = connect_to_database()
#     cursor = conn.cursor()
#     print("emails ids before entering for loop ===>", data[0].split())
#     for email_id in data[0].split():
#         result, email_data = mailbox.fetch(email_id, '(RFC822)')
#         email_message = email.message_from_bytes(email_data[0][1])

#         # Print all headers
#         print("Email Headers:")
#         for header, value in email_message.items():
#             print(f"{header}: {value}")

#         received_headers = email_message.get_all('Received', [])
#         print("received headers",received_headers)
#         received_info = None
#         if received_headers:
#             for header in received_headers:
#                 match = re.search(r'from (.*?\.PROD\.OUTLOOK\.COM)', header)
#                 if match:
#                     received_info = match.group(1)
#                     break  # Stop after the first match
#         print("Received Header Info:", received_info)

#         # Process Attachments
#         attachments = process_attachments(email_message, email_id)
#         print("Attachments:", attachments)

#         # Email Decoding
#         sender = email_message['From']
#         recipient = email_message['To']
#         raw_To = email_message['To']
#         to_email = email.utils.parseaddr(raw_To)[1]
#         to_email = "'" + to_email + "'"
#         subject = email_message['Subject']
#         date = email_message['Date']
#         cc_email = email_message['Cc']
#         messages_id = str(email_id)
#         messages_id = email.utils.parseaddr(email_message['Message-ID'])[1]
#         print("message_id Message-ID =====>", messages_id)
#         in_reply_to = email_message['In-Reply-To']
#         references = email_message['References']
#         unique_id = email_message['X-Unique-ID']
#         print("unique_id X-Unique-ID =====>", unique_id)
#         print("in_reply_to In-Reply-To =====>", in_reply_to)
#         print("references References =====>", references)

#         global_session_id = str(uuid.uuid4())

#         body = None
#         if email_message.is_multipart():
#             for part in email_message.walk():
#                 content_disposition = str(part.get("Content-Disposition"))
#                 content_type = part.get_content_type()

#                 if content_type == 'text/plain' and "attachment" not in content_disposition:
#                     body = part.get_payload(decode=True).decode()
#                     print("body",body)
#                     print("attchments",attachments)
#                     body = update_body_with_attachments(body, attachments)
#                     print("updated body with attchmnets",body)
#                     break  # Stop after processing the first plain text body part

#         else:
#             body = email_message.get_payload(decode=True).decode()

#         print("Final Body:", body)

#         # Further processing...

#         message ={
#             "queues": 
#       "technicalsupportqueue@1"
#     ,
#     "skills": 
#       "networking_skill"
#     ,
#         }
#         agent = Get_Matched_Available_Agent(message)
#         print("agents in the getmatched_avalia  1ble",agent)
#         if agent:
#                     agent_idl = agent['agent_id']
#                     print("here.............",agent_idl)
#                     await sio_Server.emit('new_email', {
#                         'sender': sender,
#                         'message_id':received_info,
#                         'recipient': recipient,
#                         'to_email': to_email,
#                         'cc_email':cc_email,
#                         'subject': subject,
#                         'date': date,
#                         'body':body,
#                         'session_id':global_session_id ,
#                         "attachments": filtered_attaacthments(attachments)
#                     })
#                     print("matched agent is avalible ")

#         else:
#               print("macthed agent is not avalible")


#     conn.commit()
#     conn.close()

##### above is imp #######################################################################
async def check_new_emails(mailbox):
    global global_session_id
    mailbox.select("INBOX")
    result, data = mailbox.search(None, "UNSEEN")
    if result != 'OK':
        print("Error checking for new emails.")
        return
    conn = connect_to_database()
    cursor = conn.cursor()
    print("emails ids before entering for loop ===>", data[0].split())
    
    for email_id in data[0].split():
        result, email_data = mailbox.fetch(email_id, '(RFC822)')
        email_message = email.message_from_bytes(email_data[0][1])

        # Print all headers
        print("Email Headers:")
        for header, value in email_message.items():
            print(f"{header}: {value}")

        received_headers = email_message.get_all('Received', [])
        print("received headers", received_headers)
        received_info = None
        if received_headers:
            for header in received_headers:
                match = re.search(r'from (.*?\.PROD\.OUTLOOK\.COM)', header)
                if match:
                    received_info = match.group(1)
                    break  # Stop after the first match
        print("Received Header Info:", received_info)
        
        if received_info is None:
            messages_id = email.utils.parseaddr(email_message['Message-ID'])[1]
            received_info = messages_id

        print("Final Received Info:", received_info)

        # Process Attachments
        attachments = process_attachments(email_message, email_id)
        print("Attachments:", attachments)

        # Email Decoding
        sender = email_message['From']
        recipient = email_message['To']
        raw_To = email_message['To']
        to_email = email.utils.parseaddr(raw_To)[1]
        to_email = "'" + to_email + "'"
        subject = email_message['Subject']
        date = email_message['Date']
        cc_email = email_message['Cc']
        messages_id = str(email_id)
        messages_id = email.utils.parseaddr(email_message['Message-ID'])[1]
        print("message_id Message-ID =====>", messages_id)
        in_reply_to = email_message['In-Reply-To']
        references = email_message['References']
        unique_id = email_message['X-Unique-ID']
        print("unique_id X-Unique-ID =====>", unique_id)
        print("in_reply_to In-Reply-To =====>", in_reply_to)
        print("references References =====>", references)

        global_session_id = str(uuid.uuid4())

        body = None
        if email_message.is_multipart():
            for part in email_message.walk():
                content_disposition = str(part.get("Content-Disposition"))
                content_type = part.get_content_type()

                if content_type == 'text/plain' and "attachment" not in content_disposition:
                    body = part.get_payload(decode=True).decode()
                    print("body", body)
                    print("attachments", attachments)
                    body = update_body_with_attachments(body, attachments)
                    print("updated body with attachments", body)
                    break  # Stop after processing the first plain text body part

        else:
            body = email_message.get_payload(decode=True).decode()

        print("Final Body:", body)

        # Further processing...
        message = {
            "queues": "technicalsupportqueue@1",
            "skills": "networking_skill",
        }

        # Loop until an agent becomes available
        while True:
            agent = Get_Matched_Available_Agent(message)
            print("Checking for available agents:", agent)
            
            if agent:
                agent_idl = agent['agent_id']
                print("Matched agent:", agent_idl)
                
                await sio_Server.emit('new_email', {
                    'sender': sender,
                    'message_id': received_info,
                    'recipient': recipient,
                    'to_email': to_email,
                    'cc_email': cc_email,
                    'subject': subject,
                    'date': date,
                    'body': body,
                    'session_id': global_session_id,
                    "attachments": filtered_attaacthments(attachments)
                })
                print("Assigned email to agent:", agent_idl)
                break  # Exit the loop after assigning the email
            else:
                print("No matched agent available. Retrying in 15 seconds...")
                await asyncio.sleep(15)  # Wait for 15 seconds before retrying

    conn.commit()
    conn.close()

   
def apply_routing(email, routing_group, cursor):
    """Fetches routing rules and applies them to the email."""
 
    # Example rule structure (adjust for your needs):
    sample_rule = {
        'routing_group': 'Tier1Support',
        'criteria': {'subject_contains': 'refund', 'sender_domain': 'angrycustomers.com'},
        'priority': 10,
        'target_agent': 'jane.doe@company.com'
    }
 
    # 1. Fetch relevant routing rules
    rules_query = "SELECT criteria, priority, target_agent, target_queue FROM routing_rules WHERE routing_group = %s"
    cursor.execute(rules_query, (routing_group,))
    rules = cursor.fetchall()
 
    # 2. Implement rule matching logic (You'll need to write this based on your criteria)
    for rule in rules:
        if match_email_to_criteria(email, rule['criteria']):  
            # 3. Update email in the database
            update_query = """
                UPDATE emails
                SET status='assigned', assigned_agent=%s, target_queue=%s
                WHERE message_id=%s
            """
            cursor.execute(update_query, (rule['target_agent'], rule['target_queue'], email['Message-ID']))
            break  # Assuming you apply only the first matching rule
 
 
def match_email_to_criteria(email, criteria):
    # TODO: Implement your logic to check if 'email' matches the 'criteria'
    # Example:
    if criteria.get('subject_contains'):
        if criteria['subject_contains'].lower() not in email['Subject'].lower():
            return False  
 
    # ... Add more checks for other criteria types ...
    return True  # If all criteria match
 
# --------------------------------- Sending Emails -----------------------------------
# def extract_images_and_replace_with_cid(body):
#     img_pattern = re.compile(r'\[Image: (data:image/\w+;base64,([a-zA-Z0-9+/=]+))\]')
#     attachments = []
#     cid_map = {}

#     def replace_with_cid(match):
#         img_data = match.group(1)
#         base64_data = match.group(2)
#         cid = f'image{uuid4()}@example.com'
#         cid_map[img_data] = cid


#         attachments.append({
#             'cid': cid,
#             'data': base64.b64decode(base64_data),
#             'maintype': img_data.split(';')[0].split(':')[1],
#             'subtype': img_data.split(';')[0].split('/')[1],
#             'filename': f'image{uuid4()}.{img_data.split(";")[0].split("/")[1]}'
#         })

#         return f'<img src="cid:{cid}"/>'
#     new_body = img_pattern.sub(replace_with_cid, body)
#     return new_body, attachments


# Function to extract images and replace with CID
# def get_base64_image_from_url(image_url: str) -> str:
#     try:
#         response = requests.get(image_url)
#         response.raise_for_status()  # Ensure we notice bad responses
#         image_data = response.content
#         base64_encoded = base64.b64encode(image_data).decode('utf-8')
#         # print("base64code fo the thins when getbase64 is excuted",base64_encoded)
#         return f"data:image/png;base64,{base64_encoded}"
#     except Exception as e:
#         print(f"Error fetching image from URL {image_url}: {e}")
#         return image_url  # Return the original URL if there is an error
def get_base64_file_from_url(url):
    response = requests.get(url)
    file_content = response.content
    mime_type = response.headers['Content-Type']
    base64_str = base64.b64encode(file_content).decode('utf-8')
    return f'data:{mime_type};base64,{base64_str}'
def convert_images_to_base64(text: str) -> str:
    def replace_url_with_base64(match, type):
        url = match.group(1)
        if url.startswith('data:'):
            return url  # It's already a base64 string, return as is
        else:
            return get_base64_file_from_url(url)

    # Regular expression to find URLs in the text that are not already base64 images
    image_url_pattern = re.compile(r'\[Image: (http[^\]]+)\]')
    file_url_pattern = re.compile(r'\[File:Name:[^\]]+, URL: (http[^\]]+)\]')

    # Substitute image URLs with their base64 equivalents
    result_text = image_url_pattern.sub(lambda match: f"[Image: {replace_url_with_base64(match, 'image')}]", text)
    
    # Substitute file URLs with their base64 equivalents
    result_text = file_url_pattern.sub(lambda match: f"[File:Name:{match.group(0).split(',')[0].split(':')[2]}, URL: {replace_url_with_base64(match, 'file')}]", result_text)
    print("files changes into the values of text")
    return result_text
# def extract_images_and_replace_with_cid(body):
#     img_pattern = re.compile(r'\[Image: (data:image/\w+;base64,([a-zA-Z0-9+/=]+))\]')
#     attachments = []
#     cid_map = {}

#     def replace_with_cid(match):
#         img_data = match.group(1)
#         base64_data = match.group(2)
#         cid = f'image{uuid4()}@example.com'
#         cid_map[img_data] = cid

#         attachments.append({
#             'cid': cid,
#             'data': base64.b64decode(base64_data),
#             'maintype': img_data.split(';')[0].split(':')[1],
#             'subtype': img_data.split(';')[0].split('/')[1],
#             'filename': f'image{uuid4()}.{img_data.split(";")[0].split("/")[1]}'
#         })

#         return f'<img src="cid:{cid}"/>'
    
#     new_body = img_pattern.sub(replace_with_cid, body)
#     return new_body, attachments
# 
def extract_images_and_replace_with_cid(body):
    img_pattern = re.compile(r'\[Image: (data:image/\w+;base64,([a-zA-Z0-9+/=]+))\]')
   
    file_pattern = re.compile(r"\[File:Name:(.*?), URL:\s*data:(.*?);base64,([a-zA-Z0-9+/=]+)\]")
    outside_link_pattern = re.compile(r'\[OutsideLink: (https?://\S+)]')
    attachments = []
    cid_map = {}

    def replace_with_cid(match):
        try:
            img_data = match.group(1)
            base64_data = match.group(2)
            cid = f'image-{uuid4()}@example.com'
            cid_map[img_data] = cid

            attachments.append({
                'cid': cid,
                'data': base64.b64decode(base64_data),
                'maintype': img_data.split(';')[0].split(':')[1],
                'subtype': img_data.split(';')[0].split('/')[1],
                'filename': f'image-{uuid4()}.{img_data.split(";")[0].split("/")[1]}'
            })

            return f'<img src="cid:{cid}" alt="image"/>'
        except Exception as e:
            print(f"Error processing image: {e}")
            return match.group(0)  # Return the original match in case of error
    
    def replace_with_cid_file(match):
        print("matchesfrom the matches", match)
        try:
            file_names = match.group(1)
            print("file with in the match group",file_names)
            file_type = match.group(2)
            base64_data = match.group(3)
            cid = f'file-{uuid4()}@example.com'
            cid_map[file_names] = cid

            # Extract file extension
            file_extension = file_type.split('/')[1].split(';')[0]

            # Set default maintype and subtype
            maintype, subtype = 'application', 'octet-stream'

            # Update maintype and subtype based on file extension
            if file_extension.lower() == 'pdf':
                maintype, subtype = 'application', 'pdf'
            elif file_extension.lower() == 'xlsx':
                maintype, subtype = 'application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            elif file_extension.lower() == 'txt':
                print("entered text")
                maintype, subtype = 'application', 'vnd.oasis.opendocument.text'
            elif file_extension.lower() == 'txt':
                print("enetered text/plain")
                maintype, subtype = 'application', 'text/plain'
            elif file_extension.lower() == 'zip':
                maintype, subtype = 'application', 'zip'

            file_name = f'{uuid4()}.{file_extension}'

            attachments.append({
                'cid': cid,
                'data': base64.b64decode(base64_data),
                'maintype': maintype,
                'subtype': subtype,
                'filename': file_names
            })

            return f'<a href="cid:{cid}"></a>'
        except Exception as e:
            print(f"Error processing file: {e}")
            return match.group(0)   # Return the original match in case of error
    def replace_with_anchor(match):
        try:
            url = match.group(1)
            return f'<a href="{url}">{url}</a>'
        except Exception as e:
            print(f"Error processing outside link: {e}")
            return match.group(0) 
    try:
        new_body = img_pattern.sub(replace_with_cid, body)
        new_body = file_pattern.sub(replace_with_cid_file, new_body)
        new_body = outside_link_pattern.sub(replace_with_anchor, new_body)
        # Convert newline characters to <br> tags to preserve formatting
        new_body = new_body.replace('\n', '<br>')
    except Exception as e:
        print(f"Error processing body: {e}")
        return body, []

    return new_body, attachments

def send_email(item):
    conn = connect_to_database()  # Assuming you have this function defined
    cursor = conn.cursor()
    print("we are entering to the send email method")
    # Fetch SMTP server details from account_configurations
    smtp_config_query = "SELECT smtp_server, smtp_port FROM account_configurations WHERE username = %s"    
    cursor.execute(smtp_config_query, (mail_username,))
    result = cursor.fetchone()
 
    if not result:
        print("Error: Could not find SMTP configuration for this user.")
        return  # Exit the function if no configuration is found
 
    smtp_server, smtp_port = result
 
    sender = mail_username # Assuming you want to send from the logged-in account
    print("before sending to the body iam getting item body =====>",item.body)
    converted_text = convert_images_to_base64(item.body)
    # print("Converted text:", converted_text)


    msg = EmailMessage()
    msg['Subject'] = item.subject
    msg['From'] = sender
    msg['To'] = item.to_email
    msg['Date'] = item.date
    msg['Cc']=item.cc
    # msg.set_content(item.body)
    new_body, attachments = extract_images_and_replace_with_cid(converted_text)
    # print("New body:", new_body)
    # print("Attachments:", attachments)
    # msg.set_content(new_body)
    msg.add_alternative(new_body, subtype='html')
    for attachment in attachments:
        msg.add_attachment(attachment['data'],
                           maintype=attachment['maintype'],
                           subtype=attachment['subtype'],
                           filename=attachment['filename'],
                           cid=attachment['cid'])
    # print("we can see the messages of what we send ====>===>", msg)
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            # server.set_debuglevel(1)  # Enable debug output
            print(f"Connecting to SMTP server {smtp_server} on port {smtp_port}")
            server.ehlo()
            server.starttls()
            print("Starting TLS")
            server.ehlo()  # Re-identify as an encrypted connection
            server.login(sender, mailbox_password)
            print("Logged in to SMTP server")
            server.send_message(msg)
            print("Email sent successfully!",msg)
    except Exception as e:
        print(f"Error sending email: {e}")
    conn.close()  # Close the database connection

def extract_original_recipients(email_message):
    """Extracts To, CC, and BCC recipients from the original email."""
    to_addrs = email_message.get_all('To', [])
    cc_addrs = email_message.get_all('Cc', [])
    # Note: BCC addresses are not accessible in the original email headers
    print("Extracts To, recipients from the original email",to_addrs)
    print("Extracts Cc, recipients from the original email",cc_addrs)
    all_recipients = email.utils.getaddresses(to_addrs + cc_addrs)
    return [email.utils.formataddr(addr) for addr in all_recipients]


def reply_all(email_message, reply_body):
    """Replies to all recipients of the original email with the new body."""
    conn = connect_to_database()
    cursor = conn.cursor()
    print("email_message ======> in the replu_all method",email_message['To'])
    # Fetch SMTP server details from account_configurations
    smtp_config_query = "SELECT smtp_server, smtp_port FROM account_configurations WHERE username = %s"
    cursor.execute(smtp_config_query, (mail_username,))
    result = cursor.fetchone()
    if not result:
        print("Error: Could not find SMTP configuration for this user.")
        return
    smtp_server, smtp_port = result

    original_sender = email.utils.parseaddr(email_message['From'])[1]
    original_recipients = extract_original_recipients(email_message)
    original_recipients.append(original_sender)  # Include the original sender
    converted_text = convert_images_to_base64(reply_body)
    print("orginal_sender the values", original_sender)
    print("original_recipients", original_recipients)
    msg = EmailMessage()
    msg['Subject'] = "Re: " + email_message['Subject']
    msg['From'] = mail_username
    msg['To'] = ", ".join(original_recipients)
    msg['Date'] = email.utils.formatdate(localtime=True)

    new_body, attachments = extract_images_and_replace_with_cid(converted_text)
    msg.add_alternative(new_body, subtype='html')

    for attachment in attachments:
        msg.add_attachment(
            attachment['data'],
            maintype=attachment['maintype'],
            subtype=attachment['subtype'],
            filename=attachment['filename'],
            cid=attachment['cid']
        )

    # Send the email
    try:
        # with smtplib.SMTP(smtp_server, smtp_port) as server:
        #     server.login(mail_username, mailbox_password)
        #     server.send_message(msg)
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            # server.set_debuglevel(1)  # Enable debug output
            print(f"Connecting to SMTP server {smtp_server} on port {smtp_port}")
            server.ehlo()
            server.starttls()
            print("Starting TLS when we doing reply all")
            server.ehlo()  # Re-identify as an encrypted connection
            server.login(mail_username, mailbox_password)
            print("Logged in to SMTP server when we doing reply all")
            server.send_message(msg)
            
        print("Reply All email sent successfully.")
    except Exception as e:
        print(f"Failed to send Reply All email: {e}")
def reply_all_internal(item):
    try:
        mailbox = connect_to_mailbox("gmail", mail_username, mailbox_password)
        if mailbox:
            mailbox.select("INBOX")
            result, data = mailbox.search(None, "ALL")
            if result == 'OK' and data[0]:
                email_id = data[0].split()[-1]  # Get the latest email
                result, email_data = mailbox.fetch(email_id, '(RFC822)')
                email_message = email.message_from_bytes(email_data[0][1])
                print("data in reply all email_data",email_data)
                print("email_message['To'] ====> in reply_all for loop", email_message['To'])
                print("message before sending reply all",email_message)
                print("message before sending reply all",item.body)
                reply_all(email_message, item.body)
            else:
                raise HTTPException(status_code=404, detail="Original email not found")
    
    except Exception as e:
      raise HTTPException(status_code=500, detail=str(e))




def forward_email_internal(item):
    try:
        mailbox = connect_to_mailbox("gmail", mail_username, mailbox_password)
        if mailbox:
            mailbox.select("INBOX")
            result, data = mailbox.search(None, "ALL")
            print("data in farword",data)
            if result == 'OK' and data:
                email_id = data[0].split()[-1]  # Get the latest email
                result, email_data = mailbox.fetch(email_id, '(RFC822)')
                if result == 'OK':
                    raw_email = email_data[0][1]
                    email_message = email.message_from_bytes(raw_email)
                    
                    print("before farwarding email message",email_message)
                    forward(email_message, item.body, item.forward_to)
                else:
                    raise HTTPException(status_code=404, detail="Failed to fetch the email")
            else:
                raise HTTPException(status_code=404, detail="Original email not found")
        else:
            raise HTTPException(status_code=500, detail="Failed to connect to mailbox")
    except HTTPException as he:
        raise he  # Re-raise HTTPExceptions as they are
    except Exception as e:
        print("We are facing an error in the forward_email_internal method:", e)
        raise HTTPException(status_code=500, detail=str(e))
    

def forward(email_message, forward_body, forward_to):
    conn = connect_to_database()
    cursor = conn.cursor()

    try:
        smtp_config_query = "SELECT smtp_server, smtp_port FROM account_configurations WHERE username = %s"
        cursor.execute(smtp_config_query, (mail_username,))
        result = cursor.fetchone()
        if not result:
            raise Exception("Error: Could not find SMTP configuration for this user.")
        smtp_server, smtp_port = result

        msg = EmailMessage()
        msg['Subject'] = "Fwd: " + email_message['Subject']
        msg['From'] = mail_username
        msg['To'] = ", ".join(forward_to)
        msg['Date'] = email.utils.formatdate(localtime=True)
        
        original_body = email_message.get_payload()
        
        print("")
        if isinstance(original_body, list):
            original_body = original_body[0].get_payload()
        full_body = f"{forward_body}{original_body}"
        # msg.set_content(full_body)
        converted_text = convert_images_to_base64(full_body)
        new_body, attachments = extract_images_and_replace_with_cid(converted_text)
    # print("New body:", new_body)
    # print("Attachments:", attachments)
    # msg.set_content(new_body)
        msg.add_alternative(new_body, subtype='html')
        for attachment in attachments:
         msg.add_attachment(attachment['data'],
                           maintype=attachment['maintype'],
                           subtype=attachment['subtype'],
                           filename=attachment['filename'],
                           cid=attachment['cid'])
        print("message in forward ")
        storefarwardmail(msg)
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()  # Re-identify as an encrypted connection
            server.login(mail_username, mailbox_password)
            server.send_message(msg)
        print("Email forwarded successfully.")
    except Exception as e:
        raise Exception(f"Failed to forward email: {e}")
    finally:
        cursor.close()
        conn.close()
# ------------------------ Main Program ------------------------------
 
def fetch_mailbox_configs():
    """Retrieves mailbox configurations from the database."""
    conn = connect_to_database()
    cursor = conn.cursor()
 
    query = "SELECT account_type, username, password, imap_server, imap_port, imap_use_ssl FROM account_configurations"
    cursor.execute(query)
    mailbox_configs = cursor.fetchall()
    conn.close()
    return mailbox_configs
async def polling_loop():
    global polling_active
    while polling_active:
        mailbox_configs = fetch_mailbox_configs()
        if not mailbox_configs:
            print("Error: No mailbox configurations found in the database.")
        else:
            for config in mailbox_configs:
                account_type, username, password, imap_server, imap_port, imap_use_ssl = config
                try:
                    mailbox = connect_to_mailbox(account_type, username, password)
                    if mailbox:
                        await check_new_emails(mailbox)
                        print(f"Checked for new emails for: {username}")
                except Exception as e:
                    print(f"Error processing mailbox for {username}: {e}")
        print("Completed one polling cycle...")
        time.sleep(10)

#-----------------------

def storefarwardmail(email):
    print("store email",email)
    conn = connect_to_database()
    cursor = conn.cursor()

    try:
        account_query = "SELECT id, routing_group FROM account_configurations WHERE username = 'itzenius@gmail.com'"
        cursor.execute(account_query)
        result = cursor.fetchone()
        account_id, routing_group = result if result else (None, None)
        print("account_id ,routing_group",account_id,routing_group)

        sender_email = extract_email_addresses(email.sender)
        recipient_emails = extract_email_addresses(email.recipient)
        print("sender and receiver is",sender_email,recipient_emails)
        print("email object is",email.cc,email.to_email,email.recipient)
       
        exists=True
        insert_query = """
                INSERT INTO emails (account_id, message_id, session_id, direction, sender, recipient, cc_emails, subject, timestamp, body, attachments)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        cursor.execute(insert_query, (
                account_id, email.message_id, email.session_id, 'replyall', email.sender, 
                json.dumps(email.recipient), json.dumps(email.cc), email.subject, 
                email.date, email.body, json.dumps(email.attachments)
            ))
        message = "Email inserted successfully"
       
        print("out side if else")

        conn.commit()
        return {"message": message}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error inserting/updating email in database: {str(e)}")

    finally:
        conn.close()


#rejected mails

async def fetch_agents1(api_url: str):
    async with ClientSession() as session:
        try:
            async with session.get(api_url) as response:
                response.raise_for_status()
                content = await response.json()
                return content
        except ClientError as e:
            print(f"Request failed: {e}")
            return None

@app.get("/process-rejected-emails")
async def process_rejected_emails():
    conn = await connect_to_database1()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        rows = await conn.fetch("SELECT * FROM rejected_emails")
        print(f"Raw data from PostgreSQL: {len(rows)} rows found")

        for row in rows:
            sender = row[4]
            received_info = row[1]
            recipient = row[5]
            to_email = row[5]
            cc_email = row[6]
            subject = row[7]
            date = row[8].isoformat() if isinstance(row[8], datetime) else str(row[8])
            body = row[9]
            rejected_session_id = row[2]
            originalattachments = row[10]
            attachments = json.loads(originalattachments.decode('utf-8'))
            
            print(f"Processing rejected email for session_id: {rejected_session_id}")

            # Prepare message for agent assignment
            message = {
                "queues": "technicalsupportqueue@1",
                "skills": "networking_skill",
            }

            # Fetch agents from API
            api_url = 'http://127.0.0.1:8000/agents'
            while True:
                agents_data = await fetch_agents1(api_url)
                if agents_data is None:
                    raise HTTPException(status_code=500, detail="Failed to fetch agents data")

                # Update agents data with additional info from cache
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

                # Find a matched agent
                matched_agent = find_matched_ready_agent(agents_data, message)
                if matched_agent:
                    agent_idl = matched_agent['agent_id']
                    print(f"Matched agent: {agent_idl}")

                    # Emit the event for the new email
                    await sio_Server.emit('new_email', {
                        'sender': sender,
                        'message_id': received_info,
                        'recipient': recipient,
                        'to_email': to_email,
                        'cc_email': cc_email,
                        'subject': subject,
                        'date': date,
                        'body': body,
                        'session_id': rejected_session_id,
                        "attachments": filtered_attaacthments(attachments)
                    })

                    print(f"Assigned email with session_id {rejected_session_id} to agent {agent_idl}")

                    # After successful assignment, delete the processed row from rejected_emails table
                    print(f"Deleting row with session_id: {rejected_session_id}")
                    # await conn.execute("DELETE FROM rejected_emails WHERE session_id = $1", rejected_session_id)
                    print(f"Deleted row for session_id {rejected_session_id}")

                    break  # Exit the while loop after successful assignment

                else:
                    print(f"No matched agent available for session_id {rejected_session_id}. Waiting for 15 seconds...")
                    await asyncio.sleep(15)  # Wait before retrying

            print("Waiting for 15 seconds before processing the next row...")
            await asyncio.sleep(15)

    except Exception as e:
        print(f"Error fetching or processing data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        await conn.close()

    return {"status": "Processing complete"}


# @app.get("/process-rejected-emails")
# async def process_rejected_emails():
#     conn = await connect_to_database1()
#     if conn is None:
#         raise HTTPException(status_code=500, detail="Database connection failed")

#     try:
#         rows = await conn.fetch("SELECT * FROM rejected_emails")
#         print(f"Raw data from PostgreSQL: {len(rows)} rows found")

#         for row in rows:
#             sender = row[4]
#             received_info = row[1]
#             recipient = row[5]
#             to_email = row[5]
#             cc_email = row[6]
#             subject = row[7]
#             date = row[8].isoformat() if isinstance(row[8], datetime) else str(row[8])
#             body = row[9]
#             rejected_session_id = row[2]
#             originalattachments = row[10]
#             attachments = json.loads(originalattachments.decode('utf-8'))
            
#             print(f"Processing rejected email for session_id: {rejected_session_id}")

#             # Prepare message for agent assignment
#             message = {
#                 "queues": "technicalsupportqueue@1",
#                 "skills": "networking_skill",
#             }

#             # Fetch agents from API
#             api_url = 'http://127.0.0.1:8000/agents'
#             agents_data = await fetch_agents1(api_url)
#             if agents_data is None:
#                 raise HTTPException(status_code=500, detail="Failed to fetch agents data")

#             # Update agents data with additional info from cache
#             for agent in fetch_detail_cache:
#                 agent_key = f"agent:{agent['agent_id']}"
#                 if agent_key in agents_data and agents_data[agent_key]['agent_id'] == str(agent['agent_id']):
#                     agents_data[agent_key].update({
#                         'queues': agent['queues'],
#                         'skills': agent['skills'],
#                         'max_chat_concurrent_interactions': agent['max_chat_concurrent_interactions'],
#                         'max_call_concurrent_interactions': agent['max_call_concurrent_interactions'],
#                         'max_email_concurrent_interactions': agent['max_email_concurrent_interactions']
#                     })

#             # Find a matched agent
#             matched_agent = find_matched_ready_agent(agents_data, message)
#             if matched_agent:
#                 agent_idl = matched_agent['agent_id']
#                 print(f"Matched agent: {agent_idl}")

#                 # Emit the event for the new email
#                 await sio_Server.emit('new_email', {
#                     'sender': sender,
#                     'message_id': received_info,
#                     'recipient': recipient,
#                     'to_email': to_email,
#                     'cc_email': cc_email,
#                     'subject': subject,
#                     'date': date,
#                     'body': body,
#                     'session_id': rejected_session_id,
#                     "attachments": filtered_attaacthments(attachments)
#                 })

#                 print(f"Assigned email with session_id {rejected_session_id} to agent {agent_idl}")

#                 # After successful assignment, delete the processed row from rejected_emails table
#                 print(f"Deleting row with session_id: {rejected_session_id}")
#                 # await conn.execute("DELETE FROM rejected_emails WHERE session_id = $1", rejected_session_id)
#                 print(f"Deleted row for session_id {rejected_session_id}")
#             else:
#                 print(f"No matched agent available for session_id {rejected_session_id}")

            
#             print("Waiting for 15 seconds before processing the next row...")
#             await asyncio.sleep(15)

#     except Exception as e:
#         print(f"Error fetching or processing data: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

#     finally:
#         await conn.close()

#     return {"status": "Processing complete"}


# commeted below code dont remove


@app.get("/gmail")
async def fetch_all_emails():
    conn = connect_to_database()
    cursor = conn.cursor()
    try:
        fetch_query = """
        SELECT * FROM emails ORDER BY TIMESTAMP DESC
        """
        cursor.execute(fetch_query)
        emails = cursor.fetchall()
        
        def parse_json_field(field):
            if isinstance(field, memoryview):
                return json.loads(field.tobytes().decode('utf-8'))
            elif isinstance(field, str):
                return json.loads(field)
            return None
        
        email_list = []
        for email in emails:
            email_data = {
                "account_id": email[0],
                "message_id": email[1],
                "session_id": email[2],
                "direction": email[3],
                "sender": email[4],
                "recipient": parse_json_field(email[5]),  # Handle both memoryview and string
                "cc_emails": parse_json_field(email[6]),  # Handle both memoryview and string
                "subject": email[7],
                "timestamp": email[8],
                "body": email[9],
                "attachments": parse_json_field(email[10])  # Handle both memoryview and string
            }
            email_list.append(email_data)
        
        return email_list
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching emails from database: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()

# @app.get("/gmail")
# async def fetch_all_emails():
#     conn = connect_to_database()
#     cursor = conn.cursor()
#     try:
#         fetch_query = """
#         SELECT * FROM emails ORDER BY TIMESTAMP DESC
#         """
#         cursor.execute(fetch_query)
#         emails = cursor.fetchall()
        
#         def parse_json_field(field):
#             if isinstance(field, memoryview):
#                 return json.loads(field.tobytes().decode('utf-8'))
#             elif isinstance(field, str):
#                 return json.loads(field)
#             return None
        
#         email_list = []
#         for email in emails:
#             email_data = {
#                 "account_id": email[0],
#                 "message_id": email[1],
#                 "session_id": email[2],
#                 "direction": email[3],
#                 "sender": email[4],
#                 "recipient": parse_json_field(email[5]),  # Handle both memoryview and string
#                 "cc_emails": parse_json_field(email[6]),  # Handle both memoryview and string
#                 "subject": email[7],
#                 "timestamp": email[8],
#                 "body": email[9],
#                 "attachments": parse_json_field(email[10])  # Handle both memoryview and string
#             }
#             email_list.append(email_data)
        
#         return email_list
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error fetching emails from database: {str(e)}")
    
#     finally:
#         cursor.close()
#         conn.close()


#-----------------------

def start_polling():
    # polling_loop()
    fetch_queue_skills()
    asyncio.run(polling_loop())

def start_fastapi():
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.submit(start_polling)
        executor.submit(start_fastapi)