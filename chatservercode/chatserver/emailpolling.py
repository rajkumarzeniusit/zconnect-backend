import asyncio
import binascii
import copy
from email import policy
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.parser import BytesParser
import asyncpg
from aiohttp import ClientSession, ClientError
from dotenv import load_dotenv
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
from flask import jsonify
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
from psycopg2.extras import RealDictCursor

from serverconnection import FreeSWITCHClient
# from sockets import sio_app
# from sockets import sio_Server
# sio = socketio.Client()

# Initialize the AsyncServer with logger
sio_Server = socketio.AsyncServer(
    async_mode="asgi",
    logger=True,
    cors_allowed_origins=
   ["http://localhost:3000","http://localhost:3001"]
)

# Initialize ASGIApp with correct parameters
sio_app = socketio.ASGIApp(
    socketio_server=sio_Server,
    socketio_path=""
)
message = {}
fetch_detail_cache = None
skills_match=None
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
    direction:str = "outgoing"
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
    direction:str = "outgoing"

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
    direction:str = "outgoing"

# class AgentState(BaseModel):
#     agentId: str
#     agentState:str
#     dateTime: str
class store_Email(BaseModel):
    message_id: str
    session_id: str
    sender: str
    recipient: Any
    cc: Optional[Any] = None
    subject: str
    date: str
    body: str
    attachments: List[dict]
    direction: str
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
    direction:str = "incoming"
    

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
    direction:str = "incoming"

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
load_dotenv()
agents_url=os.getenv("API_URL")
skills_url=os.getenv("API_SKILLS")
agent_skills=os.getenv("API_AGENT_SKILLS")

redis_host=os.getenv("REDIS_HOST")
redis_port=os.getenv("REDIS_PORT")
redis_db=os.getenv("REDIS_DB")
try:
    redis_client = redis.StrictRedis(redis_host,redis_port, db=redis_db, decode_responses=True)
    print("redis data base connected susscefully")
except redis.RedisError as e:
    raise HTTPException(status_code=500, detail=f"Redis connection error: {str(e)}")


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
        send_far_email(item)
        #send_email(item)
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
# @app.get("/agents_details")
# async def get_all_agent_details():
#      return agent_details

########################################################################

@app.get("/skills")
async def fetch_all_emails():
    conn = connect_to_database()
    cursor = conn.cursor(cursor_factory=RealDictCursor)  # Use RealDictCursor for dict-like rows
    try:
        fetch_query = """
        SELECT * FROM agent_interactions
        """
        cursor.execute(fetch_query)
        emails = cursor.fetchall()
        
        return emails  # RealDictCursor returns rows as dictionaries, which FastAPI can auto-convert to JSON
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching emails from database: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()

@app.get("/agent_skills")
async def fetch_all_emails():
    conn = connect_to_database()
    cursor = conn.cursor(cursor_factory=RealDictCursor)  # Use RealDictCursor for dict-like rows
    try:
        fetch_query = """
        SELECT * FROM agent_skills
        """
        cursor.execute(fetch_query)
        emails = cursor.fetchall()
        
        return emails  # RealDictCursor returns rows as dictionaries, which FastAPI can auto-convert to JSON
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching emails from database: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()

########################################################################




@app.post("/store_rejected_emails")
async def store_rejected_emails(request: Rejected_Email):
    print("entered rejected mail")
    data = request.json()
    print("data going into rejected mail",data)

    # Get the current value from Redis
    existing_data = redis_client.get("rejected_mail")
    print("key is there or not",existing_data)
    
    if existing_data:
        # Decode the existing data
        existing_data = json.loads(existing_data)
    else:
        # Initialize as an empty list if no data exists
        existing_data = []

    print("fetching existing data",existing_data)

    # Append new rejected email to the existing data
    existing_data.append(data)
    print("fetching after adding data",existing_data)

    # Store updated data back in Redis
    redis_client.set("rejected_mail", json.dumps(existing_data))

    return {"status": "success", "message": "Rejected email stored successfully."}


#in redis send rejected mail and delete item
async def process_rejected_emails():
    print("entered")

    while True:
        # Fetch the data from Redis
        existing_data = redis_client.get("rejected_mail")
        print("existing data", existing_data)
        
        if existing_data:
            # Decode the existing data
            existing_data = json.loads(existing_data)
        else:
            existing_data = []

        # Ensure we have a list to iterate over
        if isinstance(existing_data, list) and existing_data:
            index = 0
            while index < len(existing_data):
                item = existing_data[index]
                
                # Parse each item
                try:
                    parsed_item = json.loads(item)
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON item: {item}")
                    index += 1
                    continue

                print("Printing item:", parsed_item)

                # Extract fields
                message_id = parsed_item.get('message_id')
                sender = parsed_item.get('sender')
                recipient = parsed_item.get('recipient')
                to_email = parsed_item.get('recipient')
                cc_email = parsed_item.get('cc_email')
                subject = parsed_item.get('subject')
                date = parsed_item.get('date')
                body = parsed_item.get('body')
                rejected_session_id = parsed_item.get('session_id')
                attachments = parsed_item.get('attachments')

                print(f"Processing rejected email for session_id: {rejected_session_id}")

                # Prepare message for agent assignment
                message = {
                    "queues": "technicalsupportqueue@1",
                    "skills": "networking_skill",
                }

                # Fetch agents from API
                api_url = agents_url
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
                            'message_id': message_id,
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

                        # Remove the processed item from the local list
                        existing_data.pop(index)
                        
                        # Update Redis with the new list
                        redis_client.set("rejected_mail", json.dumps(existing_data))

                        print(f"Deleted item with session_id {rejected_session_id} from Redis")

                        break  # Exit the while loop after successful assignment

                    else:
                        print(f"No matched agent available for session_id {rejected_session_id}. Waiting for 15 seconds...")
                        await asyncio.sleep(15)  # Wait before retrying

                print("Waiting for 15 seconds before processing the next row...")
                await asyncio.sleep(30)
                
        else:
            print("No data found in Redis. Waiting for 15 seconds before checking again.")
            await asyncio.sleep(15)  # Wait before checking again



# @app.get("/process")
# async def process_rejected_emails():
#     print("entered")
#     existing_data = redis_client.get("rejected_mail")
#     print("existing data", existing_data)
    
#     try:
#         if existing_data:
#             # Decode the existing data
#             existing_data = json.loads(existing_data)
#         else:
#             existing_data = []

#         # Ensure we have a list to iterate over
#         if isinstance(existing_data, list):
#             for item in existing_data:
#                 # Parse each item
#                 parsed_item = json.loads(item)
#                 print("Printing item:", parsed_item)

#                 # Extract fields
#                 received_info=None
#                 sender = parsed_item.get('sender')
#                 recipient = parsed_item.get('recipient')
#                 to_email = parsed_item.get('recipient')
#                 cc_email = parsed_item.get('cc_email')
#                 subject = parsed_item.get('subject')
#                 date = parsed_item.get('date')
#                 body = parsed_item.get('body')
#                 rejected_session_id = parsed_item.get('session_id')
#                 attachments = parsed_item.get('attachments')
                
#                 print(f"Processing rejected email for session_id: {rejected_session_id}")

#                 # Prepare message for agent assignment
#                 message = {
#                     "queues": "technicalsupportqueue@1",
#                     "skills": "networking_skill",
#                 }

#                 # Fetch agents from API
#                 api_url = agents_url
#                 while True:
#                     agents_data = await fetch_agents1(api_url)
#                     if agents_data is None:
#                         raise HTTPException(status_code=500, detail="Failed to fetch agents data")

