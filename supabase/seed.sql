-- Insertion des 5 actions du périmètre (sans doublon si ré-exécuté)
INSERT INTO actions (ticker, nom, secteur, dernier_cours, dividende_estime)
VALUES
    ('DSY.PA', 'Dassault Systèmes', 'Logiciels industriels', 34.80, 0.29),
    ('RMS.PA', 'Hermès',            'Luxe',                  2150.00, 15.00),
    ('CAP.PA', 'Capgemini',         'Services numériques / IT', 155.00, 3.40),
    ('AI.PA',  'Air Liquide',       'Gaz industriels / Chimie', 162.00, 3.20),
    ('TTE.PA', 'TotalEnergies',     'Énergie / Pétrole & Gaz', 77.50, 3.80)
ON CONFLICT (ticker) DO NOTHING;

-- Initialisation du portefeuille client à 500 000 € (uniquement s'il n'existe pas déjà)
INSERT INTO portefeuille (capital_initial, cash_disponible, val_semaine_prec, date_ref_semaine)
SELECT 500000.00, 500000.00, 500000.00, CURRENT_DATE
WHERE NOT EXISTS (SELECT 1 FROM portefeuille);