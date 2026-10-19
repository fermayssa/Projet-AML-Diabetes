import numpy as np
import pandas as pd
import joblib
from flask import Flask, request, render_template

app = Flask(__name__)

# Chargement du modèle et du préprocesseur
model = joblib.load('model.pkl')
preprocessor = joblib.load('preprocessor.pkl')

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    if request.method == 'POST':
        data = {
            'gender': request.form.get('gender', 'Male'),
            'race': request.form.get('race', 'Caucasian'),
            'time_in_hospital': float(request.form.get('time_in_hospital', 3)),
            'max_glu_serum': request.form.get('max_glu_serum', 'None'),
            'A1Cresult': request.form.get('A1Cresult', 'None'),
            'num_lab_procedures': float(request.form['num_lab_procedures']),
            'num_procedures': float(request.form['num_procedures']),
            'num_medications': float(request.form['num_medications']),
            'number_diagnoses': float(request.form['number_diagnoses']),
            'number_inpatient': np.log1p(float(request.form['number_inpatient'])),
            'number_outpatient': np.log1p(float(request.form['number_outpatient'])),
            'number_emergency': np.log1p(float(request.form['number_emergency'])),
            'age_num': float(request.form['age']),
            'num_med_changes': float(request.form['num_med_changes']),
            'num_active_meds': float(request.form['num_active_meds']),
            'admission_type': request.form['admission_type'],
            'admission_source': request.form['admission_source'],
            'discharge_disposition': request.form['discharge_disposition'],
            'diag_1': request.form['diag_1'],
            'diag_2': request.form['diag_2'],
            'diag_3': request.form['diag_3'],
            'medical_specialty': request.form['medical_specialty']
        }

        # Transformer en DataFrame
        input_df = pd.DataFrame([data])

        # Appliquer le préprocesseur (Création de input_prepared)
        input_prepared = preprocessor.transform(input_df)

        # Effectuer la prédiction
        prediction = model.predict(input_prepared)[0]
        probability = model.predict_proba(input_prepared)[0][1]

        if prediction == 1:
            result_text = "Changement de médicament recommandé (Changement de traitement)"
        else:
            result_text = "Pas de changement de médicament (Traitement maintenu)"

        prob_text = f"{probability * 100:.2f}%"

        return render_template('index.html', prediction_text=result_text, probability_text=prob_text)
if __name__ == '__main__':
    app.run(debug=True)