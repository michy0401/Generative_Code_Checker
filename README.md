# IA CodeReview - Frontend 🚀

Este proyecto corresponde a la interfaz de usuario del sistema generativo de revisión de código, desarrollado como parte de los entregables de la carrera de Ingeniería en Software y Negocios Digitales (ISND) en ESEN.

Está construido utilizando tecnologías web modernas enfocadas en el rendimiento, la escalabilidad y una experiencia de usuario fluida (UX/UI).

## 🛠️ Stack Tecnológico
* **Core:** React 18
* **Build Tool:** Vite
* **Lenguaje:** TypeScript (Modo Estricto)
* **Estilos:** Tailwind CSS
* **Autenticación:** Supabase Auth (JWT Asimétrico)
* **Comparación de Código:** react-diff-viewer-continued

## ⚙️ Requisitos Previos
Antes de iniciar, asegúrate de tener instalado:
* [Node.js](https://nodejs.org/) (Versión 18 o superior recomendada)
* npm o yarn

## 🚀 Instalación y Ejecución Local

1. Clona el repositorio y navega a la carpeta del frontend:
   ```bash
   cd frontend
Instala las dependencias del proyecto:
npm install

Configuración de Variables de Entorno:
El sistema requiere conexión a Supabase para gestionar la autenticación y las sesiones. Crea un archivo llamado .env.local en la raíz de la carpeta frontend y agrega las siguientes credenciales (solicítalas al administrador de la base de datos o revisa el documento de Arquitectura Técnica):

Fragmento de código
VITE_SUPABASE_URL="https://loglmdehedodfkrjmjnb.supabase.co"
VITE_SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxvZ2xtZGVoZWRvZGZrcmptam5iIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQyNjc0MDEsImV4cCI6MjA5OTg0MzQwMX0.pmedy0SOM-fpHmgPhNAFnZhfYg2Rr1rAPqRPtW-Ih70"

Levanta el servidor de desarrollo:
npm run dev

Abre tu navegador en http://localhost:5173.
(Nota: Asegúrate de que el backend de Flask esté corriendo simultáneamente en el puerto 5000 para que el flujo End-to-End funcione correctamente).


📖 Arquitectura de Rutas y Funcionalidades
El frontend implementa protección de rutas mediante un sistema de sesión persistente.

/review (Ruta Pública): Pantalla principal. Permite a los usuarios (anónimos o registrados) enviar fragmentos de código, seleccionar criterios de evaluación (seguridad, rendimiento, etc.) y visualizar el análisis dinámico generado por la IA (incluyendo el visor Diff y las explicaciones detalladas).

/login & /register (Rutas Públicas): Gestión de identidad de usuarios delegada a Supabase.

/dashboard (Ruta Protegida): Panel de control analítico que consume los endpoints del backend para mostrar métricas clave del uso de la IA (Tasa de Aceptación, Lenguaje Principal, Errores Comunes).

/history (Ruta Protegida): Tabla de trazabilidad y gestión documental. Permite visualizar el historial de revisiones del usuario y abrir un modal de "Evidencia Completa" con los prompts originales, el código evaluado y los comentarios humanos registrados.