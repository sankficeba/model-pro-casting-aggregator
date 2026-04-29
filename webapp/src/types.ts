// TypeScript-типы, соответствующие Pydantic-схемам в api/schemas.py
// и api/reference_data.py.

export interface RefItem {
  code: string;
  label: string;
}

export interface Refs {
  genders: RefItem[];
  project_types: RefItem[];
  role_types: RefItem[];
  ethnicity: RefItem[];
  body_type: RefItem[];
  hair_colors: RefItem[];
  hair_lengths: RefItem[];
  education: RefItem[];
  tax_status: RefItem[];
  eye_colors: RefItem[];
  marks: RefItem[];
  skills_sport: RefItem[];
  skills_dance: RefItem[];
  skills_vocal: RefItem[];
  skills_instruments: RefItem[];
}

export interface Profile {
  user_id?: number;
  // Step 1
  full_name?: string | null;
  gender?: "male" | "female" | null;
  city?: string | null;
  ready_for_travel: boolean;
  actual_age?: number | null;
  play_age_min?: number | null;
  play_age_max?: number | null;
  // Step 2
  project_types: string[];
  role_types: string[];
  min_rate?: number | null;
  show_negotiable: boolean;
  show_noncommercial: boolean;
  show_agency: boolean;
  // Step 3
  height_cm?: number | null;
  clothing_size?: number | null;
  shoe_size?: number | null;
  ethnicity: string[];
  body_type: string[];
  hair_color?: string | null;
  hair_length?: string | null;
  // Step 4
  has_experience?: boolean | null;
  education?: string | null;
  tax_status?: string | null;
  // Step 5
  eye_color?: string | null;
  marks: string[];
  skills_sport: string[];
  skills_dance: string[];
  skills_vocal: string[];
  skills_instruments: string[];
  // Step 6
  portfolio_url?: string | null;
  video_url?: string | null;
  professional_url?: string | null;
  phone?: string | null;
  vk_url?: string | null;
  email?: string | null;
  // meta
  completion_pct: number;
}

export interface MeResponse {
  user_id: number;
  username: string | null;
  is_admin: boolean;
}

export interface AdminStats {
  profiles_total: number;
  profiles_completed: number;
  messages_total: number;
  messages_casting: number;
  notifications_total: number;
  notifications_success: number;
}

export interface AdminProfileRow {
  user_id: number;
  full_name: string | null;
  gender: string | null;
  city: string | null;
  actual_age: number | null;
  project_types: string[];
  role_types: string[];
  email: string | null;
  completed_at: string | null;
  updated_at: string;
}

export interface AdminVacancyRow {
  id: number;
  idx: number;
  role_types: string[];
  gender: string | null;
  age_min: number | null;
  age_max: number | null;
  rate: number | null;
  ethnicity: string[];
  height_min: number | null;
  height_max: number | null;
  body_type: string[];
  hair_color: string[];
  hair_length: string[];
  description: string | null;
  role_label: string | null;
}

export interface AdminMessageRow {
  id: number;
  tg_chat_username: string | null;
  tg_message_id: number;
  text: string;
  is_casting: boolean;
  project_types: string[];
  city: string | null;
  summary: string | null;
  confidence: number;
  received_at: string;
  notified_count: number;
  vacancies: AdminVacancyRow[];
}

export const EMPTY_PROFILE: Profile = {
  ready_for_travel: false,
  project_types: [],
  role_types: [],
  show_negotiable: false,
  show_noncommercial: true,
  show_agency: true,
  ethnicity: [],
  body_type: [],
  marks: [],
  skills_sport: [],
  skills_dance: [],
  skills_vocal: [],
  skills_instruments: [],
  completion_pct: 0,
};
