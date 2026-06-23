// AgriSage SDK — Déclarations TypeScript
// Version : 1.0.0

export interface AgriSageClientConfig {
  /** Clé API (préfixe as_test_ ou as_live_) */
  apiKey: string;
  /** URL de base personnalisée */
  baseUrl?: string;
  /** Utiliser le sandbox (données fictives) */
  sandbox?: boolean;
  /** Langue par défaut des réponses : 'fr' | 'ar' */
  lang?: 'fr' | 'ar';
  /** Timeout en millisecondes (défaut : 30 000) */
  timeout?: number;
  /** Nombre de tentatives en cas d'erreur réseau ou 5xx (défaut : 2) */
  maxRetries?: number;
  /** Activer les logs de debug */
  debug?: boolean;
}

export interface RateLimit {
  limit: number | null;
  remaining: number | null;
  reset: string | null;
}

export interface ApiResponse<T> {
  data: T;
  rateLimit: RateLimit;
}

export interface Pagination {
  page: number;
  par_page: number;
  total: number;
  pages_total: number;
}

// ── Schémas métier ────────────────────────────────────────────────────────────

export interface Dose {
  valeur: number;
  unite: 'kg/ha' | 'L/ha' | 'g/ha' | 'mL/ha' | 'g/plant' | 'mL/plant';
}

export type RisqueAbeilles = 'très faible' | 'faible' | 'modéré' | 'élevé';
export type RisqueAuxiliaires = 'faible' | 'modéré' | 'élevé';

export interface AlternativeProduit {
  produit: string;
  matiere_active: string;
  groupe_frac: string;
  dar: number;
  dose: Dose;
}

export interface Conseil {
  conseil_id: string;
  produit: string;
  matiere_active: string;
  numero_amm: string;
  dose: Dose;
  dar: number;
  volume_bouillie: string;
  groupe_frac: string | null;
  groupe_irac: string | null;
  groupe_hrac: string | null;
  homologue_onssa: true;
  conforme_globalgap: boolean;
  lmr_ue_respectee: boolean | null;
  risque_abeilles: RisqueAbeilles;
  risque_auxiliaires: RisqueAuxiliaires;
  alertes: string[];
  alternatives: AlternativeProduit[];
  timestamp: string;
}

export interface ProduitONSSA {
  id: string;
  nom_commercial: string;
  titulaire: string;
  numero_amm: string;
  matieres_actives: Array<{ nom: string; teneur: string }>;
  formulation: string;
  usage: 'fongicide' | 'insecticide' | 'herbicide' | 'nematicide' | 'acaricide' | 'molluscicide';
  cultures_homologuees: string[];
  dar: number;
  statut: 'homologué' | 'retiré' | 'suspendu';
  date_homologation: string;
  date_expiration: string;
}

export interface TraitementResponse {
  traitement_id: string;
  statut: 'enregistré' | 'alerte_dar' | 'alerte_produit';
  dar_restant: number;
  alertes: string[];
}

export interface GroupeResistance {
  type: 'irac' | 'frac' | 'hrac';
  numero: string;
  nom: string;
  mecanisme_action: string;
  risque_resistance: 'faible' | 'modéré' | 'élevé' | 'très élevé';
  recommandation_rotation: string;
  matieres_actives: string[];
}

export interface Alerte {
  alerte_id: string;
  type: 'DAR_DEPASSE' | 'PRODUIT_RETIRE' | 'LMR_MODIFIEE' | 'ROTATION_REQUISE' | 'ZNT_VIOLATION';
  urgence: 'critique' | 'élevée' | 'modérée' | 'information';
  message: string;
  parcelle_id: string;
  traitement_id: string;
  action_recommandee: string;
  date_alerte: string;
  lue: boolean;
}

export interface Culture {
  id: string;
  nom_fr: string;
  nom_ar: string;
  famille: string;
  nb_produits_homologues: number;
}

// ── Paramètres des méthodes ───────────────────────────────────────────────────

export type Stade = 'germination' | 'levee' | 'vegetation' | 'floraison' | 'fructification' | 'recolte' | 'post-recolte';
export type Region = 'souss-massa' | 'gharb-chrarda' | 'marrakech-safi' | 'fes-meknes' | 'tanger-tetouan' | 'oriental' | 'rabat-sale-kenitra' | 'beni-mellal-khenifra' | 'draa-tafilalet' | 'laayoune-sakia';

export interface ConseilParams {
  culture: string;
  ravageur: string;
  stade: Stade;
  region?: Region;
  darMax?: number;
  globalgap?: boolean;
  exportUe?: boolean;
  historiqueFrac?: string[];
  historiqueIrac?: string[];
  nbAlternatives?: number;
  lang?: 'fr' | 'ar';
}

export interface ProduitsListParams {
  culture?: string;
  usage?: 'fongicide' | 'insecticide' | 'herbicide' | 'nematicide' | 'acaricide' | 'molluscicide';
  ma?: string;
  statut?: 'homologue' | 'retire' | 'tous';
  groupeFrac?: string;
  groupeIrac?: string;
  page?: number;
  lang?: 'fr' | 'ar';
}

