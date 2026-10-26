"""
Routes pour le module Clinique
"""
from flask import render_template, redirect, url_for, flash, request
from . import bp
import db_config

@bp.route('/')
def accueil():
    """Page d'accueil de la clinique"""
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM patients")
            patients_count = cursor.fetchone()['count']
            cursor.execute("SELECT COUNT(*) as count FROM rendez_vous")
            rendez_vous_count = cursor.fetchone()['count']
            cursor.execute("SELECT * FROM rendez_vous ORDER BY date LIMIT 3")
            rendez_vous = cursor.fetchall()
    finally:
        conn.close()
    
    return render_template('accueil.html', 
                         patients_count=patients_count,
                         rendez_vous_count=rendez_vous_count,
                         rendez_vous=rendez_vous)

@bp.route('/patients')
def patients():
    """Liste des patients"""
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM patients")
            patients = cursor.fetchall()
    finally:
        conn.close()
    
    # Return JSON if requested by chatbot
    if request.headers.get('Accept') == 'application/json' or request.args.get('json'):
        from flask import jsonify
        return jsonify(patients)
    
    return render_template('patients.html', patients=patients)

@bp.route('/patients/<int:patient_id>')
def patient_detail(patient_id):
    """Détails d'un patient"""
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
            patient = cursor.fetchone()
    finally:
        conn.close()
    
    if patient:
        return render_template('patient_detail.html', patient=patient)
    return redirect(url_for('clinique.patients'))

@bp.route('/rendez-vous')
def rendez_vous():
    """Liste des rendez-vous"""
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM rendez_vous ORDER BY date")
            rendez_vous = cursor.fetchall()
    finally:
        conn.close()
    
    return render_template('rendez_vous.html', rendez_vous=rendez_vous)

@bp.route('/nouveau-patient')
def nouveau_patient():
    """Formulaire d'ajout de patient"""
    return render_template('nouveau_patient.html')

@bp.route('/nouveau-rendez-vous')
def nouveau_rendez_vous():
    """Formulaire de prise de rendez-vous"""
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM patients")
            patients = cursor.fetchall()
    finally:
        conn.close()
    
    return render_template('nouveau_rendez_vous.html', patients=patients)

