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

Cada endpoint indica en `GET /api/docs` (Swagger, con el servidor corriendo) si la autenticacion
es opcional u obligatoria, y todos los codigos de respuesta posibles (incluyendo los `401`/`403`
relacionados a auth) - esa es la fuente de verdad para el detalle exacto endpoint por endpoint.
En resumen: la mayoria de los endpoints de lectura son publicos, `POST /api/review` y
`POST /api/reviews/<id>/regenerate` aceptan token opcional (cambia el comportamiento, no lo
bloquean), y `GET /api/reviews/mine` lo exige.

Una regla que **no** cambia entre endpoints: si se manda un `Authorization: Bearer <token>` y ese
token es invalido o expiro, el backend nunca lo trata como anonimo en silencio - corta con `401`.

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
