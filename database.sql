-- Script SQL pour créer la base de données GlycoFlow dans phpMyAdmin
-- Exécuter ce script dans phpMyAdmin pour créer la base de données et les tables

-- Créer la base de données
CREATE DATABASE IF NOT EXISTS glycoflow_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE glycoflow_db;

-- Table users (utilisateurs pour l'authentification)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    email VARCHAR(120) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table clusters (pour le profilage patients) - créée AVANT patients pour la FOREIGN KEY
CREATE TABLE IF NOT EXISTS clusters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(200) NOT NULL,
    description TEXT,
    taille INT DEFAULT 0,
    age_moyen DECIMAL(5,2),
    duree_sejour_moyenne DECIMAL(5,2),
    readmission_rate DECIMAL(5,2),
    change_rate DECIMAL(5,2),
    conditions_frequentes JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table patients
CREATE TABLE IF NOT EXISTS patients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    sexe VARCHAR(10) NOT NULL,
    date_naissance DATE,
    telephone VARCHAR(20),
    email VARCHAR(120),
    adresse TEXT,
    diabetes_type VARCHAR(50),
    date_diagnostic DATE,
    hba1c DECIMAL(5,2),
    glycemie DECIMAL(5,2),
    diabetes_med VARCHAR(10) DEFAULT 'No',
    traitement TEXT,
    admission_type VARCHAR(100),
    admission_type_id VARCHAR(10),
    time_in_hospital INT,
    num_lab_procedures INT,
    num_procedures INT,
    num_medications INT,
    number_outpatient INT,
    number_emergency INT,
    number_inpatient INT,
    number_diagnoses INT,
    discharge_disposition_id VARCHAR(10),
    admission_source_id VARCHAR(10),
    max_glu_serum VARCHAR(50),
    A1Cresult VARCHAR(50),
    race VARCHAR(50),
    cluster_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (cluster_id) REFERENCES clusters(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table rendez_vous
CREATE TABLE IF NOT EXISTS rendez_vous (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    medecin_id INT,
    date DATETIME NOT NULL,
    duree INT DEFAULT 30,
    type_rdv VARCHAR(50),
    motif TEXT,
    statut VARCHAR(20) DEFAULT 'planifie',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (medecin_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table predictions (historique des prédictions ML)
CREATE TABLE IF NOT EXISTS predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    modele VARCHAR(100) NOT NULL,
    type_prediction VARCHAR(50) NOT NULL,
    predicted_class INT,
    probability JSON,
    threshold DECIMAL(5,2),
    input_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table chatbot_conversations (historique des conversations du chatbot)
CREATE TABLE IF NOT EXISTS chatbot_conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    role VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insérer des données de test

-- Utilisateurs de test (mot de passe: password123)
INSERT INTO users (username, password_hash, role, email) VALUES
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5N7yq5z1Fq1W6', 'admin', 'admin@hospital.com'),
('medecin1', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5N7yq5z1Fq1W6', 'medecin', 'medecin1@hospital.com'),
('infirmier1', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5N7yq5z1Fq1W6', 'infirmier', 'infirmier1@hospital.com'),
('gestionnaire1', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5N7yq5z1Fq1W6', 'gestionnaire', 'gestionnaire1@hospital.com');

-- Clusters de test
INSERT INTO clusters (nom, description, taille, age_moyen, duree_sejour_moyenne, readmission_rate, change_rate, conditions_frequentes) VALUES
('Patients âgés avec comorbidités', 'Patients de plus de 65 ans avec multiples comorbidités', 234, 72.0, 8.5, 0.35, 0.42, '["Hypertension", "Maladies cardiovasculaires", "Insuffisance rénale"]'),
('Patients jeunes avec diabète de type 1', 'Patients de moins de 40 ans, diabète type 1', 156, 28.0, 5.2, 0.18, 0.28, '["Cétose", "Hypoglycémie", "Déséquilibre glycémique"]'),
('Patients avec complications sévères', 'Patients avec complications diabétiques avancées', 189, 58.0, 11.3, 0.48, 0.65, '["Neuropathie", "Rétinopathie", "Ulcères du pied"]'),
('Patients stables sous traitement', 'Patients bien contrôlés avec traitement stable', 321, 52.0, 3.8, 0.12, 0.15, '["Aucune complication majeure"]');

-- Patients de test - Commenté pour utiliser des données réelles
-- Les patients seront ajoutés via l'application ou importés depuis un fichier CSV réel