@bp.route('/patients/add', methods=['POST'])
def add_patient():
    """Ajouter un nouveau patient"""
    nom = request.form.get('nom', '').strip()
    prenom = request.form.get('prenom', '').strip()
    age = request.form.get('age')
    sexe = request.form.get('sexe')
    telephone = request.form.get('telephone', '').strip()
    email = request.form.get('email', '').strip()
    adresse = request.form.get('adresse', '').strip()
    diabetes_type = request.form.get('diabetes_type')
    
    # Validations côté serveur
    if not nom or len(nom) < 2 or len(nom) > 50:
        flash('Le nom doit contenir entre 2 et 50 caractères', 'error')
        return redirect(url_for('clinique.patients'))
    
    if not prenom or len(prenom) < 2 or len(prenom) > 50:
        flash('Le prénom doit contenir entre 2 et 50 caractères', 'error')
        return redirect(url_for('clinique.patients'))
    
    if not age or not age.isdigit() or int(age) < 0 or int(age) > 120:
        flash('L\'âge doit être entre 0 et 120', 'error')
        return redirect(url_for('clinique.patients'))
    
    if sexe not in ['M', 'F']:
        flash('Sexe invalide', 'error')
        return redirect(url_for('clinique.patients'))
    
    if telephone and (not telephone.isdigit() or len(telephone) != 10):
        flash('Le téléphone doit contenir exactement 10 chiffres', 'error')
        return redirect(url_for('clinique.patients'))
    
    if email and not ('@' in email and '.' in email):
        flash('Format d\'email invalide', 'error')
        return redirect(url_for('clinique.patients'))
    
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO patients (nom, prenom, age, sexe, telephone, email, adresse, diabetes_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                nom, prenom, int(age), sexe,
                telephone if telephone else None,
                email if email else None,
                adresse if adresse else None,
                diabetes_type
            ))
        conn.commit()
        flash('Patient ajouté avec succès!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erreur lors de l\'ajout: {e}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('clinique.patients'))

@bp.route('/patients/<int:patient_id>/edit', methods=['GET', 'POST'])
def edit_patient(patient_id):
    """Modifier un patient"""
    conn = db_config.get_db_connection()
    try:
        if request.method == 'POST':
            nom = request.form.get('nom', '').strip()
            prenom = request.form.get('prenom', '').strip()
            age = request.form.get('age')
            sexe = request.form.get('sexe')
            telephone = request.form.get('telephone', '').strip()
            email = request.form.get('email', '').strip()
            adresse = request.form.get('adresse', '').strip()
            diabetes_type = request.form.get('diabetes_type')
            date_naissance = request.form.get('date_naissance')
            hba1c = request.form.get('hba1c')
            glycemie = request.form.get('glycemie')
            traitement = request.form.get('traitement', '').strip()
            
            # Validations côté serveur
            if not nom or len(nom) < 2 or len(nom) > 50:
                flash('Le nom doit contenir entre 2 et 50 caractères', 'error')
                return redirect(url_for('clinique.edit_patient', patient_id=patient_id))
            
            if not prenom or len(prenom) < 2 or len(prenom) > 50:
                flash('Le prénom doit contenir entre 2 et 50 caractères', 'error')
                return redirect(url_for('clinique.edit_patient', patient_id=patient_id))
            
            if not age or not age.isdigit() or int(age) < 0 or int(age) > 120:
                flash('L\'âge doit être entre 0 et 120', 'error')
                return redirect(url_for('clinique.edit_patient', patient_id=patient_id))
            
            if sexe not in ['M', 'F', 'A']:
                flash('Sexe invalide', 'error')
                return redirect(url_for('clinique.edit_patient', patient_id=patient_id))
            
            if telephone and (not telephone.isdigit() or len(telephone) != 10):
                flash('Le téléphone doit contenir exactement 10 chiffres', 'error')
                return redirect(url_for('clinique.edit_patient', patient_id=patient_id))
            
            if email and not ('@' in email and '.' in email):
                flash('Format d\'email invalide', 'error')
                return redirect(url_for('clinique.edit_patient', patient_id=patient_id))
            
            if hba1c:
                try:
                    hba1c_float = float(hba1c)
                    if hba1c_float < 3 or hba1c_float > 15:
                        flash('L\'HbA1c doit être entre 3 et 15%', 'error')
                        return redirect(url_for('clinique.edit_patient', patient_id=patient_id))
                except ValueError:
                    flash('L\'HbA1c doit être un nombre', 'error')
                    return redirect(url_for('clinique.edit_patient', patient_id=patient_id))
            
            if glycemie:
                try:
                    glycemie_float = float(glycemie)
                    if glycemie_float < 0.5 or glycemie_float > 5:
                        flash('La glycémie doit être entre 0.5 et 5 g/L', 'error')
                        return redirect(url_for('clinique.edit_patient', patient_id=patient_id))
                except ValueError:
                    flash('La glycémie doit être un nombre', 'error')
                    return redirect(url_for('clinique.edit_patient', patient_id=patient_id))
            
            with conn.cursor() as cursor:
                sql = """
                    UPDATE patients SET
                        nom = %s, prenom = %s, age = %s, sexe = %s,
                        telephone = %s, email = %s, adresse = %s, diabetes_type = %s,
                        date_naissance = %s, hba1c = %s, glycemie = %s,
                        traitement = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                cursor.execute(sql, (
                    nom, prenom, int(age), sexe,
                    telephone if telephone else None,
                    email if email else None,
                    adresse if adresse else None,
                    diabetes_type,
                    date_naissance if date_naissance else None,
                    float(hba1c) if hba1c else None,
                    float(glycemie) if glycemie else None,
                    traitement if traitement else None,
                    patient_id
                ))
            conn.commit()
            flash('Patient modifié avec succès!', 'success')
            return redirect(url_for('clinique.patients'))
        else:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
                patient = cursor.fetchone()
    finally:
        conn.close()
    
    if not patient:
        flash('Patient non trouvé', 'error')
        return redirect(url_for('clinique.patients'))
    
    return render_template('edit_patient.html', patient=patient)

@bp.route('/patients/<int:patient_id>/delete', methods=['POST'])
def delete_patient(patient_id):
    """Supprimer un patient"""
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM patients WHERE id = %s", (patient_id,))
        conn.commit()
        flash('Patient supprimé avec succès!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erreur lors de la suppression: {e}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('clinique.patients'))

@bp.route('/rendez-vous/add', methods=['POST'])
def add_rendez_vous():
    """Ajouter un nouveau rendez-vous"""
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO rendez_vous (patient_id, date, duree, type_rdv, motif)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                request.form.get('patient_id'),
                request.form.get('date'),
                request.form.get('duree', 30),
                request.form.get('type_rdv'),
                request.form.get('motif')
            ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return str(e), 400
    finally:
        conn.close()
    
    return '', 200

@bp.route('/rendez-vous/<int:rdv_id>/edit', methods=['GET', 'POST'])
def edit_rendez_vous(rdv_id):
    """Modifier un rendez-vous"""
    conn = db_config.get_db_connection()
    try:
        if request.method == 'POST':
            with conn.cursor() as cursor:
                sql = """
                    UPDATE rendez_vous SET
                        patient_id = %s, date = %s, duree = %s,
                        type_rdv = %s, motif = %s, statut = %s,
                        notes = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                cursor.execute(sql, (
                    request.form.get('patient_id'),
                    request.form.get('date'),
                    request.form.get('duree'),
                    request.form.get('type_rdv'),
                    request.form.get('motif'),
                    request.form.get('statut'),
                    request.form.get('notes'),
                    rdv_id
                ))
            conn.commit()
            flash('Rendez-vous modifié avec succès!', 'success')
            return redirect(url_for('clinique.rendez_vous'))
        else:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM rendez_vous WHERE id = %s", (rdv_id,))
                rdv = cursor.fetchone()
                cursor.execute("SELECT * FROM patients")
                patients = cursor.fetchall()
    finally:
        conn.close()
    
    if not rdv:
        flash('Rendez-vous non trouvé', 'error')
        return redirect(url_for('clinique.rendez_vous'))
    
    return render_template('edit_rendez_vous.html', rdv=rdv, patients=patients)

@bp.route('/rendez-vous/<int:rdv_id>/delete', methods=['POST'])
def delete_rendez_vous(rdv_id):
    """Supprimer un rendez-vous"""
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM rendez_vous WHERE id = %s", (rdv_id,))
        conn.commit()
        flash('Rendez-vous supprimé avec succès!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erreur lors de la suppression: {e}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('clinique.rendez_vous'))
