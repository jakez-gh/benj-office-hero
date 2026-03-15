import { client } from './index';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthUser {
  id: string;
  email: string;
  role: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: AuthUser;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface RefreshResponse {
  access_token: string;
  user: AuthUser;
}

export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  const response = await client.post<LoginResponse>('/auth/login', credentials);
  return response.data;
}

export async function refresh(request: RefreshRequest): Promise<RefreshResponse> {
  const response = await client.post<RefreshResponse>('/auth/refresh', request);
  return response.data;
}

export async function logout(request: { refresh_token: string }): Promise<void> {
  await client.post('/auth/logout', request);
}
