"""
Script pour créer un utilisateur dans la base de données
Exécutez: python create_user.py
"""
import bcrypt
import db_config

def create_user(username, password, role, email=None):
    """Crée un utilisateur dans la base de données"""
    # Hasher le mot de passe
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (username, password_hash, role, email) VALUES (%s, %s, %s, %s)",
                (username, password_hash, role, email)
            )
            conn.commit()
            print(f"Utilisateur '{username}' créé avec succès!")
            print(f"Rôle: {role}")
            if email:
                print(f"Email: {email}")
    except Exception as e:
        print(f"Erreur lors de la création de l'utilisateur: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("=== Création d'un utilisateur ===")
    username = input("Nom d'utilisateur: ")
    password = input("Mot de passe: ")
    role = input("Rôle (admin/medecin/infirmier/gestionnaire): ")
    email = input("Email (optionnel): ") or None
    
    if role not in ['admin', 'medecin', 'infirmier', 'gestionnaire']:
        print("Rôle invalide. Rôles valides: admin, medecin, infirmier, gestionnaire")
    else:
        create_user(username, password, role, email)
