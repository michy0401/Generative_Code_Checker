# IA CodeReview - Documento Funcional (Frontend)

Este proyecto corresponde a la interfaz de usuario del sistema generativo de revisión de código, desarrollado como parte de los entregables de la carrera de Ingeniería en Software y Negocios Digitales en ESEN.

Está construido utilizando tecnologías web modernas (Vite, React, TypeScript, Tailwind CSS) enfocadas en el rendimiento y una experiencia de usuario fluida.

## Requisitos Previos e Instalación Local
Asegúrate de tener Node.js (v18+) instalado.
1. `cd frontend`
2. `npm install`
3. Crea un archivo `.env.local` con las variables:
    `VITE_SUPABASE_URL="https://loglmdehedodfkrjmjnb.supabase.co"`
    `VITE_SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxvZ2xtZGVoZWRvZGZrcmptam5iIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQyNjc0MDEsImV4cCI6MjA5OTg0MzQwMX0.pmedy0SOM-fpHmgPhNAFnZhfYg2Rr1rAPqRPtW-Ih70"`
4. `npm run dev` para levantar el servidor en el puerto `5173`.

## Arquitectura de Rutas y Casos Principales
El frontend implementa protección de rutas mediante un sistema de sesión (Supabase Auth y LocalStorage para usuarios anónimos).

* **`/review` (Ruta Pública - Camino Principal):** Permite a cualquier estudiante enviar fragmentos de código (máximo 20,000 caracteres) y seleccionar criterios de evaluación específicos. Renderiza el análisis dinámico generado por la IA (hallazgos, pruebas, explicaciones) e incluye un visor de diferencias (DiffViewer).
* **`/login` & `/register` (Rutas Públicas):** Gestión de identidad de usuarios.
* **`/dashboard` (Ruta Protegida):** Panel analítico que muestra métricas globales (Tasa de Aceptación, Lenguaje Principal, Errores Comunes).
* **`/history` (Ruta Protegida):** Tabla de trazabilidad que permite visualizar el historial de revisiones del usuario y abrir la evidencia completa del diagnóstico.

## Reglas de Negocio (Control Humano RF-08)
El sistema exige trazabilidad de las decisiones del desarrollador sobre las sugerencias de la IA. Desde la vista de revisión, el usuario cuenta con 4 acciones:
1. **Aceptar:** Registra el código de la IA como válido (`status: 'accepted'`).
2. **Descartar:** Rechaza la sugerencia de la IA (`status: 'discarded'`).
3. **Comentar:** Permite añadir feedback cualitativo al diagnóstico sin alterar la decisión previa (mantiene el `status` intacto).
4. **Regenerar:** Solicita una segunda opinión a la IA, creando una nueva revisión hija vinculada a la petición original.