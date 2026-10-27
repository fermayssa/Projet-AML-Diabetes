"""
Routes pour le module Clinique
"""
from flask import render_template, redirect, url_for, flash, request
from . import bp
import db_config
from modules.segmentation import service as seg
import json
from modules.segmentation import service as seg, triage as seg_triage

@bp.route('/')
def accueil():
    """Le dashboard clinique est celui des groupes de patients (module segmentation)."""
    return redirect(url_for('segmentation.dashboard'))

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
            cursor.execute("""
    SELECT r.*, CONCAT(p.prenom, ' ', p.nom) AS patient_nom
    FROM rendez_vous r
    LEFT JOIN patients p ON p.id = r.patient_id
    ORDER BY (r.urgence IS NULL), FIELD(r.urgence, 'urgent', 'priority', 'standard'), r.date
""")
            rendez_vous = cursor.fetchall()
    finally:
        conn.close()
    
    return render_template('rendez_vous.html', rendez_vous=rendez_vous)

@bp.route('/nouveau-patient')
def nouveau_patient():
    """Formulaire d'ajout de patient"""
    return render_template('nouveau_patient.html')

@bp.route('/nouveau-rendez-vous', methods=['GET', 'POST'])
def nouveau_rendez_vous():
    """Prise de RDV : calcule le groupe du patient et le niveau d'urgence."""
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM patients")
            patients = cursor.fetchall()

        error = None
        values = request.form.to_dict() if request.method == 'POST' else {}

        if request.method == 'POST':
            try:
                if not seg.is_ready():
                    raise ValueError("Le modèle de segmentation n'est pas disponible.")
                patient = next((p for p in patients if str(p['id']) == values.get('patient')), None)
                if not patient:
                    raise ValueError("Veuillez sélectionner un patient.")
                if not values.get('date') or not values.get('heure'):
                    raise ValueError("La date et l'heure sont obligatoires.")

                raw = seg.form_to_raw(request.form)          # valide les champs cliniques
                res = seg.predict_raw(raw)
                t = seg_triage.evaluate(raw, res['cluster'], values.get('type_rdv', ''))

                with conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO rendez_vous
                           (patient_id, date, duree, type_rdv, motif, notes,
                            cluster, urgence, score, raisons)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (patient['id'], f"{values['date']} {values['heure']}",
                         values.get('duree') or 30, values.get('type_rdv'),
                         values.get('motif'), values.get('notes'),
                         res['cluster'], t['level'], t['score'],
                         json.dumps(t['reasons'], ensure_ascii=False)))
                conn.commit()
                return render_template('rdv_resultat.html', patient=patient, res=res, t=t,
                                       date=values['date'], heure=values['heure'])
            except ValueError as exc:
                error = str(exc)
            except Exception as exc:
                conn.rollback()
                error = f"Erreur lors de l'enregistrement : {exc}"
    finally:
        conn.close()

        ctx = seg.form_context(values=values)
        ctx["error"] = error or ctx.get("error")     # notre message d'abord, sinon l'erreur du modèle
        return render_template('nouveau_rendez_vous.html', patients=patients, **ctx)

@bp.route('/patients/add', methods=['POST'])
def add_patient():
    """Ajouter un nouveau patient"""
    conn = db_config.get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO patients (nom, prenom, age, sexe, telephone, email, adresse, diabetes_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                request.form.get('nom'),
                request.form.get('prenom'),
                request.form.get('age'),
                request.form.get('sexe'),
                request.form.get('telephone'),
                request.form.get('email'),
                request.form.get('adresse'),
                request.form.get('diabetes_type')
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
                    request.form.get('nom'),
                    request.form.get('prenom'),
                    request.form.get('age'),
                    request.form.get('sexe'),
                    request.form.get('telephone'),
                    request.form.get('email'),
                    request.form.get('adresse'),
                    request.form.get('diabetes_type'),
                    request.form.get('date_naissance'),
                    request.form.get('hba1c'),
                    request.form.get('glycemie'),
                    request.form.get('traitement'),
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
