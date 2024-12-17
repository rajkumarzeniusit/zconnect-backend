FROM python:3.10-slim

WORKDIR /opt/zconnect

COPY emailpolling.py /opt/zconnect/
RUN python3 get-pip.py --force-reinstall
RUN pip3 install redis
EXPOSE 8000
CMD [ "python3","emailpolling.py" ]
