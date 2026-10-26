"""
Configuration de la base de données MySQL
"""
import pymysql

# Configuration de la connexion MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'glycoflow_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    """Crée et retourne une connexion à la base de données"""
    return pymysql.connect(**DB_CONFIG)
