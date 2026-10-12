export interface Farmer {
  id: number
  login: string
  full_name: string
  shop_name: string
  region: string
}

export interface ActionItem {
  id: number
  day: string
  rule_key: string
  type: string
  title: string
  why: string
  plan: string[]
  effect_note: string
  effect_weekly: number
  confidence: number
  urgency: number
  score: number
  facts: Record<string, unknown>
  payload: Record<string, any>
  texts_source: 'llm' | 'template'
  status: 'proposed' | 'completed' | 'rejected'
  rejection_reason?: string | null
  feedback?: string | null
}

export interface TodayData {
  date: string
  actions: ActionItem[]
  candidates_found: number
  candidates_passed: number
  llm: { enabled: boolean; model: string }
}

export interface Overview {
  revenue_7d: number
  revenue_7d_prev: number
  revenue_trend: number
  orders_7d: number
  avg_check: number
  new_clients_30d: number
  repeat_clients: number
  assistant_effect: number
}

export interface ProductRow {
  id: number
  name: string
  category: string
  unit: string
  price: number
  stock: number
  expires_at: string | null
  velocity: number
  cover_days: number | null
  description_len: number
  photo_count: number
}

export interface CardRow {
  id: number
  name: string
  category: string
  price: number
  photo_count: number
  description_len: number
  views_14d: number
  cart_14d: number
  ctr: number
  quality: number
}

export interface SalesData {
  by_day: { day: string; revenue: number; orders: number }[]
  top_products: { name: string; category: string; qty: number; revenue: number }[]
  by_category: { category: string; revenue: number }[]
}

export interface PromotionRow {
  id: number
  title: string
  description: string
  scope: 'marketplace' | 'shop'
  discount_pct: number
  category: string | null
  starts_at: string
  ends_at: string
  joined: boolean
  status: string
  result_revenue: number | null
  result_uplift_pct: number | null
}

export interface ClientsData {
  segments: { key: string; name: string; count: number; spent: number }[]
  lapsed_count: number
  lapsed_avg_silence: number
  top: { ext_ref: string; segment: string; orders: number; spent: number; last_order: string }[]
}

export interface JournalData {
  metrics: {
    proposed: number
    completed: number
    rejected: number
    completed_effect_weekly: number
    accepted_rate: number
    useful_votes: number
  }
  actions: (ActionItem & { status_name: string })[]
}

export interface RulesData {
  formula: string
  filters: string[]
  rules: { key: string; name: string; signal: string; data: string; effect: string }[]
}

export const TYPE_META: Record<string, { name: string; color: string }> = {
  weak_card: { name: 'Слабая карточка', color: '#fa8c16' },
  sales_drop: { name: 'Падение продаж', color: '#fa541c' },
  expiry_risk: { name: 'Скоропорт', color: '#f5222d' },
  stock_imbalance: { name: 'Запасы', color: '#faad14' },
  churn_risk: { name: 'Отток клиентов', color: '#722ed1' },
  promo_gap: { name: 'Акция маркетплейса', color: '#2f54eb' },
  pricing: { name: 'Цена', color: '#13c2c2' },
}

export const URGENCY_LABEL: Record<number, { label: string; color: string }> = {
  1: { label: 'Запланировать', color: 'default' },
  2: { label: 'Важно сегодня', color: 'orange' },
  3: { label: 'Срочно', color: 'red' },
}

export const REJECT_REASONS = [
  'Не согласен с расчётом эффекта',
  'Не могу сейчас',
  'Уже сделал по-своему',
  'Не актуально',
]
