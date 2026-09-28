export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); this.name = 'ApiError'; }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1${path}`, { ...options, headers: { 'content-type': 'application/json', ...options.headers }, credentials: 'same-origin', cache: 'no-store' });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const details = body.error?.details?.map((d: { message: string }) => d.message).join('; ');
    throw new ApiError(details || body.detail || body.error?.message || `Request failed (${response.status})`, response.status);
  }
  return body as T;
}

export type Role = 'CITIZEN' | 'VOLUNTEER' | 'ORGANIZATION' | 'OPERATOR' | 'ADMIN';
export type User = { id: string; name: string; email: string; role: Role; verified: boolean; available: boolean; capacity: number; categories: string[]; skills: string[]; languages: string[]; transport: string | null; latitude: number | null; longitude: number | null };
export type Event = { id: string; from_status: string | null; to_status: string; reason: string; evidence_url: string | null; system_notes: string | null; confidence: number | null; created_at: string };
export type Need = { id: string; owner_id: string; category: string; description: string; status: string; verification: string; urgency: string; priority_reason: string; quantity: number | null; unit: string | null; deadline: string | null; location_text: string; latitude: number | null; longitude: number | null; location_precision: string; visibility_scope: string; privacy_mode: boolean; details: Record<string, string>; created_at: string; updated_at: string; events: Event[]; evidence: { id: string; name: string; mime_type: string; size: number; url: string }[]; assignment: { id: string; resource_id: string | null; volunteer_id: string | null; status: string; rationale: string } | null; outcome: { summary: string; evidence_url: string | null; verified_at: string | null; impact_value: number | null; impact_unit: string | null } | null; feedback: { answer: 'YES' | 'NO' | 'PARTIALLY'; comment: string; created_at: string } | null };
export type Organization = { id: string; name: string; description: string; status: string; service_categories: string[]; service_area: string; created_at: string; membership_role?: 'OWNER' | 'MEMBER' };
export type Resource = { id: string; organization_id: string; organization_name: string; title: string; description: string; category: string; capacity: number; current_workload: number; remaining_capacity: number; available: boolean; available_from: string | null; available_until: string | null; expires_at: string | null; service_radius_km: number; latitude: number | null; longitude: number | null };
export type Notification = { id: string; request_id: string | null; kind: string; title: string; body: string; read_at: string | null; created_at: string };
export type Candidate = { type: 'resource' | 'volunteer'; id: string; name: string; organization?: string; score: number; distance_km: number | null; why: string[]; interested?: boolean };
