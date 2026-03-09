// Shared TypeScript types used by both web and mobile clients

export interface Stop {
  id: string;
  address: string;
  latitude: number;
  longitude: number;
  acknowledged: boolean;
}

export interface Route {
  id: string;
  date: string; // ISO date string yyyy-mm-dd
  vehicleId?: string;
  stops: Stop[];
}

export interface LoginResponse {
  token: string;
}

export interface AcknowledgeResponse {
  success: boolean;
}

export interface CreateJobRequest {
  customerName: string;
  address: string;
  latitude?: number;
  longitude?: number;
  description?: string;
}

export interface CreateJobResponse {
  jobId: string;
}
