"""
Script pour recréer les utilisateurs de test avec le mot de passe correct
"""
import bcrypt
import db_config

def reset_test_users():
    """Recrée les utilisateurs de test avec password123"""
    password = "password123"
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    users = [
        ('admin', 'admin', 'admin@hospital.com'),
        ('medecin1', 'medecin', 'medecin1@hospital.com'),
        ('infirmier1', 'infirmier', 'infirmier1@hospital.com'),
        ('gestionnaire1', 'gestionnaire', 'gestionnaire1@hospital.com')
    ]
    
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Supprimer les utilisateurs existants
            cursor.execute("DELETE FROM users")
            conn.commit()
            print("Utilisateurs existants supprimés")
            
            # Insérer les nouveaux utilisateurs
            for username, role, email in users:
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role, email) VALUES (%s, %s, %s, %s)",
                    (username, password_hash, role, email)
                )
                print(f"Utilisateur '{username}' créé (mot de passe: {password})")
            
            conn.commit()
            print("\n✓ Tous les utilisateurs recréés avec succès!")
            print(f"Mot de passe pour tous: {password}")
    except Exception as e:
        print(f"Erreur: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("=== Recréation des utilisateurs de test ===\n")
    reset_test_users()
