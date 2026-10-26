"""
Application Flask - point d'entrée COMMUN.

NE PAS MODIFIER ce fichier : il charge automatiquement tous les dossiers
présents dans modules/ (sauf ceux qui commencent par "_").
Un module en erreur est signalé sur la page d'accueil, mais ne bloque
pas les autres modules.
"""
import importlib
import os
import pkgutil
import traceback
from flask import Flask, render_template, redirect, url_for, session, request, jsonify
import bcrypt
from groq import Groq

import modules
import db_config

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete_ici'

loaded_modules = []   # modules chargés correctement
failed_modules = []   # modules en erreur

for info in pkgutil.iter_modules(modules.__path__):
    if not info.ispkg or info.name.startswith("_"):
        continue
    try:
        mod = importlib.import_module(f"modules.{info.name}")
        app.register_blueprint(mod.bp)
        loaded_modules.append({
            "title": getattr(mod, "TITLE", info.name),
            "description": getattr(mod, "DESCRIPTION", ""),
            "url": mod.bp.url_prefix or f"/{info.name}",
        })
    except Exception as exc:  # une erreur dans un module ne doit pas casser l'application
        failed_modules.append({"name": info.name, "error": repr(exc)})
        traceback.print_exc()


@app.route("/")
def home_public():
    """Page d'accueil publique de l'hôpital"""
    return render_template("home.html")


@app.route("/app")
def home():
    """Page d'accueil de l'application (après login)"""
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template("index.html", modules=loaded_modules, failed=failed_modules)


@app.route("/login", methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username and password:
            conn = db_config.get_db_connection()
            try:
                with conn.cursor() as cursor:
                    # Rechercher par username ou email
                    cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, username))
                    user = cursor.fetchone()
                    
                    if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                        session['user'] = {
                            'username': user['username'],
                            'role': user['role']
                        }
                        
                        # Redirection selon le rôle
                        if user['role'] == 'admin':
                            return redirect(url_for('admin_dashboard'))
                        elif user['role'] == 'medecin':
                            return redirect(url_for('medecin_dashboard'))
                        elif user['role'] == 'infirmier':
                            return redirect(url_for('infirmier_dashboard'))
                        elif user['role'] == 'gestionnaire':
                            return redirect(url_for('gestionnaire_dashboard'))
                        else:
                            return redirect(url_for('home'))
            except Exception as e:
                print(f"Erreur lors de la connexion: {e}")
            finally:
                conn.close()
    
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Déconnexion"""
    session.clear()
    return redirect(url_for('home_public'))


@app.route("/dashboard/admin")
def admin_dashboard():
    """Dashboard administrateur"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    return render_template("dashboards/admin.html")


@app.route("/dashboard/medecin")
def medecin_dashboard():
    """Dashboard médecin"""
    if 'user' not in session or session['user']['role'] != 'medecin':
        return redirect(url_for('login'))
    return render_template("dashboards/medecin.html")


@app.route("/dashboard/infirmier")
def infirmier_dashboard():
    """Dashboard infirmier"""
    if 'user' not in session or session['user']['role'] != 'infirmier':
        return redirect(url_for('login'))
    return render_template("dashboards/infirmier.html")


@app.route("/dashboard/gestionnaire")
def gestionnaire_dashboard():
    """Dashboard gestionnaire"""
    if 'user' not in session or session['user']['role'] != 'gestionnaire':
        return redirect(url_for('login'))
    return render_template("dashboards/gestionnaire.html")


@app.route('/users')
def users_list():
    """Liste des utilisateurs (admin only)"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, username, email, role, created_at FROM users")
            users = cursor.fetchall()
    finally:
        conn.close()
    
    return render_template('users.html', users=users)


@app.route('/users/add', methods=['POST'])
def add_user():
    """Ajouter un utilisateur (admin only)"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    email = request.form.get('email', '').strip()
    role = request.form.get('role', '')
    
    # Validations côté serveur
    if not username or len(username) < 3 or len(username) > 30:
        flash('Le username doit contenir entre 3 et 30 caractères', 'error')
        return redirect(url_for('users_list'))
    
    if not password or len(password) < 8:
        flash('Le mot de passe doit contenir au moins 8 caractères', 'error')
        return redirect(url_for('users_list'))
    
    if email and not ('@' in email and '.' in email):
        flash('Format d\'email invalide', 'error')
        return redirect(url_for('users_list'))
    
    if role not in ['admin', 'medecin', 'infirmier', 'gestionnaire']:
        flash('Rôle invalide', 'error')
        return redirect(url_for('users_list'))
    
    import bcrypt
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (username, password_hash, email, role) VALUES (%s, %s, %s, %s)",
                (username, password_hash, email if email else None, role)
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f'Erreur lors de l\'ajout: {e}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('users_list'))


