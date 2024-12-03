import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get the database credentials from the environment variables
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")

# Establish the connection
try:
    connection = psycopg2.connect(
        host=db_host,
        port=db_port,
        database=db_name,
        user=db_user,
        password=db_password
    )
    print("Database connection established successfully!",db_host,db_name,db_password)
except psycopg2.Error as e:
    print(f"Error connecting to the database: {e}")
finally:
    # Remember to close the connection when done
    if 'connection' in locals() and connection:
        connection.close()
        print("Database connection closed.")
