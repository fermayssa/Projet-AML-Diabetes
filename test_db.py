"""
Script de test pour vérifier la connexion à la base de données et les utilisateurs
"""
import db_config

def test_connection():
    """Teste la connexion à la base de données"""
    try:
        conn = db_config.get_db_connection()
        print("✓ Connexion à la base de données réussie")
        
        with conn.cursor() as cursor:
            # Vérifier si la table users existe
            cursor.execute("SHOW TABLES LIKE 'users'")
            result = cursor.fetchone()
            if result:
                print("✓ Table 'users' existe")
                
                # Lister les utilisateurs
                cursor.execute("SELECT username, role, email FROM users")
                users = cursor.fetchall()
                print(f"\nUtilisateurs dans la base ({len(users)}):")
                for user in users:
                    print(f"  - {user['username']} ({user['role']}) - {user['email']}")
            else:
                print("✗ Table 'users' n'existe pas")
                print("  Exécutez le script database.sql dans phpMyAdmin")
        
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Erreur de connexion: {e}")
        print("\nVérifiez:")
        print("  - MySQL est en cours d'exécution")
        print("  - La base de données 'glycoflow_db' existe")
        print("  - Les identifiants dans db_config.py sont corrects")
        return False

if __name__ == "__main__":
    print("=== Test de connexion à la base de données ===\n")
    test_connection()
