"""
Script pour créer la table chatbot_conversations
"""
import pymysql
from db_config import get_db_connection

# SQL pour créer la table
create_table_sql = """
CREATE TABLE IF NOT EXISTS chatbot_conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    role VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

try:
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(create_table_sql)
        conn.commit()
        print("Table 'chatbot_conversations' créée avec succès !")
except Exception as e:
    print(f"Erreur lors de la création de la table: {e}")
finally:
    if 'conn' in locals():
        conn.close()
