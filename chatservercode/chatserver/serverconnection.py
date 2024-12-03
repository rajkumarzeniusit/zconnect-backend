import socket
import json
import re
import csv
from io import StringIO


class FreeSWITCHClient:
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.connection = None
 
    def connect(self):
        if self.connection is None:
            print("Connecting to FreeSWITCH")
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection.settimeout(30)  # Set timeout to 30 seconds
            self.connection.connect((self.host, self.port))
            auth_response = self.connection.recv(1024).decode()
            if "Content-Type: auth/request" in auth_response:
                self.connection.send(f"auth {self.password}\n\n".encode())
                response = self.connection.recv(1024).decode()
                if "Reply-Text: +OK" in response:
                    print("Connected to FreeSWITCH")
                else:
                    raise ConnectionError("Failed to authenticate with FreeSWITCH")
            else:
                raise ConnectionError("Failed to connect to FreeSWITCH")
 
    def reconnect(self):
        if self.connection:
            self.connection.close()
        self.connection = None
        self.connect()
 
    def execute(self, command):
        if self.connection is None:
            self.connect()
        self.connection.send(f"api {command}\n\n".encode())
        response = self._recv_response()
        return response
 
    def _recv_response(self):
        response = ""
        content_length = None
        while True:
            part = self.connection.recv(1024).decode()
            response += part
            if content_length is None:
                content_length_match = re.search(r"Content-Length: (\d+)", response)
                if content_length_match:
                    content_length = int(content_length_match.group(1))
            if content_length and len(response.split("\n\n", 1)[1]) >= content_length:
                break
        return response
 
    def execute_multiple_commands(self, commands):
        results = {}
        for command in commands:
            try:
                results[command] = self.execute(command)
            except (ConnectionError, socket.timeout) as e:
                print(f"Connection error while executing command '{command}': {e}")
                self.reconnect()
                results[command] = self.execute(command)
            except Exception as e:
                results[command] = str(e)
        return results
 
    def parse_response(self, response):
        try:
            data = response.split('\n\n', 1)[1].strip()
        except IndexError:
            raise ValueError("Invalid response format")
        reader = csv.DictReader(StringIO(data), delimiter='|')
        return [row for row in reader]
 
    def data_to_json(self, data):
        return [json.dumps(item) for item in data]
    

       