#                     # Update agents data with additional info from cache
#                     for agent in fetch_detail_cache:
#                         agent_key = f"agent:{agent['agent_id']}"
#                         if agent_key in agents_data and agents_data[agent_key]['agent_id'] == str(agent['agent_id']):
#                             agents_data[agent_key].update({
#                                 'queues': agent['queues'],
#                                 'skills': agent['skills'],
#                                 'max_chat_concurrent_interactions': agent['max_chat_concurrent_interactions'],
#                                 'max_call_concurrent_interactions': agent['max_call_concurrent_interactions'],
#                                 'max_email_concurrent_interactions': agent['max_email_concurrent_interactions']
#                             })

#                     # Find a matched agent
#                     matched_agent = find_matched_ready_agent(agents_data, message)
#                     if matched_agent:
#                         agent_idl = matched_agent['agent_id']
#                         print(f"Matched agent: {agent_idl}")

#                         # Emit the event for the new email
#                         await sio_Server.emit('new_email', {
#                             'sender': sender,
#                             'message_id': received_info,
#                             'recipient': recipient,
#                             'to_email': to_email,
#                             'cc_email': cc_email,
#                             'subject': subject,
#                             'date': date,
#                             'body': body,
#                             'session_id': rejected_session_id,
#                             "attachments": filtered_attaacthments(attachments)
#                         })

#                         print(f"Assigned email with session_id {rejected_session_id} to agent {agent_idl}")

#                         # After successful assignment, delete the processed row from rejected_emails table
#                         print(f"Deleting row with session_id: {rejected_session_id}")
#                         print(f"Deleted row for session_id {rejected_session_id}")

#                         break  # Exit the while loop after successful assignment

#                     else:
#                         print(f"No matched agent available for session_id {rejected_session_id}. Waiting for 15 seconds...")
#                         await asyncio.sleep(15)  # Wait before retrying

#                 print("Waiting for 15 seconds before processing the next row...")
#                 await asyncio.sleep(15)

#         else:
#             print("No valid data found in Redis.")

#     except Exception as e:
#         print(f"Error fetching or processing data: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

#     finally:
#         print("Processing complete")

#     return {"status": "Processing complete"}


  



# @app.post("/store_rejected_emails")
# async def receive_rejected_email(email: Rejected_Email):
#     print("store rejected email", email)
#     print("store rejected email", email.session_id)
#     conn = connect_to_database()
#     cursor = conn.cursor()

#     try:
#         account_query = "SELECT id, routing_group FROM account_configurations WHERE username = 'itzenius@gmail.com'"
#         cursor.execute(account_query)
#         result = cursor.fetchone()
#         account_id, routing_group = result if result else (None, None)

#         sender_email = extract_email_addresses(email.sender)
#         recipient_emails = extract_email_addresses(email.recipient)
#         print("sender and receiver", sender_email, recipient_emails)

#         # Insert a new rejected email
#         insert_query = """
#             INSERT INTO rejected_emails (account_id, message_id, session_id, direction, sender, recipient, cc_emails, subject, timestamp, body, attachments)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#         """
#         cursor.execute(insert_query, (
#             account_id, email.message_id, email.session_id, 'rejected', email.sender,
#             json.dumps(email.recipient), json.dumps(email.cc_email), email.subject,
#             email.date, email.body, json.dumps(email.attachments)
#         ))

#         conn.commit()
#         return {"message": "Rejected email inserted successfully"}

#     except Exception as e:
#         conn.rollback()
#         raise HTTPException(status_code=500, detail=f"Error inserting rejected email in database: {str(e)}")

#     finally:
#         conn.close()

def extract_email_addresses(text):
    # Regular expression to find email addresses
    email_regex = r'[\w\.-]+@[\w\.-]+'
    matches = re.findall(email_regex, text)
    return matches[0] if matches else None

#in redis store mails in redis
@app.post("/store_emails")
async def store_emails(email:accept_Email):
    print("store mails for accept",email.body)
    #email.body = re.sub(r'\[(https?://[^\s]+)\]', r'\1', email.body)
    print("store mails for accept",email.body)
    data = email.json()
    #print("data going into accept mail",data)

    # Get the current value from Redis
    existing_data = redis_client.get("accepted_mail")
    #print("key is there or not",existing_data)
    
    if existing_data:
        # Decode the existing data
        existing_data = json.loads(existing_data)
    else:
        # Initialize as an empty list if no data exists
        existing_data = []

    #print("fetching existing data",existing_data)

    # Append new rejected email to the existing data
    existing_data.append(data)
    #print("fetching after adding data",existing_data)

    # Store updated data back in Redis
    redis_client.set("accepted_mail", json.dumps(existing_data))

    return {"status": "success", "message": "accepted stored successfully."}
@app.post("/store_emails_for_replyall")
async def store_emails(email: ReplyAllEmailObject):
    print("email object is",email)
    email.body= re.sub(r'\[OutsideLink:\s*(https?://[^\]]+)\]', r'\1', email.body)
    # if "[Image: data:image/png;base64" in email.body:
    # # Keep the prefix but remove the closing bracket
    #   email.body = email.body.replace("[Image: ", "[")
        # Check if the email body starts with "[Image:"
    # if email.body.startswith("[Image:"):
    #     # Remove the brackets and the "Image: " prefix
    #     email.body = email.body.strip("[]").replace("Image: ", "").strip()
    send_email(email)
    print("entered accept mail")
    data = email.json()
    print("email object is",email)

    # Get the current value from Redis
    existing_data = redis_client.get("accepted_mail")
    print("key is there or not",existing_data)
    
    if existing_data:
        # Decode the existing data
        existing_data = json.loads(existing_data)
    else:
        # Initialize as an empty list if no data exists
        existing_data = []

    print("fetching existing data",existing_data)

    # Append new rejected email to the existing data
    existing_data.append(data)
    print("fetching after adding data",existing_data)

    # Store updated data back in Redis
    redis_client.set("accepted_mail", json.dumps(existing_data))

    return {"status": "success", "message": "accepted stored successfully."}

@app.post("/store_emails_for_far")
async def store_emails(email:ForwardEmailObject):
    #send_email(email)
    email.body= re.sub(r'\[OutsideLink:\s*(https?://[^\]]+)\]', r'\1', email.body)
    send_far_email(email)
    print("entered accept mail")
    data = email.json()

    # Get the current value from Redis
    existing_data = redis_client.get("accepted_mail")
    print("key is there or not",existing_data)
    
    if existing_data:
        # Decode the existing data
        existing_data = json.loads(existing_data)
    else:
        # Initialize as an empty list if no data exists
        existing_data = []

    print("fetching existing data",existing_data)

    # Append new rejected email to the existing data
    existing_data.append(data)
    print("fetching after adding data",existing_data)

    # Store updated data back in Redis
    redis_client.set("accepted_mail", json.dumps(existing_data))

    return {"status": "success", "message": "accepted stored successfully."}

