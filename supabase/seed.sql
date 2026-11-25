-- Données initiales — reprend les lignes présentes dans la base en ligne le 2026-11-25.
-- Rejouable : ne crée aucun doublon (CLAUDE.md §6.2). Les cours sont provisoires :
-- ils seront remplacés par le premier POST /api/market/refresh (yfinance).

insert into actions (ticker, nom, secteur, dernier_cours, dividende_estime) values
  ('DSY.PA', 'Dassault Systèmes', 'Logiciels industriels',     34.80,  0.29),
  ('RMS.PA', 'Hermès',            'Luxe',                    2150.00, 15.00),
  ('CAP.PA', 'Capgemini',         'Services numériques / IT', 155.00,  3.40),
  ('AI.PA',  'Air Liquide',       'Gaz industriels / Chimie', 162.00,  3.20),
  ('TTE.PA', 'TotalEnergies',     'Énergie / Pétrole & Gaz',   77.50,  3.80)
on conflict (ticker) do nothing;

-- Un seul portefeuille de 500 000 € (valeurs par défaut de la table).
insert into portefeuille (capital_initial, cash_disponible, val_semaine_prec)
select 500000.00, 500000.00, 500000.00
where not exists (select 1 from portefeuille);
