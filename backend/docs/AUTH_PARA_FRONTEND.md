# Autenticacion: que hace el backend y que tiene que hacer el frontend

## Resumen

**El backend no tiene login.** No existe `/api/signup`, `/api/login` ni nada
parecido. El signup/login se hace 100% desde el frontend, hablando directo
con Supabase Auth via `supabase-js`.

El backend solo hace una cosa con la autenticacion: **si el request trae un
JWT de Supabase, lo valida y lo usa para identificar al estudiante.** Si no
trae ninguno, sigue funcionando en modo anonimo, exactamente como ya
funcionaba antes de que existiera login.

## Que tiene que hacer el frontend

1. Signup / login con `supabase-js`, por ejemplo:

   ```js
   const { data, error } = await supabase.auth.signInWithPassword({ email, password });
   const accessToken = data.session.access_token;
   ```

2. En cada request al backend, si el usuario esta logueado, mandar ese token asi:

   ```
   Authorization: Bearer <access_token>
   ```

   Por ejemplo con `fetch`:

   ```js
   fetch("http://localhost:5000/api/review", {
     method: "POST",
     headers: {
       "Content-Type": "application/json",
       ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
     },
     body: JSON.stringify({ language, exercise, level, review_type, student_code }),
   });
   ```

3. Si el usuario **no** esta logueado, simplemente no mandar el header
   `Authorization`. No es obligatorio loguearse para usar `/api/review` -
   el backend sigue usando `session_id` para agrupar el historial anonimo,
   igual que antes.

## Que endpoints requieren token y cuales no

| Endpoint | Token requerido | Comportamiento |
|---|---|---|
| `POST /api/review` | Opcional | Sin token: funciona anonimo con `session_id` (igual que siempre). Con token valido: la revision queda asociada al `student_id` del usuario. Con token invalido/expirado: `401`. |
| `GET /api/reviews/<id>` | No | Publico, no cambia. |
| `GET /api/reviews?session_id=...` | No | Historial anonimo por sesion, no cambia. |
| `GET /api/reviews/mine` | **Si, obligatorio** | Devuelve el historial del estudiante logueado. Sin token, o con token invalido: `401`. |

## Errores que puede devolver el backend por temas de auth

- **401** con `{"error": "Token invalido o expirado."}` si el `Authorization: Bearer <token>` que se manda no es valido (mal formado, firma incorrecta, o vencido). El backend nunca lo trata como anonimo en silencio: si mandaste un token, se valida.
- **401** con `{"error": "Se requiere autenticacion."}` en `GET /api/reviews/mine` si no se manda ningun token.

## Detalle tecnico (por si hace falta debuggear)

Este proyecto de Supabase usa el modelo nuevo de llaves asimetricas (ECC
P-256, algoritmo `ES256`) - no hay ningun secreto compartido involucrado. El
backend valida la firma del JWT contra la llave publica del proyecto, que
descarga del endpoint JWKS de Supabase Auth
(`${SUPABASE_URL}/auth/v1/.well-known/jwks.json`), exigiendo
`aud: "authenticated"` (el claim que Supabase pone en los tokens de usuarios
logueados). Esto no cambia nada para el frontend: seguis mandando el
`access_token` de la sesion tal cual te lo da `supabase-js`, sin importar
que algoritmo se use para firmarlo. El `student_id` que usa el backend es el
claim `sub` del token, que coincide con `auth.users.id` / `public.students.id`.
