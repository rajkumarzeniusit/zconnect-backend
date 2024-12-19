FROM python:3.10-slim

WORKDIR /opt/zconnect

COPY emailpolling.py /opt/zconnect/
COPY serverconnection.py /opt/zconnect/
COPY .env /opt/zconnect/
COPY Dockerfile /opt/zconnect/
RUN apt-get update && apt-get install -y curl

# Download get-pip.py if not present
RUN curl -O https://bootstrap.pypa.io/get-pip.py && \
    chmod +x get-pip.py && \
    python3 get-pip.py --force-reinstall
RUN pip install asyncpg
RUN pip install uvicorn
RUN python3 -m pip install uvicorn
RUN python -m uvicorn --version
RUN pip install aiohttp
RUN pip install python-dotenv
RUN pip install fastapi
RUN pip install flask
RUN pip install psycopg2-binary
RUN pip install requests
RUN pip install fastapi_socketio
RUN pip3 install redis
CMD ["python", "emailpolling.py"]