export interface TraitementParams {
  parcelleId: string;
  produitNom: string;
  doseAppliquee: Dose;
  dateTraitement: string;
  conseilId?: string;
  culture?: string;
  numeroAmm?: string;
  surfaceTraitee?: number;
  dateRecoltePrevue?: string;
  operateur?: string;
  epiPortes?: string[];
  conditionsMeteo?: {
    temperatureC?: number;
    ventKmh?: number;
    hygrometriePct?: number;
  };
  notes?: string;
}

export interface CarnetParams {
  parcelleId?: string;
  du?: string;
  au?: string;
  format?: 'json' | 'pdf';
  page?: number;
}

export interface GroupesParams {
  type: 'irac' | 'frac' | 'hrac';
  groupe?: string;
  ma?: string;
  risque?: 'faible' | 'modéré' | 'élevé' | 'très élevé';
  lang?: 'fr' | 'ar';
}

export interface AlertesParams {
  type?: 'DAR_DEPASSE' | 'PRODUIT_RETIRE' | 'LMR_MODIFIEE' | 'ROTATION_REQUISE' | 'ZNT_VIOLATION';
  urgence?: 'critique' | 'élevée' | 'modérée' | 'information';
  lue?: boolean;
  parcelleId?: string;
  page?: number;
}

// ── Ressources ────────────────────────────────────────────────────────────────

export declare class ConseilResource {
  generer(params: ConseilParams): Promise<ApiResponse<Conseil>>;
}

export declare class ProduitsResource {
  lister(params?: ProduitsListParams): Promise<ApiResponse<{ data: ProduitONSSA[]; pagination: Pagination }>>;
  obtenir(id: string, lang?: 'fr' | 'ar'): Promise<ApiResponse<ProduitONSSA>>;
}

export declare class TraitementResource {
  enregistrer(params: TraitementParams): Promise<ApiResponse<TraitementResponse>>;
}

export declare class CarnetResource {
  obtenir(params?: CarnetParams): Promise<ApiResponse<{ data: TraitementResponse[]; pagination: Pagination } | Buffer>>;
  exporterPdf(params?: Omit<CarnetParams, 'format'>): Promise<Buffer>;
}

export declare class GroupesResource {
  lister(params: GroupesParams): Promise<ApiResponse<{ data: GroupeResistance[]; total: number }>>;
  irac(params?: Omit<GroupesParams, 'type'>): Promise<ApiResponse<{ data: GroupeResistance[]; total: number }>>;
  frac(params?: Omit<GroupesParams, 'type'>): Promise<ApiResponse<{ data: GroupeResistance[]; total: number }>>;
  hrac(params?: Omit<GroupesParams, 'type'>): Promise<ApiResponse<{ data: GroupeResistance[]; total: number }>>;
}

export declare class AlertesResource {
  lister(params?: AlertesParams): Promise<ApiResponse<{ data: Alerte[]; non_lues: number; pagination: Pagination }>>;
  marquerLue(id: string): Promise<ApiResponse<{ alerte_id: string; lue: true }>>;
  nonLues(params?: Omit<AlertesParams, 'lue'>): Promise<ApiResponse<{ data: Alerte[]; non_lues: number; pagination: Pagination }>>;
  critiques(params?: Omit<AlertesParams, 'urgence'>): Promise<ApiResponse<{ data: Alerte[]; non_lues: number; pagination: Pagination }>>;
}

export declare class CulturesResource {
  lister(params?: { q?: string; lang?: 'fr' | 'ar' }): Promise<ApiResponse<{ data: Culture[]; total: number }>>;
  rechercher(terme: string, lang?: 'fr' | 'ar'): Promise<ApiResponse<{ data: Culture[]; total: number }>>;
}

// ── Client principal ──────────────────────────────────────────────────────────

export declare class AgriSageClient {
  conseil:    ConseilResource;
  produits:   ProduitsResource;
  traitement: TraitementResource;
  carnet:     CarnetResource;
  groupes:    GroupesResource;
  alertes:    AlertesResource;
  cultures:   CulturesResource;

  constructor(config: AgriSageClientConfig);
}

// ── Erreurs ───────────────────────────────────────────────────────────────────

export declare class AgriSageError extends Error {
  code: string;
  statusCode: number | null;
  requestId: string | null;
  suggestion: string | null;
}
export declare class AuthenticationError extends AgriSageError {}
export declare class PlanLimitError extends AgriSageError {}
export declare class QuotaExceededError extends AgriSageError { resetAt: string | null; }
export declare class NotFoundError extends AgriSageError {}
export declare class ValidationError extends AgriSageError {}
export declare class NetworkError extends AgriSageError { originalError: Error | null; }

// ── Constantes ────────────────────────────────────────────────────────────────

export declare const STADES: Readonly<Record<string, Stade>>;
export declare const REGIONS: Readonly<Record<string, Region>>;
export declare const USAGES: Readonly<Record<string, string>>;
export declare const ALERTES_TYPES: Readonly<Record<string, string>>;
