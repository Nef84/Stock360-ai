// ── Auth ──────────────────────────────────────────────────────────────────────
export type UserRole = 'admin' | 'supervisor' | 'agent';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

// ── Product ───────────────────────────────────────────────────────────────────
export interface Product {
  id: number;
  name: string;
  category: string;
  description: string | null;
  price: number;
  cost: number;
  stock: number;
  reserved: number;
  available_stock: number;
  margin_pct: number;
  sku: string | null;
  image_url: string | null;
  is_active: boolean;
  ai_priority: number;
  updated_at: string;
}

export interface ProductCreate {
  name: string;
  category: string;
  description?: string;
  price: number;
  cost: number;
  stock: number;
  margin_pct: number;
  ai_priority: number;
  sku?: string;
}

export interface ProductImportResult {
  created: number;
  updated: number;
  skipped: number;
  errors: string[];
}

// ── Customer ──────────────────────────────────────────────────────────────────
export type Channel = 'whatsapp' | 'messenger' | 'web' | 'manual';

export interface Customer {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  channel: Channel;
  total_spent: number;
  created_at: string;
}

// ── Conversation ──────────────────────────────────────────────────────────────
export type ConversationStatus = 'open' | 'in_progress' | 'escalated' | 'closed';

export interface Conversation {
  id: number;
  customer: Customer;
  channel: Channel;
  status: ConversationStatus;
  ai_active: boolean;
  assigned_to: number | null;
  tags: string[] | null;
  created_at: string;
  updated_at: string;
}

// ── Message ───────────────────────────────────────────────────────────────────
export type MessageSource = 'customer' | 'ai' | 'agent' | 'system';

export interface Message {
  id: number;
  conversation_id: number;
  content: string;
  source: MessageSource;
  sender_id: number | null;
  created_at: string;
  is_read: boolean;
}

export interface AIChatResponse {
  message: Message;
  ai_response: Message;
  sale_detected: boolean;
  sale_id: number | null;
  escalated: boolean;
}

// ── Sale ──────────────────────────────────────────────────────────────────────
export type SaleStatus = 'pending' | 'confirmed' | 'shipped' | 'delivered' | 'cancelled';

export interface Sale {
  id: number;
  product: Product;
  customer: Customer;
  quantity: number;
  unit_price: number;
  total: number;
  status: SaleStatus;
  closed_by_ai: boolean;
  created_at: string;
}

// ── Analytics ─────────────────────────────────────────────────────────────────
export interface DashboardStats {
  ai_sales_today: number;
  total_sales_today: number;
  clients_served_ai: number;
  conversion_rate: number;
  avg_response_ms: number;
  open_conversations: number;
  escalated_today: number;
}

export interface SalesByDay {
  day: string;
  ai: number;
  human: number;
}

export interface TopProduct {
  product_id: number;
  product_name: string;
  units_sold: number;
  revenue: number;
  pct: number;
}

// ── API Error ─────────────────────────────────────────────────────────────────
export interface ApiError {
  detail: string;
}
