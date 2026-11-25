import type * as React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** primary = action principale de l'écran (une seule) · secondary = défaut · ghost = action discrète · buy / sell = validation d'un achat ou d'une vente */
  variant?: 'primary' | 'secondary' | 'ghost' | 'buy' | 'sell';
  size?: 'md' | 'sm';
}
export declare function Button(props: ButtonProps): React.ReactElement;

export interface DecisionBadgeProps {
  /** Conseil renvoyé par l'API (scores_actions.decision) */
  decision: 'ACHAT' | 'VENTE' | 'RIEN';
  size?: 'md' | 'lg';
}
export declare function DecisionBadge(props: DecisionBadgeProps): React.ReactElement;

export interface KpiCardProps {
  label: string;
  /** Valeur déjà formatée, ex. « 512 340 € » */
  value: string;
  /** Variation en %, ex. 2.47 ; le signe et la couleur sont calculés */
  delta?: number;
  deltaLabel?: string;
  /** Texte secondaire quand il n'y a pas de variation */
  hint?: string;
}
export declare function KpiCard(props: KpiCardProps): React.ReactElement;

export interface AlertBannerProps {
  /** niveau_alerte renvoyé par GET /api/dashboard */
  level: 'AUCUN' | 'APPROCHE' | 'ATTEINT';
  /** variation_hebdo_pct, ex. -8.1 */
  variation: number;
}
export declare function AlertBanner(props: AlertBannerProps): React.ReactElement | null;

export interface AmountInputProps {
  id?: string;
  label?: string;
  value: string;
  onChange?: React.ChangeEventHandler<HTMLInputElement>;
  /** Cash disponible, affiché en aide sous le champ */
  cash?: number;
  /** Message d'erreur ; remplace l'aide */
  error?: string;
}
export declare function AmountInput(props: AmountInputProps): React.ReactElement;

export interface StockCheckboxProps {
  name: string;
  ticker: string;
  /** Nom du token de couleur du titre : chart-dsy, chart-tte, chart-cap, chart-rms, chart-ai */
  color?: string;
  checked?: boolean;
  onChange?: React.ChangeEventHandler<HTMLInputElement>;
}
export declare function StockCheckbox(props: StockCheckboxProps): React.ReactElement;

export interface ForecastBarProps {
  /** prevision_semaine_pct, en % */
  defavorable: number;
  central: number;
  favorable: number;
  /** Montant investi : ajoute l'équivalent en euros */
  montant?: number;
}
export declare function ForecastBar(props: ForecastBarProps): React.ReactElement;

export interface AdviceCardProps {
  nom: string;
  ticker: string;
  cours: number;
  conseil: 'ACHAT' | 'VENTE' | 'RIEN';
  verdict: 'VALIDER' | 'NE_RIEN_FAIRE' | 'PRIVILEGIER_VENTE' | 'CONSERVER' | 'REFUSE';
  quantite: number;
  montant: number;
  reliquat: number;
  dividende: number;
  prevision?: { defavorable: number; central: number; favorable: number };
  raisons?: string[];
  /** Boutons d'action sous la carte */
  children?: React.ReactNode;
}
export declare function AdviceCard(props: AdviceCardProps): React.ReactElement;

declare global {
  interface Window {
    Pf500: {
      Button: typeof Button; DecisionBadge: typeof DecisionBadge; KpiCard: typeof KpiCard; AlertBanner: typeof AlertBanner;
      AmountInput: typeof AmountInput; StockCheckbox: typeof StockCheckbox; ForecastBar: typeof ForecastBar; AdviceCard: typeof AdviceCard;
      format: { eur(n: number, noDecimals?: boolean): string; pct(n: number): string; int(n: number): string };
    };
  }
}
