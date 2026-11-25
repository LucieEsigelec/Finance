-- ============================================================================
-- SCHEMA SUPABASE (PostgreSQL) — Portefeuille Actions 500 000 €
-- ============================================================================

-- 1. Référentiel des 5 actions du CAC 40
CREATE TABLE IF NOT EXISTS actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(16) UNIQUE NOT NULL,
    nom VARCHAR(100) NOT NULL,
    secteur VARCHAR(80) NOT NULL,
    dernier_cours NUMERIC(12, 2) NOT NULL DEFAULT 0,
    dividende_estime NUMERIC(10, 2) NOT NULL DEFAULT 0,
    maj_le TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Historique des cours (OHLCV) pour l'analyse graphique et les courbes
CREATE TABLE IF NOT EXISTS historique_cours (
    id BIGSERIAL PRIMARY KEY,
    action_id UUID NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
    date_seance DATE NOT NULL,
    open NUMERIC(12, 2),
    high NUMERIC(12, 2),
    low NUMERIC(12, 2),
    close NUMERIC(12, 2) NOT NULL,
    volume BIGINT,
    UNIQUE (action_id, date_seance)
);

-- 3. Ratios financiers (CA, dividende par action, rendement)
CREATE TABLE IF NOT EXISTS ratios_financiers (
    id BIGSERIAL PRIMARY KEY,
    action_id UUID NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
    date_maj DATE NOT NULL,
    chiffre_affaires NUMERIC(18, 2),
    dividende_par_action NUMERIC(10, 2),
    rendement_pct NUMERIC(6, 2)
);

-- 4. Actualités (Pilier majoritaire Informations & onglet « Infos sur l'action »)
CREATE TABLE IF NOT EXISTS actualites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_id UUID NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
    date_pub TIMESTAMPTZ NOT NULL,
    titre TEXT NOT NULL,
    source VARCHAR(100),
    url TEXT,
    resume TEXT,
    score_impact NUMERIC(5, 2) NOT NULL CHECK (score_impact BETWEEN 0 AND 100)
);

-- 5. Scores pré-calculés & prévisions hebdomadaires (cache < 2 s)
CREATE TABLE IF NOT EXISTS scores_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_id UUID NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
    date_calcul TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    score_global NUMERIC(5, 2) NOT NULL CHECK (score_global BETWEEN 0 AND 100),
    decision VARCHAR(10) NOT NULL CHECK (decision IN ('ACHAT', 'VENTE', 'RIEN')),
    prevision_semaine_pct NUMERIC(6, 2),
    details_piliers JSONB NOT NULL
);

-- 6. Portefeuille (500 000 € & référence hebdomadaire pour le garde-fou RG-01)
CREATE TABLE IF NOT EXISTS portefeuille (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capital_initial NUMERIC(14, 2) NOT NULL DEFAULT 500000.00,
    cash_disponible NUMERIC(14, 2) NOT NULL DEFAULT 500000.00 CHECK (cash_disponible >= 0),
    val_semaine_prec NUMERIC(14, 2) NOT NULL DEFAULT 500000.00,
    date_ref_semaine DATE NOT NULL DEFAULT CURRENT_DATE
);

-- 7. Historique des allers-retours (RG-05 : titres entiers, RG-06 : suivi 1 an)
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portefeuille_id UUID NOT NULL REFERENCES portefeuille(id) ON DELETE CASCADE,
    action_id UUID NOT NULL REFERENCES actions(id) ON DELETE RESTRICT,
    type_op VARCHAR(10) NOT NULL CHECK (type_op IN ('ACHAT', 'VENTE')),
    quantite_entiere INT NOT NULL CHECK (quantite_entiere > 0),
    prix_unitaire NUMERIC(12, 2) NOT NULL,
    montant_total NUMERIC(14, 2) NOT NULL,
    conseil_algo JSONB NOT NULL,
    date_execution TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- INDEX DE PERFORMANCE
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_hist_action_date   ON historique_cours(action_id, date_seance DESC);
CREATE INDEX IF NOT EXISTS idx_ratios_action_date ON ratios_financiers(action_id, date_maj DESC);
CREATE INDEX IF NOT EXISTS idx_news_action_date   ON actualites(action_id, date_pub DESC);
CREATE INDEX IF NOT EXISTS idx_scores_action_date ON scores_actions(action_id, date_calcul DESC);
CREATE INDEX IF NOT EXISTS idx_tx_pf_date         ON transactions(portefeuille_id, date_execution DESC);

-- ============================================================================
-- FONCTION SQL ATOMIQUE : executer_transaction()
-- Appelée via supabase.rpc('executer_transaction', ...) sur POST /api/transactions
-- Verrouille le portefeuille, revérifie RG-05, insère la transaction et met à jour le cash
-- ============================================================================
CREATE OR REPLACE FUNCTION executer_transaction(
    p_portefeuille UUID,
    p_action UUID,
    p_type TEXT,
    p_qte INT,
    p_conseil JSONB
)
RETURNS transactions
LANGUAGE plpgsql
AS $$
DECLARE
    v_prix NUMERIC(12, 2);
    v_cash NUMERIC(14, 2);
    v_detenu INT;
    v_tx transactions;
BEGIN
    IF p_type NOT IN ('ACHAT', 'VENTE') THEN
        RAISE EXCEPTION 'TYPE_OPERATION_INVALIDE';
    END IF;

    IF p_qte <= 0 THEN
        RAISE EXCEPTION 'QUANTITE_INVALIDE';
    END IF;

    -- Verrouillage exclusif de la ligne portefeuille pendant la transaction
    SELECT cash_disponible INTO v_cash
    FROM portefeuille
    WHERE id = p_portefeuille
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'PORTEFEUILLE_INTROUVABLE';
    END IF;

    -- Lecture du dernier cours connu
    SELECT dernier_cours INTO v_prix
    FROM actions
    WHERE id = p_action;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'ACTION_INTROUVABLE';
    END IF;

    -- Calcul de la position actuelle détenue sur ce titre
    SELECT COALESCE(
        SUM(CASE WHEN type_op = 'ACHAT' THEN quantite_entiere ELSE -quantite_entiere END),
        0
    )
    INTO v_detenu
    FROM transactions
    WHERE portefeuille_id = p_portefeuille AND action_id = p_action;

    -- Contrôles métier (RG-05)
    IF p_type = 'ACHAT' AND (p_qte * v_prix) > v_cash THEN
        RAISE EXCEPTION 'RG05_CASH_INSUFFISANT';
    END IF;

    IF p_type = 'VENTE' AND p_qte > v_detenu THEN
        RAISE EXCEPTION 'VENTE_SUPERIEURE_A_LA_POSITION';
    END IF;

    -- Insertion de l'aller-retour
    INSERT INTO transactions (
        portefeuille_id, action_id, type_op,
        quantite_entiere, prix_unitaire, montant_total, conseil_algo
    )
    VALUES (
        p_portefeuille, p_action, p_type,
        p_qte, v_prix, p_qte * v_prix, p_conseil
    )
    RETURNING * INTO v_tx;

    -- Mise à jour atomique du cash disponible
    UPDATE portefeuille
    SET cash_disponible = cash_disponible + (CASE WHEN p_type = 'ACHAT' THEN -1 ELSE 1 END) * (p_qte * v_prix)
    WHERE id = p_portefeuille;

    RETURN v_tx;
END;
$$;