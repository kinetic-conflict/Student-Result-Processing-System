import mysql.connector
from mysql.connector import Error
from config import Config

def get_db_connection():
    """Create and return a database connection."""
    try:
        connection = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        raise

def execute_query(query, params=None, fetch=True):
    """Execute a SELECT query and return results."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        
        if fetch:
            result = cursor.fetchall()
        else:
            result = cursor.lastrowid
            connection.commit()
        
        return result
    except Error as e:
        if connection:
            connection.rollback()
        print(f"Error executing query: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

def execute_update(query, params=None):
    """Execute an INSERT, UPDATE, or DELETE query."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        connection.commit()
        return cursor.lastrowid
    except Error as e:
        if connection:
            connection.rollback()
        print(f"Error executing update: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

def execute_transaction(queries_with_params):
    """Execute multiple queries in a transaction."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        for query, params in queries_with_params:
            cursor.execute(query, params or ())
        
        connection.commit()
        return True
    except Error as e:
        if connection:
            connection.rollback()
        print(f"Error executing transaction: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
