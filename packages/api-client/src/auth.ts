import { client } from './index';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
}

export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  const response = await client.post<LoginResponse>('/auth/login', credentials);
  return response.data;
}
