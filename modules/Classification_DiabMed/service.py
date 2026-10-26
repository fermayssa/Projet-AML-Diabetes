"""
Service pour le module Classification_DiabMed
"""
import os
import joblib

class ClassificationService:
    """Service de classification pour patients diabétiques"""
    
    def __init__(self):
        self.model = None
        self.model_path = os.path.join(os.path.dirname(__file__), 'artifacts', 'model.joblib')
        self.load_model()
    
    def load_model(self):
        """Charger le modèle de classification"""
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
    
    def predict(self, features):
        """Prédire la classe du patient"""
        if self.model is None:
            raise ValueError("Modèle non chargé")
        return self.model.predict([features])
