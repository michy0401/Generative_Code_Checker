import { supabase } from '../supabaseClient';

export default async function apiFetch(endpoint: string, options: RequestInit = {}) {
  // 1. Obtenemos la sesión actual directamente de Supabase
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;

  // 2. Forzamos el tipo a Record<string, string> para poder inyectar llaves dinámicas
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };

  // 3. Si existe el token, inyectamos el Authorization Bearer
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // 4. Hacemos la petición al backend
  const response = await fetch(`http://localhost:5000${endpoint}`, {
    ...options,
    headers,
  });

  return response;
}