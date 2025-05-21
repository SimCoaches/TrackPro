import psycopg2
from dotenv import load_dotenv
import os
import time

# Load environment variables from .env
load_dotenv("M:\\TrackPro-main\\.env")

def get_db_connection():
    """Establish and return a connection to the Supabase database."""
    USER = os.getenv("user")
    PASSWORD = os.getenv("password")
    HOST = os.getenv("host")
    PORT = os.getenv("port")
    DBNAME = os.getenv("dbname")

    try:
        connection = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME
        )
        print("Database connection established.")
        return connection
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return None

def mcp_server():
    """Run a simple MCP server that periodically checks the database."""
    print("Starting MCP server...")
    while True:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT NOW();")
                result = cursor.fetchone()
                print(f"MCP Server - Current Time: {result}")
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"MCP Server - Error querying database: {e}")
        else:
            print("MCP Server - Failed to establish connection, retrying...")
        time.sleep(5)  # Poll every 5 seconds to keep the server alive

if __name__ == "__main__":
    try:
        mcp_server()
    except KeyboardInterrupt:
        print("MCP server stopped by user.")