@app.post("/store_emails_for_reply")
async def store_emails(email:postEmailObject):
    #print("email object is",email)
    print("entered reply or send mail",email.body)
    email.body= re.sub(r'\[OutsideLink:\s*(https?://[^\]]+)\]', r'\1', email.body)
    send_email(email)
    
    data = email.json()
    #print("data going into accept mail",data)
    # data = json.loads(data)
    # # Extract the body
    # email_body = data['body']
    # print("body is",email_body)
    # if ']' in email_body:
    #     print("entered if")
    #     body_parts = email_body.split(']', 1)
    #     data['body'] = body_parts[1].strip()  # Content after ']'
    #     #data['attch'] = body_parts[0] + ']'  # Content before ']'
    # else:
    #     print("entered else")
    #     data['body'] = email_body  # If there's no ']', keep the original body
    #     data['attch'] = None  # Set attachment to None or an empty string if needed

    # print("Updated data:", data)

    # Get the current value from Redis
    existing_data = redis_client.get("accepted_mail")
    print("key is there or not",existing_data)
    
    if existing_data:
        # Decode the existing data
        existing_data = json.loads(existing_data)
    else:
        # Initialize as an empty list if no data exists
        existing_data = []

    print("fetching existing data",existing_data)

    # Append new rejected email to the existing data
    existing_data.append(data)
    print("fetching after adding data",existing_data)

    # Store updated data back in Redis
    redis_client.set("accepted_mail", json.dumps(existing_data))

    return {"status": "success", "message": "accepted stored successfully."}

@app.post("/store_emails_in_db")
async def receive_email(email:store_Email):
    print("store email",email)
    delete_email(email)
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
                account_id, email.message_id, email.session_id,email.direction, email.sender, 
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
    global skills_match
    print("started")
    #testurl='http://127.0.0.1:8000/agents_details'
    testurl=skills_url
    print("we are entering before fecth deatils =====>123456")
    fetch_detail=fetch_details(testurl)
    print("we are entering after fecth deatils")
    print("fetch_detail ====>:",fetch_detail)
    fetch_detail_cache=fetch_detail
    testskillsurl=agent_skills
    skills_match=fetch_details(testskillsurl)
    print("testing for skills from db",skills_match)
    for record in skills_match:
     record['queues'] = record['queues'][0] if record['queues'] else None  # Extract first element from 'queues'
     record['skills'] = record['skills'][0] if record['skills'] else None  # Extract first element from 'skills'

# Now printing without square brackets
    print("testing for skills from db", skills_match[0])
    