@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
def edit_user(user_id):
    """Modifier un utilisateur (admin only)"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    conn = db_config.get_db_connection()
    try:
        if request.method == 'POST':
            password = request.form.get('password')
            email = request.form.get('email')
            role = request.form.get('role')
            
            with conn.cursor() as cursor:
                if password:
                    import bcrypt
                    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    sql = "UPDATE users SET password_hash = %s, email = %s, role = %s WHERE id = %s"
                    cursor.execute(sql, (password_hash, email, role, user_id))
                else:
                    sql = "UPDATE users SET email = %s, role = %s WHERE id = %s"
                    cursor.execute(sql, (email, role, user_id))
            
            conn.commit()
            return redirect(url_for('users_list'))
        else:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, username, email, role FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
    finally:
        conn.close()
    
    if not user:
        return redirect(url_for('users_list'))
    
    return render_template('edit_user.html', user=user)


@app.route('/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    """Supprimer un utilisateur (admin only)"""
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return str(e), 400
    finally:
        conn.close()
    
    return redirect(url_for('users_list'))


@app.route("/search", methods=['GET'])
def search():
    """Recherche de patients et rendez-vous"""
    if 'user' not in session:
        return jsonify({'error': 'Non connecté'}), 401
    
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'patients': [], 'rendez_vous': []})
    
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Recherche de patients (nom, prenom, email, telephone)
            cursor.execute("""
                SELECT id, nom, prenom, age, sexe, email, telephone 
                FROM patients 
                WHERE nom LIKE %s 
                   OR prenom LIKE %s 
                   OR email LIKE %s 
                   OR telephone LIKE %s
                LIMIT 10
            """, (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
            patients = cursor.fetchall()
            
            # Recherche de rendez-vous (patient nom, prenom, date)
            cursor.execute("""
                SELECT r.id, r.date, r.patient_id, p.nom, p.prenom 
                FROM rendez_vous r
                JOIN patients p ON r.patient_id = p.id
                WHERE p.nom LIKE %s 
                   OR p.prenom LIKE %s 
                   OR r.date LIKE %s
                LIMIT 10
            """, (f'%{query}%', f'%{query}%', f'%{query}%'))
            rendez_vous = cursor.fetchall()
            
            return jsonify({
                'patients': patients,
                'rendez_vous': rendez_vous
            })
    finally:
        conn.close()


@app.route('/chatbot', methods=['POST'])
def chatbot():
    """Route pour le chatbot avec Groq"""
    if 'user' not in session:
        return jsonify({'error': 'Non connecté'}), 401
    
    user_message = request.json.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'Message vide'}), 400
    
    try:
        api_key = os.environ.get('GROQ_API_KEY')
        if not api_key:
            return jsonify({'error': 'Clé API Groq non configurée'}), 500
        client = Groq(api_key=api_key)
        
        system_prompt = """Tu es un assistant virtuel pour l'application GlycoFlow, une application de gestion de patients diabétiques. 
Tu peux aider les utilisateurs à:
- Naviguer dans l'application (accueil, clinique, patients, rendez-vous, aide à la décision)
- Ajouter des patients
- Créer des rendez-vous
- Accéder aux outils d'analyse (profilage, réadmission, instabilité, durée de séjour, traitement)

Si l'utilisateur demande d'ajouter un patient ou créer un rendez-vous, réponds simplement "ACTION:ajouter_patient" ou "ACTION:creer_rendez_vous".
Si l'utilisateur demande de naviguer vers une page, réponds avec "NAVIGATE:url" où url est le chemin de la page.
Pour les autres questions, réponds de manière utile et concise en français."""
        
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        bot_response = response.choices[0].message.content
        
        # Sauvegarder le message utilisateur et la réponse dans la base de données
        conn = db_config.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Récupérer l'user_id
                cursor.execute("SELECT id FROM users WHERE username = %s", (session['user']['username'],))
                user = cursor.fetchone()
                if user:
                    user_id = user['id']
                    # Sauvegarder le message utilisateur
                    cursor.execute(
                        "INSERT INTO chatbot_conversations (user_id, role, message) VALUES (%s, %s, %s)",
                        (user_id, 'user', user_message)
                    )
                    # Sauvegarder la réponse du bot
                    cursor.execute(
                        "INSERT INTO chatbot_conversations (user_id, role, message) VALUES (%s, %s, %s)",
                        (user_id, 'assistant', bot_response)
                    )
                    conn.commit()
        finally:
            conn.close()
        
        # Vérifier si c'est une action spéciale
        if bot_response.startswith("ACTION:"):
            action = bot_response.replace("ACTION:", "")
            return jsonify({'action': action, 'message': ''})
        elif bot_response.startswith("NAVIGATE:"):
            url = bot_response.replace("NAVIGATE:", "")
            return jsonify({'navigate': url, 'message': ''})
        
        return jsonify({'message': bot_response})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/chatbot/history', methods=['GET'])
def chatbot_history():
    """Route pour récupérer l'historique des conversations du chatbot"""
    if 'user' not in session:
        return jsonify({'error': 'Non connecté'}), 401
    
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Récupérer l'user_id
            cursor.execute("SELECT id FROM users WHERE username = %s", (session['user']['username'],))
            user = cursor.fetchone()
            if not user:
                return jsonify({'messages': []})
            
            user_id = user['id']
            # Récupérer les 50 derniers messages
            cursor.execute(
                "SELECT role, message, created_at FROM chatbot_conversations WHERE user_id = %s ORDER BY created_at ASC LIMIT 50",
                (user_id,)
            )
            messages = cursor.fetchall()
            
            return jsonify({'messages': messages})
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True)