def Get_Matched_Available_Agent(message):
    print("matched method")
    api_url = agents_url
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
    #skills = message['skills']
    print("find_matched_ready_agent:", message)
   
    if 'rejectedMessage' in message and message['rejectedMessage']:
        print("Rejected message handling...")
        rejected_id = str(message['agent_id'])  # Ensure the rejected_id is a string
        ready_agents = [
            agent for agent in agents_data.values()
            if agent['current_state'] == 'Available' and
               any(q in queues for q in agent['queues']) and
               #any(s in skills for s in agent['skills']) and
               agent['agentId'] != rejected_id
        ]
    else:
        print("Regular message handling...")
        print("agents_daata_values",agents_data.values())
        ready_agents = [
            agent for agent in agents_data.values()
            if agent['current_state'] == 'Available' and
               any(q in queues for q in agent['queues']) #and
               #any(s in skills for s in agent['skills'])
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
    
# Load environment variables from .env file
load_dotenv()

# Get the database credentials from the environment variables
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
print("db pass isss",db_password,db_user,redis_host)
    
async def connect_to_database1():
    try:
        conn = await asyncpg.connect(
            database=db_name,#"zconnect",
            user=db_user,#"postgres",
            password=db_password,#"123456789",
            host=db_host,#"127.0.0.1",
            port=db_port#"9999"
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
          dbname=db_name,# "zconnect",
          user=db_user,#"postgres",
          password= db_password,#"123456789",
          host=db_host,# "127.0.0.1",
          port=db_port#"9999"
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
        print("message is")
        if email_message.is_multipart():
            for part in email_message.walk():
                try:
                    print("part for incomming is:",part)
                    content_type = part.get_content_type()
                    print("content for incomming is:",content_type)
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

def process_new_attachments(email_message, email_id):
    """Processes email attachments."""
    attachments = []
    try:
        print("message is")
        if email_message.is_multipart():
            for part in email_message.walk():
                try:
                    #print("part for incomming is:",part)
                    content_type = part.get_content_type()
                    #print("content for incomming is:",content_type)
                    if content_type in [
                        'application/octet-stream', 'image/jpeg', 'image/png', 'application/zip',
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        'application/x-zip-compressed', 'application/vnd.ms-excel', 'application/pdf',
                        'application/msword', 'application/docx', 'application/vnd.oasis.opendocument.text','text/plain','text/csv'
                    ]:
                        filepath = part.get_payload().replace('\r\n', '').replace('\n', '')
                        #part.get_payload()#save_attachment(part, email_id)
                        #print("file path is",filepath)
                        if content_type=="application/octet-stream":
                            content_type="text/csv"
                        filename=part.get_filename()
                        cid = part.get('Content-ID')
                        if cid:
                            cid = cid.strip('<>')
                        if filepath and filename!=None :
                            attachments.append({
                            'filepath': f'data:{content_type};base64,{filepath}',  # Encode as base64 string
                            'cid': cid,
                            'filename': filename
                            })
                        #print(f"Attachment saved: {filepath}")
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
            if not (attachment['filename'].lower().endswith(('.png')) or attachment['filename'].lower() == 'noname')#, '.jpg', '.jpeg'
        ]

        # Replace file path with the desired URL

        # Replace file path for .jpeg files or update SAVE_DIRECTORY paths
    for attachment in filtered_attachments:
        if attachment['filename'].lower().endswith('.jpeg'):
            # If the filepath is a base64-encoded string, update the mime type to `data:image/png`
            if attachment['filepath'].startswith('data:'):
                attachment['filepath'] = attachment['filepath'].replace('data:text/csv', 'data:image/png')
        else:
            # Replace SAVE_DIRECTORY with BASE_URL for regular file paths
            attachment['filepath'] = attachment['filepath'].replace(SAVE_DIRECTORY, BASE_URL)
            attachment['filepath'] = attachment['filepath'].replace('\\', '')  # Handle backslashes in file paths

    # for attachment in filtered_attachments:
    #     attachment['filepath'] = attachment['filepath'].replace(SAVE_DIRECTORY, BASE_URL)
    #     attachment['filepath'] = attachment['filepath'].replace('\\', '')
    print("Filtered and Updated Attachments:", filtered_attachments)
    #filtered_attachments = [attachment for attachment in filtered_attachments if attachment.get('cid') is None]
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
    print("body in updated", body)
    print("attachments in updated", attachments)
    for attachment in attachments:
        print("loooop")
        print("loop b in updated", body)
        cid = attachment['cid']
        filepath = attachment['filepath']
        # Extract the filename from the filepath
        filename = os.path.basename(filepath)
        #print("filename when we sending the data",filename)
        # Replace the local file path prefix with the base URL
        relative_filepath = filepath.replace(
            SAVE_DIRECTORY,
            BASE_URL
        )
        relative_filepath = relative_filepath.replace('\\', '')
        # print("relative_filepath in the email",relative_filepath)
        # Construct the URL
        url = f"{relative_filepath}"

        if f"cid:{cid}" in body:
            body = body.replace(f"cid:{cid}", url)
            print(f"Replaced CID:{cid} with {url}")
            # Move to the next attachment once updated
            continue

        if "[Embedded Image]" in body:
            body = body.replace("Embedded Image", filepath,1)
            print(f"Replaced 'Embedded Image' with {filepath}")
            # Move to the next attachment once updated
            continue

        if "[image: Embedded Image]" in body:
            body = body.replace("image: Embedded Image", filepath,1)
            print(f"Replaced 'image: image.png' with {filepath}")
            # Move to the next attachment once updated
            continue

 
        if "image: image.png" in body:
            body = body.replace("image: image.png", filepath,1)
            print(f"Replaced 'image: image.png' with {filepath}")
            # Move to the next attachment once updated
            continue
        

        
   


        # body = body.replace(f"cid:{cid}", url)
        # body=body.replace(f"image: image.png",filepath)
        # body=body.replace(f"Embedded Image",filepath)
        print("exiting",body)
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
def clean_email_body(body):
    if body is None:
        return ""
    # Split the body into lines
    lines = body.splitlines()
    
    # Iterate over each line and remove leading '>' and extra spaces
    cleaned_lines = []
    for line in lines:
        cleaned_line = line.lstrip('>').strip()  # Removes leading '>' and trims spaces
        cleaned_lines.append(cleaned_line)
    
    # Join the cleaned lines back into the final body
    cleaned_body = "\n".join(cleaned_lines)
    return cleaned_body

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
    #print("emails ids before entering for loop ===>", data[0].split())
    
    for email_id in data[0].split():
        result, email_data = mailbox.fetch(email_id, '(RFC822)')
        email_message = email.message_from_bytes(email_data[0][1])
        

        # Print all headers
        print("Email Headers:")
        for header, value in email_message.items():
            print(f"{header}: {value}")

        received_headers = email_message.get_all('Received', [])
        #print("received headers", received_headers)
        received_info = None
        if received_headers:
            for header in received_headers:
                match = re.search(r'from (.*?\.PROD\.OUTLOOK\.COM)', header)
                if match:
                    received_info = match.group(1)
                    break  # Stop after the first match
        #print("Received Header Info:", received_info)
        
        if received_info is None:
            messages_id = email.utils.parseaddr(email_message['Message-ID'])[1]
            received_info = messages_id

        # Process Attachments
        attachments = process_new_attachments(email_message, email_id)
        print("new attchments is Attachments:", attachments)

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
        in_reply_to = email_message['In-Reply-To']
        references = email_message['References']
        unique_id = email_message['X-Unique-ID']
        dynamicattachments=[{'filepath': 'data:text/csv;base64,TmFtZWQgQWdlbnRzDQoicHJhbW9kX2pvc2hpI2FjcXVlb25fY29tIg0KInNhaWt1bWFyX2ojYWNxdWVvbl9jb20i', 'cid': None, 'filename': 'download.csv'}]
        global_session_id = str(uuid.uuid4())

        body = None
        if email_message.is_multipart():
            print("part isssss",email_message)
            for part in email_message.walk():
                content_disposition = str(part.get("Content-Disposition"))
                content_type = part.get_content_type()
                charset=part.get_content_charset()
                print("charset is",charset)

                if content_type == 'text/plain' and charset== 'us-ascii' and "attachment" not in content_disposition:
                    print("***********************************************")
                    body = part.get_payload(decode=True).decode()
                    # print("body", body)
                    # print("attachments", attachments)
                    body = update_body_with_attachments(body, attachments)
                    #print("updated body with attachments", body)
                    break  # Stop after processing the first plain text body part
                elif content_type == 'text/plain' and charset== 'utf-8' and "attachment" not in content_disposition:
                    print("***********************************img***********************",content_type)
                    body = part.get_payload(decode=True).decode()
                    # print("body", body)
                    # print("attachments", attachments)
                    body = update_body_with_attachments(body, attachments)
                    #print("updated body with attachments", body)
                    break  # Stop after processing the first plain text body part
                
                elif content_type == 'text/plain' and charset== 'iso-8859-1' and "attachment" not in content_disposition:
                    print("***********************************img***********************",content_type)
                    body = part.get_payload(decode=True).decode()
                    # print("body", body)
                    # print("attachments", attachments)
                    body = update_body_with_attachments(body, attachments)
                    #print("updated body with attachments", body)
                    break  # Stop after processing the first plain text body part
                # elif content_type == 'text/plain' and charset== 'windows-1252' and "attachment" not in content_disposition:
                #     print("***********************************img***********************",content_type)
                #     body = part.get_payload(decode=True).decode()
                #     # print("body", body)
                #     # print("attachments", attachments)
                #     body = update_body_with_attachments(body, attachments)
                #     #print("updated body with attachments", body)
                #     break  # Stop after processing the first plain text body part


        # if email_message.is_multipart():
        #     print("part isssss", email_message)
        #     for part in email_message.walk():
        #         content_type = part.get_content_type()
        #         charset = part.get_content_charset()

        #         if content_type == 'text/plain' and (charset == 'us-ascii' or charset == 'utf-8') and "attachment" not in part.get("Content-Disposition"):
        #         # Process plain text body
        #             body = part.get_payload(decode=True).decode()
        #             # Replace image references with base64 data
        #             body = body.replace('[embedded image]', image_data)

        #         elif content_type.startswith('image/png'):
        #         # Process image attachment
        #             content_disposition = part.get("Content-Disposition")
        #             filename = None
        #             if content_disposition:
        #             # Extract filename from Content-Disposition header (optional)
        #                 filename_params = content_disposition.split(';')
        #                 for param in filename_params:
        #                     if param.strip().lower().startswith('filename='):
        #                         filename = param.strip().split('=')[1].strip('"')
                
        #         # Get the base64 encoded image data
        #             image_data = part.get_payload(decode=True)

        #         # ... (any other image processing)

        #         # Replace image references with base64 data in the body
        #             body = body.replace('[embedded image]', f'<img src="data:{content_type};base64,{image_data}" />')

        #             break  # Stop after processing the first image

        #     # Now, the body variable contains the text with embedded base64 image data
        #     print(body)

                    

        else:
            body = email_message.get_payload(decode=True).decode()

        body=clean_email_body(body)

        print("Final Body:", body)
        #print("new attchments is Attachments:", attachments)

        # Further processing...
        # message = {
        #     "queues": "technicalsupportqueue@1",
        #     "skills": "networking_skill",
        # }
        message = skills_match[0]

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

import re
import base64
import smtplib
from email.message import EmailMessage

# def replace_images_with_tags(body):
#     # Define a regex to match the base64 image pattern
#     pattern = r'\[Image: (data:image/[^;]+;base64,[^\]]+)\]'
    
#     # Function to replace matched pattern with <img> tag
#     def replace_with_img_tag(match):
#         base64_image = match.group(1)
#         return f'<img src="{base64_image}" alt="Embedded Image"/>'
    
#     # Replace all occurrences in the body
#     new_body = re.sub(pattern, replace_with_img_tag, body)
    
#     return new_body

# def send_email(item):
#     print("Entered send method", item)
#     conn = connect_to_database()  # Assuming you have this function defined
#     cursor = conn.cursor()
#     print("We are entering the send email method")
    
#     # Fetch SMTP server details from account_configurations
#     smtp_config_query = "SELECT smtp_server, smtp_port FROM account_configurations WHERE username = %s"
#     cursor.execute(smtp_config_query, (mail_username,))
#     result = cursor.fetchone()

#     if not result:
#         print("Error: Could not find SMTP configuration for this user.")
#         return  # Exit the function if no configuration is found

#     smtp_server, smtp_port = result

#     sender = mail_username  # Assuming you want to send from the logged-in account
    
#     # Replace images in the body dynamically with HTML img tags
#     updated_body = replace_images_with_tags(item.body)
    
#     msg = EmailMessage()
#     msg['Subject'] = item.subject
#     msg['From'] = sender
#     msg['To'] = item.to_email
#     msg['Date'] = item.date
#     msg['Cc'] = item.cc

#     # Set the email body as both plain text and HTML
#     msg.set_content(item.body)  # Plain text version
#     msg.add_alternative(updated_body.replace('\n', '<br>'), subtype='html')  # HTML version with images replaced

#     # Adding attachments
#     for attachment in item.attachments:
#         try:
#             attachment_data = attachment['filepath'].split(',', 1)[1]
#             attachment_bytes = base64.b64decode(attachment_data)

#             # Determine the MIME type based on the filename extension
#             filename = attachment['filename']
#             extension = filename.split('.')[-1].lower()
#             maintype = 'application'
#             subtype = 'octet-stream'

#             if extension == 'pdf':
#                 subtype = 'pdf'
#             elif extension == 'csv':
#                 subtype = 'csv'
#             elif extension == 'txt':
#                 subtype = 'text/plain'

#             msg.add_attachment(attachment_bytes,
#                                maintype=maintype,
#                                subtype=subtype,
#                                filename=filename,  # Use the original filename
#                                cid=attachment.get('cid'))  # Attach CID if available
#         except Exception as e:
#             print(f"Error adding attachment: {e}")

#     print("Message attachments:", msg)

#     try:
#         with smtplib.SMTP(smtp_server, smtp_port) as server:
#             # Enable debug output if needed
#             # server.set_debuglevel(1)
#             print(f"Connecting to SMTP server {smtp_server} on port {smtp_port}")
#             server.ehlo()
#             server.starttls()
#             print("Starting TLS")
#             server.ehlo()  # Re-identify as an encrypted connection
#             server.login(sender, mailbox_password)
#             print("Logged in to SMTP server")
#             server.send_message(msg)
#             print("Email sent successfully!")
#     except Exception as e:
#         print(f"Error sending email: {e}")
    
#     conn.close()  # Close the database connection
##################################################################
# def send_email(item):
#     print("Entered send method", item)
#     conn = connect_to_database()  # Assuming you have this function defined
#     cursor = conn.cursor()
#     print("We are entering the send email method")
    
#     # Fetch SMTP server details from account_configurations
#     smtp_config_query = "SELECT smtp_server, smtp_port FROM account_configurations WHERE username = %s"
#     cursor.execute(smtp_config_query, (mail_username,))
#     result = cursor.fetchone()

#     if not result:
#         print("Error: Could not find SMTP configuration for this user.")
#         return  # Exit the function if no configuration is found

#     smtp_server, smtp_port = result

#     sender = mail_username  # Assuming you want to send from the logged-in account
    
#     # Prepare an attachments list to store the image data (if any)
#     inline_attachments = []
#     non_image_attachments = []

#     # Replace inline images in the body with cid and prepare attachments
#     updated_body = replace_images_with_tags(item.body, inline_attachments)
    
#     msg = EmailMessage()
#     msg['Subject'] = item.subject
#     msg['From'] = sender
#     msg['To'] = item.to_email
#     msg['Date'] = item.date
#     msg['Cc'] = item.cc

#     # Set the email body as both plain text and HTML
#     msg.set_content(item.body)  # Plain text version
#     msg.add_alternative(updated_body.replace('\n', '<br>'), subtype='html')  # HTML version with images replaced
#     print("attach for new outlook", inline_attachments)

#     # Add inline image attachments
#     for attachment in inline_attachments:
#         try:
#             attachment_data = attachment['data'].split(',', 1)[1]
#             attachment_bytes = base64.b64decode(attachment_data)
#             cid = attachment['cid']
#             msg.add_attachment(attachment_bytes,
#                                maintype='image',
#                                subtype='png',  # Assuming all images are png
#                                cid=cid)
#         except Exception as e:
#             print(f"Error adding image attachment: {e}")

#     # Separate inline images from actual attachments in `item.attachments`
#     for attachment in item.attachments:
#         # Assuming `inline` field helps identify inline images in item.attachments
#         if 'cid' in attachment and attachment.get('inline', False):
#             inline_attachments.append(attachment)
#         else:
#             non_image_attachments.append(attachment)

#     # Adding non-image attachments
#     for attachment in non_image_attachments:
#         try:
#             attachment_data = attachment['filepath'].split(',', 1)[1]
#             attachment_bytes = base64.b64decode(attachment_data)

#             # Determine the MIME type based on the filename extension
#             filename = attachment['filename']
#             extension = filename.split('.')[-1].lower()
#             maintype = 'application'
#             subtype = 'octet-stream'

#             if extension == 'pdf':
#                 subtype = 'pdf'
#             elif extension == 'csv':
#                 subtype = 'csv'
#             elif extension == 'txt':
#                 subtype = 'plain'

#             msg.add_attachment(attachment_bytes,
#                                maintype=maintype,
#                                subtype=subtype,
#                                filename=filename)  # Use the original filename
#         except Exception as e:
#             print(f"Error adding attachment: {e}")

#     try:
#         with smtplib.SMTP(smtp_server, smtp_port) as server:
#             print(f"Connecting to SMTP server {smtp_server} on port {smtp_port}")
#             server.ehlo()
#             server.starttls()
#             print("Starting TLS")
#             server.ehlo()  # Re-identify as an encrypted connection
#             server.login(sender, mailbox_password)
#             print("Logged in to SMTP server")
#             server.send_message(msg)
#             print("Email sent successfully!")
#     except Exception as e:
#         print(f"Error sending email: {e}")
    
#     conn.close()
##############################################################################################

def send_email(item):
    print("Entered send method", item)
    conn = connect_to_database()  # Assuming you have this function defined
    cursor = conn.cursor()
    print("We are entering the send email method")
    
    # Fetch SMTP server details from account_configurations
    smtp_config_query = "SELECT smtp_server, smtp_port FROM account_configurations WHERE username = %s"
    cursor.execute(smtp_config_query, (mail_username,))
    result = cursor.fetchone()

    if not result:
        print("Error: Could not find SMTP configuration for this user.")
        return  # Exit the function if no configuration is found

    smtp_server, smtp_port = result

    sender = mail_username  # Assuming you want to send from the logged-in account
    
    # Prepare an attachments list to store the image data (if any)
    attachments = []

    # Replace images in the body with cid and prepare attachments (this works even if no images are present)
    updated_body = replace_images_with_tags(item.body, attachments)
    
    msg = EmailMessage()
    msg['Subject'] = item.subject
    msg['From'] = sender
    msg['To'] = item.to_email
    msg['Date'] = item.date
    msg['Cc'] = item.cc

    # Set the email body as both plain text and HTML
    msg.set_content(item.body)  # Plain text version
    msg.add_alternative(updated_body.replace('\n', '<br>'), subtype='html')  # HTML version with images replaced
    print("attach for new outlook",attachments)

    # Add image attachments with cid
    for attachment in attachments:
        try:
            attachment_data = attachment['data'].split(',', 1)[1]
            attachment_bytes = base64.b64decode(attachment_data)
            cid = attachment['cid']
            msg.add_attachment(attachment_bytes,
                               maintype='image',
                               subtype='png',  # Assuming all images are png
                               cid=cid)
        except Exception as e:
            print(f"Error adding image attachment: {e}")

    

    # Adding non-image attachments
    for attachment in item.attachments:
        try:
            attachment_data = attachment['filepath'].split(',', 1)[1]
            attachment_bytes = base64.b64decode(attachment_data)

            # Determine the MIME type based on the filename extension
            filename = attachment['filename']
            extension = filename.split('.')[-1].lower()
            maintype = 'application'
            subtype = 'octet-stream'

            if extension == 'pdf':
                subtype = 'pdf'
            elif extension == 'csv':
                subtype = 'csv'
            elif extension == 'txt':
                subtype = 'plain'

            msg.add_attachment(attachment_bytes,
                               maintype=maintype,
                               subtype=subtype,
                               filename=filename,  # Use the original filename
                               cid=attachment.get('cid'))  # Attach CID if available
        except Exception as e:
            print(f"Error adding attachment: {e}")

   # print("Message attachments:", msg)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            print(f"Connecting to SMTP server {smtp_server} on port {smtp_port}")
            server.ehlo()
            server.starttls()
            print("Starting TLS")
            server.ehlo()  # Re-identify as an encrypted connection
            server.login(sender, mailbox_password)
            print("Logged in to SMTP server")
            server.send_message(msg)
            print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")
    
    conn.close()  # Close the database connection

def replace_images_with_tags(body, attachments=None):
    if attachments is None:
        attachments = []
    
    # Define a regex to match the base64 image pattern
    pattern = r'\[Image: (data:image/[^;]+;base64,[^\]]+)\]'
    
    # Function to replace matched pattern with <img> tag and generate CID
    def replace_with_img_tag(match):
        base64_image = match.group(1)
        # Generate a unique CID for each image
        cid = f'image_{len(attachments)}'
        # Add the image data to attachments
        attachments.append({
            'data': base64_image,
            'cid': cid
        })
        return f'<img src="cid:{cid}" alt="Embedded Image"/>'
    
    # Replace all occurrences in the body
    new_body = re.sub(pattern, replace_with_img_tag, body)
    
    return new_body






def send_email1(item):
    print("enterd sent method",item)
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
    #print("before sending to the body iam getting item body =====>",item.body)
    converted_text = convert_images_to_base64(item.body)
    # print("Converted text:", converted_text)


    msg = EmailMessage()
    msg['Subject'] = item.subject
    msg['From'] = sender
    msg['To'] = item.to_email
    msg['Date'] = item.date
    msg['Cc']=item.cc
    # msg.set_content(item.body)
    
    # print("New body:", new_body)
    # print("Attachments:", attachments)
    # msg.set_content(new_body)

    # new_body, attachments = extract_images_and_replace_with_cid(converted_text)
    # msg.add_alternative(new_body, subtype='html')
    # for attachment in attachments:
    #     msg.add_attachment(attachment['data'],
    #                        maintype=attachment['maintype'],
    #                        subtype=attachment['subtype'],
    #                        filename=attachment['filename'],
    #                        cid=attachment['cid'])

        # Set email body
    # msg.set_content(item.body)
    # msg.add_alternative(item.body, subtype='html')

    # # Attachments are now provided directly in item.attachments
    # for attachment in item.attachments:
    #     try:
    #         attachment_data = attachment['filepath'].split(',', 1)[1]
    #         attachment_bytes = base64.b64decode(attachment_data)
    #         msg.add_attachment(attachment_bytes,
    #                            maintype='application',
    #                            subtype='octet-stream',
    #                            filename='attachment.csv',  # Customize filename or extract from attachment if available
    #                            cid=attachment['cid'] if attachment['cid'] else None)
    #     except Exception as e:
    #         print(f"Error adding attachment: {e}")

        # Process the email body and handle base64-encoded images

    #below code is working for send email with all attchments
    #item.body='<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD4AAABDCAYAAADEfbZbAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAPiSURBVHhe7ZptSJNRFMf/JWQfajlKMcuS0FUiC1xQWWymWTmwjMpKMC1SP4hJRZLRUlkvkBTkPuUkKMkKiTBDC7K5COlDRg0LKgvDfEGp2YqwKJ7u3XONx7WicrKNe39w95xzdq/bn3PuuZt7JkkEcMhkduUOIZw3hHDeEMJ5QwjnDSGcN4Rw3uBWuO+/lr6pR2qaBV3M9UZs6TW07olinn+YMOE9CcnIjJ/OgmOJXluIYv1M5vkJKtyndF+SUuKWSynWXhYITPy4x/tg3bgC80ubYKvYjPkaYi8rR6OTPvcVPS0W7FifJscXp2HVLgtuDbgXytwtJ8/lwvq4E9Yitp7MM1a0Yeg74LpngXGZQY6nlZF5n9hCGf83t6YTyHugg/lsJY7kr0OSGuiqzceqknp0qjaQ+ElUH0hC6MN6FK4mQl+zdW76UF1UhHMfk+X16bPwtL4M2wsPYGVROxJKKnGuIhuJn9twbMdxNH5myygs877jr0u9V6rZsFyaF7dfuvKBhSj9DVImWR+3zyYpw9L7G1LuIjJ/r00aoX7rUbLWc95zqSqZ/s2dUvUrFiKMNB1yzz1oZwHChGW86xQrP4+RWtvHZjAW65CkYjZh6J4djxCFgt3JUIQBdQYKtk0DWm7jliJz69OV86ZhBnU0q5G+QI5QQuMXIpZcR77JPmXChIeSrr4tK+OXkakJZTO8M+JykUcN4hRvfJToufQI7MPgkOy7CWFXJSFTMOZViO/JhAmPNhbj1LHDvwy/H2MM/zc3D6aqaK2+wMsxTUym5y3dJjEk87I/HgJOeLjegERSzjXn20CL/ifOJtRcJUeSfil03sr7Hwk44YjcgqpSDb7cLMPKLAsutrShsbYcqfoTsJG9f+RwBsLZ1PEQeMIJsXusuH82GwmuGzCVlGHv6XZ80efhsu0C8r00vf9B/HbGG0I4bwjhvCGE84YQzhtCOG8I4bwhhPOGEM4bQjhv+PR/br39yp8zAxufC58zO5J5gY3Y47whhPOGOM58gS+7uqPOgoZu5vwBtW4r9hv//TVFqfNGkHyAGcAdSwPsw8SMMcCco5XDo3Rch6n5LXMoKhh252LNHOZ6IegzTnvBWNEUF+znLTjT/PuP0MEtnGR6tAHSJmc2FbvH1hg55uy4jTu9su1JUAt3PGOZDtMiR9HZtTkGaNyWC44n3rMexMIHMEj3PCVM7XFfTARmh8mW892gbHjAbVcPYuGRiGBZxbATypsdgUH0s2pQz4yQDQ+COuPaeHan37ADdYoO7qiz44XbUkG7xPvxGtylrtuk6OANMJnJ0UbGaKfXGH93lgM/ABhy36qC+SSaAAAAAElFTkSuQmCC" alt="Embedded Image">'
    print("body is",item.body)
    html_body = item.body.replace('\n', '<br>')
    print("message body is")

    msg.set_content(item.body)
    msg.add_alternative(html_body, subtype='html')

    for attachment in item.attachments:
        try:
            attachment_data = attachment['filepath'].split(',', 1)[1]
            attachment_bytes = base64.b64decode(attachment_data)

            # Determine the MIME type based on the filename extension
            filename = attachment['filename']
            extension = filename.split('.')[-1].lower()
            maintype = 'application'
            subtype = 'octet-stream'

            if extension == 'pdf':
                subtype = 'pdf'
            elif extension == 'csv':
                subtype = 'csv'
            elif extension == 'txt':
                subtype = 'text/plain'

            msg.add_attachment(attachment_bytes,
                            maintype=maintype,
                            subtype=subtype,
                            filename=filename,  # Use the original filename
                            cid=attachment['cid'] if attachment['cid'] else None)
        except Exception as e:
            print(f"Error adding attachment: {e}")
    
    print("msg attchments is",msg)
        

    #print("we can see the messages of what we send ====>===>", msg)
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
            print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")
    conn.close()  # Close the database connection

import smtplib
import base64
import requests
from email.message import EmailMessage

def send_far_email(item):
    print("Entered send method", item)
    conn = connect_to_database()  # Assuming you have this function defined
    cursor = conn.cursor()
    print("We are entering the send email method")
    
    # Fetch SMTP server details from account_configurations
    smtp_config_query = "SELECT smtp_server, smtp_port FROM account_configurations WHERE username = %s"    
    cursor.execute(smtp_config_query, (mail_username,))
    result = cursor.fetchone()

    if not result:
        print("Error: Could not find SMTP configuration for this user.")
        return  # Exit the function if no configuration is found

    smtp_server, smtp_port = result
    sender = mail_username  # Assuming you want to send from the logged-in account
    
    # Prepare an attachments list to store the image data (if any)
    attachments = []
    
    # Replace images in the body with cid and prepare attachments (works even if no images are present)
    updated_body = replace_images_with_tags(item.body, attachments)

    msg = EmailMessage()
    msg['Subject'] = item.subject
    msg['From'] = sender
    msg['To'] = item.to_email
    msg['Date'] = item.date
    msg['Cc'] = item.cc

    html_body = item.body.replace('\n', '<br>')
    print("Message body is", item.body)
    
    # Set the email body as both plain text and HTML
    msg.set_content(item.body)  # Plain text version
    msg.add_alternative(updated_body.replace('\n', '<br>'), subtype='html')  # HTML version with image tags

    # Add image attachments with cid
    for attachment in attachments:
        try:
            attachment_data = attachment['data'].split(',', 1)[1]
            attachment_bytes = base64.b64decode(attachment_data)
            cid = attachment['cid']
            msg.add_attachment(attachment_bytes,
                               maintype='image',
                               subtype='png',  # Assuming all images are png
                               cid=cid)
        except Exception as e:
            print(f"Error adding image attachment: {e}")

    # Adding non-image attachments (PDF, CSV, etc.)
    for attachment in item.attachments:
        try:
            attachment_data = attachment['filepath'].split(',', 1)[1]
            attachment_bytes = base64.b64decode(attachment_data)

            # Determine the MIME type based on the filename extension
            filename = attachment['filename']
            extension = filename.split('.')[-1].lower()
            maintype = 'application'
            subtype = 'octet-stream'

            if extension == 'pdf':
                subtype = 'pdf'
            elif extension == 'csv':
                subtype = 'csv'
            elif extension == 'txt':
                maintype = 'text'
                subtype = 'plain'

            msg.add_attachment(attachment_bytes,
                               maintype=maintype,
                               subtype=subtype,
                               filename=filename,  # Use the original filename
                               cid=attachment.get('cid'))  # Attach CID if available
        except Exception as e:
            print(f"Error adding attachment: {e}")
    
    print("Message attachments:", msg)

    # Send the email
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            print(f"Connecting to SMTP server {smtp_server} on port {smtp_port}")
            server.ehlo()
            server.starttls()
            server.ehlo()  # Re-identify as an encrypted connection
            server.login(sender, mailbox_password)
            print("Logged in to SMTP server")
            server.send_message(msg)
            print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

    conn.close()  # Close the database connection


# def send_far_email(item):
#     print("enterd sent method",item)
#     conn = connect_to_database()  # Assuming you have this function defined
#     cursor = conn.cursor()
#     print("we are entering to the send email method")
#     # Fetch SMTP server details from account_configurations
#     smtp_config_query = "SELECT smtp_server, smtp_port FROM account_configurations WHERE username = %s"    
#     cursor.execute(smtp_config_query, (mail_username,))
#     result = cursor.fetchone()
 
#     if not result:
#         print("Error: Could not find SMTP configuration for this user.")
#         return  # Exit the function if no configuration is found
 
#     smtp_server, smtp_port = result
#     sender = mail_username # Assuming you want to send from the logged-in account
#     #print("before sending to the body iam getting item body =====>",item.body)
#     converted_text = convert_images_to_base64(item.body)
#     # print("Converted text:", converted_text)
#     updated_body = replace_images_with_tags(item.body)
#     msg = EmailMessage()
#     msg['Subject'] = item.subject
#     msg['From'] = sender
#     msg['To'] = item.to_email
#     msg['Date'] = item.date
#     msg['Cc']=item.cc

#     html_body = item.body.replace('\n', '<br>')
#     print("message body is",item.body)
#     msg.set_content(item.body)
#     #msg.add_alternative(html_body, subtype='html')
#     msg.add_alternative(updated_body.replace('\n', '<br>'), subtype='html') 

#     for attachment in item.attachments:
#         try:
#             attachment_data = attachment['filepath'].split(',', 1)[1]
#             attachment_bytes = base64.b64decode(attachment_data)

#             # Determine the MIME type based on the filename extension
#             filename = attachment['filename']
#             extension = filename.split('.')[-1].lower()
#             maintype = 'application'
#             subtype = 'octet-stream'

#             if extension == 'pdf':
#                 subtype = 'pdf'
#             elif extension == 'csv':
#                 subtype = 'csv'
#             elif extension == 'txt':
#                 subtype = 'text/plain'

#             msg.add_attachment(attachment_bytes,
#                             maintype=maintype,
#                             subtype=subtype,
#                             filename=filename,  # Use the original filename
#                             cid=attachment['cid'] if attachment['cid'] else None)
#         except Exception as e:
#             print(f"Error adding attachment: {e}")
    
#     print("msg attchments is",msg)



#     # Send the email
#     try:
#         with smtplib.SMTP(smtp_server, smtp_port) as server:
#             print(f"Connecting to SMTP server {smtp_server} on port {smtp_port}")
#             server.ehlo()
#             server.starttls()
#             server.ehlo()  # Re-identify as an encrypted connection
#             server.login(sender, mailbox_password)
#             print("Logged in to SMTP server")
#             server.send_message(msg)
#             print("Email sent successfully!")
#     except Exception as e:
#         print(f"Error sending email: {e}")

#     conn.close()  # Close the database connection


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

# @app.get("/skills")
# async def fetch_all_emails():
#     conn = connect_to_database()
#     cursor = conn.cursor(cursor_factory=RealDictCursor)  # Use RealDictCursor for dict-like rows
#     try:
#         fetch_query = """
#         SELECT * FROM agent_interactions
#         """
#         cursor.execute(fetch_query)
#         emails = cursor.fetchall()
        
#         return emails  # RealDictCursor returns rows as dictionaries, which FastAPI can auto-convert to JSON
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error fetching emails from database: {str(e)}")
    
#     finally:
#         cursor.close()
#         conn.close()


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
#             api_url = agents_url
#             while True:
#                 agents_data = await fetch_agents1(api_url)
#                 if agents_data is None:
#                     raise HTTPException(status_code=500, detail="Failed to fetch agents data")

#                 # Update agents data with additional info from cache
#                 for agent in fetch_detail_cache:
#                     agent_key = f"agent:{agent['agent_id']}"
#                     if agent_key in agents_data and agents_data[agent_key]['agent_id'] == str(agent['agent_id']):
#                         agents_data[agent_key].update({
#                             'queues': agent['queues'],
#                             'skills': agent['skills'],
#                             'max_chat_concurrent_interactions': agent['max_chat_concurrent_interactions'],
#                             'max_call_concurrent_interactions': agent['max_call_concurrent_interactions'],
#                             'max_email_concurrent_interactions': agent['max_email_concurrent_interactions']
#                         })

#                 # Find a matched agent
#                 matched_agent = find_matched_ready_agent(agents_data, message)
#                 if matched_agent:
#                     agent_idl = matched_agent['agent_id']
#                     print(f"Matched agent: {agent_idl}")

#                     # Emit the event for the new email
#                     await sio_Server.emit('new_email', {
#                         'sender': sender,
#                         'message_id': received_info,
#                         'recipient': recipient,
#                         'to_email': to_email,
#                         'cc_email': cc_email,
#                         'subject': subject,
#                         'date': date,
#                         'body': body,
#                         'session_id': rejected_session_id,
#                         "attachments": filtered_attaacthments(attachments)
#                     })

#                     print(f"Assigned email with session_id {rejected_session_id} to agent {agent_idl}")

#                     # After successful assignment, delete the processed row from rejected_emails table
#                     print(f"Deleting row with session_id: {rejected_session_id}")
#                     await conn.execute("DELETE FROM rejected_emails WHERE session_id = $1", rejected_session_id)
#                     print(f"Deleted row for session_id {rejected_session_id}")

#                     break  # Exit the while loop after successful assignment

#                 else:
#                     print(f"No matched agent available for session_id {rejected_session_id}. Waiting for 15 seconds...")
#                     await asyncio.sleep(15)  # Wait before retrying

#             print("Waiting for 15 seconds before processing the next row...")
#             await asyncio.sleep(15)

#     except Exception as e:
#         print(f"Error fetching or processing data: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

#     finally:
#         await conn.close()

#     return {"status": "Processing complete"}


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
#             api_url = agents_url
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


@app.get("/gmail/{name}")
async def fetch_emails_by_name(name: str):
    """Fetch emails filtered by sender, recipient, or cc_emails using the name."""
    print("started search : started", name)
    conn = connect_to_database()
    cursor = conn.cursor()
    try:
        fetch_query = """
        SELECT * FROM emails
        WHERE sender = %s OR recipient = %s OR cc_emails = %s
        """
        print("query is", fetch_query)
        cursor.execute(fetch_query, (name, name, name))
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
        
        print("started search : ", email_list)

        print("started search : ended")
        
        if not email_list:
            raise HTTPException(status_code=404, detail="No emails found with the specified name.")
        
        return email_list
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching emails from database: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()



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


@app.get("/rightside")
async def fetch_latest_email():
    conn = connect_to_database()
    cursor = conn.cursor()
    try:
        fetch_query = """
        SELECT * FROM emails ORDER BY TIMESTAMP DESC LIMIT 1
        """
        cursor.execute(fetch_query)
        email = cursor.fetchone()  # Fetch only one row
        
        def parse_json_field(field):
            if isinstance(field, memoryview):
                return json.loads(field.tobytes().decode('utf-8'))
            elif isinstance(field, str):
                return json.loads(field)
            return None
        
        if email:
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
            return email_data
        else:
            raise HTTPException(status_code=404, detail="No emails found")
    
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


#in redis all mails
@app.get("/fetch_mails")
async def fetch_emails():
    print("entered accept mail")
    existing_data = redis_client.get("accepted_mail")
    #print("key is there or not",existing_data)
    
    if existing_data:
        # Decode the existing data
        existing_data = json.loads(existing_data)
    else:
        # Initialize as an empty list if no data exists
        existing_data = []

    #print("fetching existing data",existing_data)

    # Append new rejected email to the existing data
   
    #print("fetching after adding data",existing_data)


    return existing_data
##########################

# Route to execute commands
@app.get("/available-command/{name}")
async def execute_commands(name: str):
    print("Executing FreeSWITCH commands...",name)
    response=client1.execute('callcenter_config agent set status 1033@10.16.7.91 Available')
    print("response is",response)
    return "available"

@app.get("/busy-command/{name}")
async def execute_commands(name: str):
    print("Executing FreeSWITCH commands...",name)
    response=client1.execute('callcenter_config agent set status 1033@10.16.7.91 \'Available (On Demand)\'')
    print("response is",response)
    return "busy"
########################

#in redis delet the deleted item

@app.get("/rejected_mails")
async def fetch_emails():
    print("entered accept mail")
    existing_data = redis_client.get("rejected_mail")
    #print("key is there or not",existing_data)
    
    if existing_data:
        # Decode the existing data
        existing_data = json.loads(existing_data)
    else:
        # Initialize as an empty list if no data exists
        existing_data = []

    #print("fetching existing data",existing_data)

    # Append new rejected email to the existing data
   
    #print("fetching after adding data",existing_data)


    return existing_data



# def delete_email(email):
#     print("Entered delete mail:", email)
    
#     # Fetch the existing data from Redis
#     existing_data = redis_client.get("accepted_mail")
#     print("Key is there or not:", existing_data)
    
#     if existing_data:
#         # Decode the existing data
#         existing_data = json.loads(existing_data)
#         print("Existing data fetched:", existing_data)
        
#         # Find and remove the email from the existing data
#         updated_data = [item for item in existing_data if item.get('email') != email]
        
#         if len(existing_data) != len(updated_data):
#             # If the email was found and removed, update the Redis key with the new data
#             redis_client.set("accepted_mail", json.dumps(updated_data))
#             print(f"Email {email} removed successfully.")
#         else:
#             print(f"Email {email} not found in the list.")
        
#         return updated_data
#     else:
#         # If no data exists, return an empty list
#         print("No existing data found.")
#         return []



def delete_email(email: accept_Email):
    try:
        # Fetch existing data from Redis
        existing_data = redis_client.get("accepted_mail")
        print("Type of existing_data from Redis:", type(existing_data))
        print("Type of email:", type(email))

        # If existing_data is not None, deserialize it
        if existing_data:
            existing_data = json.loads(existing_data)  # Convert string to a list of JSON objects
            print("Deserialized existing_data:", existing_data)
            print("Type of deserialized data:", type(existing_data))  # Should now be a list

        # Convert the email object to a dictionary
        email_dict = email.dict()
        print("Converted email object to dictionary:", email_dict)

        # Loop through each email in the existing data to find the match
        email_found = False
        for i, stored_email in enumerate(existing_data):
            stored_email_dict = json.loads(stored_email)  # Deserialize each email string in the list
            if stored_email_dict["session_id"] == email_dict["session_id"]:  # Match by session_id or other criteria
                email_found = True
                print(f"Email with session_id {email.session_id} found, deleting...")
                del existing_data[i]  # Remove the email from the list
                break

        if not email_found:
            print(f"No email with session_id {email.session_id} found.")

        # Re-serialize the modified data and store it back in Redis
        redis_client.set("accepted_mail", json.dumps(existing_data))

    except Exception as e:
        print("An error occurred while processing the email deletion:")
        print(str(e))




# FreeSWITCH client configuration
host = "10.16.7.91"
port = 8021
password = "ClueCon"

client = FreeSWITCHClient(host, port, password)
commands = [
    "callcenter_config agent set status 1045@10.16.7.91 Available"
]









#-----------------------

def start_polling():
    host = "10.16.7.91"
    port = 8021
    password = "ClueCon"

    client = FreeSWITCHClient(host, port, password)
    print("client response is",client)
    global client1
    client1 = client
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
        asyncio.run(process_rejected_emails())