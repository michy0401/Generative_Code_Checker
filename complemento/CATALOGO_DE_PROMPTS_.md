# Catálogo de Prompts del Sistema

## Información del Documento

- **Proyecto:** Generative Code Checker (Backend LLM API)
- **Módulo principal:** `services/llm_connector.py`
- **Versión global del prompt:** `PROMPT_VERSION = "1.2"`
- **Historial de cambios:** `docs/PROMPT_CHANGELOG.md`
- **Autor / Rol:** Erick Alexander Bernal — AI Engineer & Prompt Architect (Persona 3)  

---

## 1. Marco Teórico y Restricciones Pedagógicas del Sistema

El módulo de Inteligencia Artificial de *Generative Code Checker* no opera como un simple generador de código, sino como un **Tutor Pedagógico de Ingeniería de Software**. Para garantizar un aprendizaje significativo y evitar la dependencia ciega en el modelo, se han incorporado las siguientes restricciones obligatorias dentro de la arquitectura de prompts y en el conector (`services/llm_connector.py`):

1. **Principio de No Validación Ficticia (R1):** El LLM tiene estrictamente prohibido afirmar o garantizar que el código enviado "funciona correctamente en producción" únicamente basándose en la inferencia estática de texto. Debe advertir al estudiante que el código requiere validación en un entorno de ejecución real.
2. **Clasificación Taxativa y Modular (R2):** La retroalimentación debe desglosarse de forma segregada en categorías claras:
   * **Errores (`findings` / `severity: high|critical`):** Fallos de sintaxis, errores de ejecución o lógica rota.
   * **Mejoras (`findings` / `severity: medium`):** Optimización de rendimiento, refactorización y reducción de complejidad.
   * **Recomendaciones (`findings` / `severity: low`):** Buenas prácticas de diseño, legibilidad, nombrado e ingeniería.
3. **Prevención de Alucinaciones y Aislamiento de Seguridad (R3):** Si el análisis detecta vulnerabilidades críticas (como Inyección SQL, XSS o falta de sanitización), estas deben aislarse y destacarse explícitamente dentro del arreglo de `warnings` y en los `findings` de seguridad.
4. **Contrato de Salida Estricto (R4):** La respuesta del modelo debe ajustarse al 100% al esquema JSON definido en `schemas/response_schema.json`. Cualquier respuesta no parseable activa mecanismos defensivos de reintento.

---

## 2. Ficha Técnica Completa: Prompt #1 — `SYSTEM_PROMPT` Base

### 2.1 Objetivo
Establecer el rol del LLM como un Ingeniero de Software Senior enfocado en la revisión educativa de código. Su propósito es analizar el fragmento de código enviado por el estudiante según el tipo de revisión seleccionado (`Errores`, `Seguridad basica`, `Legibilidad`, `Rendimiento`), aplicando las restricciones pedagógicas del sistema, calculando una puntuación cualitativa (`score`) y forzando la salida en un formato JSON estricto.

### 2.2 Versión
`1.2` (Definido en la constante `PROMPT_VERSION` de `services/llm_connector.py`).

### 2.3 Estructura del System Prompt (`llm_connector.py`)

```text
Actuas como un Ingeniero de Software Senior especializado en revision de codigo con enfoque educativo.
Tu objetivo es analizar el codigo proporcionado por un estudiante de programacion y generar una evaluacion estructurada, precisa y orientada al aprendizaje.

REGLAS DE EVALUACION Y FORMATO:
1. Responde UNICAMENTE en formato JSON plano, sin bloques de codigo markdown (no uses ```json), sin explicaciones fuera del JSON.
2. La estructura del JSON DEBE cumplir estrictamente con el siguiente esquema:
   - summary: { overall_assessment: string, score: integer (0-100) }
   - findings: array de objetos { severity: "high"|"medium"|"low", type: string, title: string, description: string }
   - explanations: array de objetos { why: string, impact: string, how_to_fix: string }
   - suggested_code: { improved_code: string, changes_summary: string }
   - suggested_tests: array de strings con casos de prueba sugeridos
   - warnings: array de strings con advertencias pedagógicas o de seguridad
3. RESTRICCIÓN PEDAGÓGICA OBLIGATORIA: NUNCA afirmes que el codigo funciona al 100%. Debes incluir en 'warnings' una nota indicando que el codigo debe ser validado en un entorno de ejecucion real.
4. Ajusta el tono y la profundidad segun el nivel del estudiante (Basico, Intermedio, Avanzado) y enfócate en el 'review_type' solicitado.

```

### 2.4 Ejemplo de Entrada Real (Caso 1 de QA: Sintaxis Básica)

* **Endpoint:** `POST /api/review`

* **Payload JSON:**

```json
{
  "language": "Python",
  "exercise": "Calcular el promedio de una lista de notas",
  "level": "Basico",
  "review_type": "Errores",
  "student_code": "def calcular_promedio(notas)\n    total = sum(notas)\n    return total / len(notas)"
}

```

### 2.5 Ejemplo de Salida Real (Caso 1 de QA: Respuesta de la API)

* **HTTP Status:** `200 OK`

* **JSON de Respuesta:**

```json
{
  "summary": {
    "overall_assessment": "El codigo presenta un error de sintaxis fundamental que impide que el interprete de Python ejecute el script, ademas de un posible caso de borde si la lista de notas esta vacia.",
    "score": 60
  },
  "findings": [
    {
      "severity": "high",
      "type": "Error",
      "title": "Falta de dos puntos (:) al definir la funcion",
      "description": "La sentencia de definicion de la funcion carece del caracter de dos puntos al final de la linea."
    },
    {
      "severity": "medium",
      "type": "Error",
      "title": "Division por cero potencial",
      "description": "Si la lista de notas pasada como argumento esta vacia, len(notas) devolvera 0, lo que causara una excepcion de tipo ZeroDivisionError."
    }
  ],
  "explanations": [
    {
      "why": "En la sintaxis del lenguaje Python, todas las estructuras de control y definiciones de funciones deben terminar con dos puntos (:) para indicar el inicio de un bloque de codigo indentado.",
      "impact": "El codigo genera un error de sintaxis (SyntaxError) al momento de ser interpretado, evitando por completo que el programa inicie su ejecucion.",
      "how_to_fix": "Agrega dos puntos al final de la linea de definicion de la funcion, quedando de la siguiente manera: def calcular_promedio(notas):"
    },
    {
      "why": "Matematicamente y computacionalmente, no es posible dividir un numero entre cero. Al utilizar len(notas) como divisor sin validar previamente el contenido de la lista, se asume que siempre habra elementos.",
      "impact": "Si un usuario o funcion externa invoca calcular_promedio([]) enviando una lista vacia, el programa se detendra abruptamente lanzando una excepcion no controlada.",
      "how_to_fix": "Implementa una validacion condicional antes de realizar la operacion para verificar si la longitud de la lista es mayor a cero, y retorna un valor por defecto (como 0) en caso contrario."
    }
  ],
  "suggested_code": {
    "improved_code": "def calcular_promedio(notas):\n    if not notas:\n        return 0\n    total = sum(notas)\n    return total / len(notas)",
    "changes_summary": "Se agregaron los dos puntos (:) al final de la declaracion de la funcion en la linea 1. Se agrego una validacion para verificar si la lista esta vacia y prevenir un error de division por cero."
  },
  "suggested_tests": [
    "Prueba con lista de notas validas: Pasar [80, 90, 100]. -> Resultado esperado: 90.0.",
    "Prueba con lista vacia: Pasar []. -> Resultado esperado: Retornar 0 en lugar de lanzar excepcion."
  ],
  "warnings": [
    "Asegurate de revisar siempre el uso de los dos puntos al definir funciones y estructuras de control en Python.",
    "Ten en cuenta los casos de borde (como entradas vacias o nulas) al diseñar tus funciones.",
    "El codigo debe ser validado en un entorno de ejecucion real."
  ]
}

```

---

## 3. Ficha Técnica Completa: Prompt #2 — Bloque de Contexto de Regeneración (`previous_review` / `motivo_regeneracion`)

### 3.1 Objetivo

Reinyectar el contexto completo de una revisión previamente almacenada (`previous_review`) junto con la justificación o duda expresada explícitamente por el usuario (`motivo_regeneracion`) cuando se invoca el endpoint `POST /api/reviews/<id>/regenerate`. Este prompt permite reevaluar el código original ampliando el espectro de análisis hacia dimensiones adicionales (por ejemplo, evaluar eficiencia o legibilidad sobre un código que originalmente solo se revisó por errores de lógica).

### 3.2 Versión

`1.2` (Inyectado dinámicamente por la función `analizar_codigo` en `services/llm_connector.py`).

### 3.3 Estructura de Inyección del Contexto de Regeneración

```text
[CONTEXTO DE REGENERACIÓN SOLICITADA POR EL USUARIO]
El estudiante ha solicitado una reevaluación del código analizado anteriormente.
REVISIÓN ANTERIOR (Resumen):
- Evaluacion previa: {previous_review.summary.overall_assessment}
- Score previo: {previous_review.summary.score}
- Hallazgos previos: {previous_review.findings}

MOTIVO DE REGENERACIÓN EXPRESADO POR EL USUARIO:
"{motivo_regeneracion}"

INSTRUCCIÓN ESPECIAL PARA ESTA REGENERACIÓN:
Toma en cuenta la revision anterior y responde directamente a la inquietud o motivo planteado por el usuario. Ajusta la evaluacion, agrega nuevos hallazgos si la consulta lo requiere y actualiza el codigo sugerido para abordar tanto los problemas originales como el nuevo motivo especificado. Mantén la salida estrictamente bajo el JSON Schema requerido.

```

### 3.4 Ejemplo de Entrada Real (Caso 5 de QA: Regeneración sobre Detección de Primos)

* **Endpoint:** `POST /api/reviews/9dd24dd5-3820-43d2-9718-32ee1638e9b3/regenerate`

* **Código Base Analizado (`student_code`):**

```python
def es_primo(n):
    if n < 2:
        return False
    for i in range(2, n):
        if n % i == 0:
            return True
    return False

```

* **Payload JSON Enviado por el Estudiante:**

```json
{
  "motivo_regeneracion": "Quiero confirmar si detecta también el problema de eficiencia además del bug de lógica"
}

```

### 3.5 Ejemplo de Salida Real (Caso 5 de QA: Respuesta Regenerada por la API)

* **HTTP Status:** `200 OK`

* **JSON de Respuesta:**

```json
{
  "summary": {
    "overall_assessment": "El código presenta dos problemas principales: un error crítico de lógica en el retorno del bucle que clasifica erróneamente a los números compuestos como primos, y una oportunidad de mejora significativa en la eficiencia algorítmica al evaluar divisores innecesarios más allá de la raíz cuadrada del número.",
    "score": 40
  },
  "findings": [
    {
      "severity": "high",
      "type": "Error",
      "title": "Retorno incorrecto dentro del bucle de validación",
      "description": "Dentro de la iteración, cuando se encuentra un divisor exacto (n % i == 0), la función retorna True en lugar de False."
    },
    {
      "severity": "medium",
      "type": "Improvement",
      "title": "Baja eficiencia en el rango de búsqueda de divisores",
      "description": "El bucle recorre todos los números desde 2 hasta n-1, lo que genera una complejidad temporal de O(n), cuando es suficiente evaluar hasta la raíz cuadrada de n."
    }
  ],
  "explanations": [
    {
      "why": "Ocurre porque se programó 'return True' al detectar que el número es divisible por 'i', lo cual es la definición de un número compuesto (no primo), no de un número primo.",
      "impact": "Provoca que la función devuelva resultados completamente equivocados, por ejemplo, afirmando que el número 4 es primo.",
      "how_to_fix": "Cámbialo para que retorne False cuando se encuentre un divisor exacto, ya que esto demuestra que el número no es primo."
    },
    {
      "why": "Ocurre porque si un número 'n' tiene un divisor mayor que su raíz cuadrada, necesariamente debe tener otro divisor menor o igual a su raíz cuadrada.",
      "impact": "Para números grandes, realizar tantas iteraciones innecesarias degrada el rendimiento de la aplicación (complejidad O(n) en lugar de O(sqrt(n))).",
      "how_to_fix": "Ajusta el rango del bucle para que termine en la raíz cuadrada de n más uno, utilizando por ejemplo math.isqrt(n) + 1 o n**0.5."
    }
  ],
  "suggested_code": {
    "improved_code": "import math\n\ndef es_primo(n):\n    if n < 2:\n        return False\n    for i in range(2, math.isqrt(n) + 1):\n        if n % i == 0:\n            return False\n    return True",
    "changes_summary": "Se corrigió el retorno dentro del bucle para devolver False cuando se encuentra un divisor exacto. Se ajustó el límite superior del bucle hasta la raíz cuadrada del número para optimizar la eficiencia temporal."
  },
  "suggested_tests": [
    "Prueba con números menores a 2: Evaluar es_primo(1) -> Resultado esperado: False.",
    "Prueba con un número primo conocido: Evaluar es_primo(7) -> Resultado esperado: True.",
    "Prueba con un número compuesto: Evaluar es_primo(4) -> Resultado esperado: False."
  ],
  "warnings": [
    "Asegúrate de importar el módulo math si decides utilizar math.isqrt para calcular la raíz cuadrada de forma entera y segura.",
    "El código debe ser validado en un entorno de ejecución real."
  ]
}

```

---

## 4. Ficha Técnica Completa: Prompt #3 — Bloque de Few-Shot Examples (`FEW_SHOT_EXAMPLES`)

### 4.1 Objetivo

Funcionar como un mecanismo de fallback defensivo contra alucinaciones de formato. **Este bloque solo se activa condicionalmente si el primer intento de llamada al LLM falla la validación del esquema** (`jsonschema.validate` contra `schemas/response_schema.json`). Al activarse, la función `analizar_codigo` reescribe el prompt adjuntando la constante `FEW_SHOT_EXAMPLES` declarada en `services/llm_connector.py` para forzar visualmente al modelo a alinearse con la estructura esperada.

### 4.2 Versión

`1.2` (Constante `FEW_SHOT_EXAMPLES` exportada en `services/llm_connector.py`).

### 4.3 Definición de la Constante `FEW_SHOT_EXAMPLES` en Código (`services/llm_connector.py`)

```python
FEW_SHOT_EXAMPLES = """
[EJEMPLO DE REFERENCIA DE ENTRADA Y SALIDA ESPERADA]

Entrada de Ejemplo:
Lenguaje: Python | Nivel: Intermedio | Tipo: Seguridad basica
Ejercicio: Buscar un usuario en la base de datos por nombre
Código:
def buscar_usuario(cursor, nombre_usuario):
    query = "SELECT * FROM usuarios WHERE nombre = '" + nombre_usuario + "'"
    cursor.execute(query)
    return cursor.fetchall()

Salida JSON Esperada (Cumpliendo el Schema):
{
  "summary": {
    "overall_assessment": "El codigo cumple con su objetivo logico pero presenta una vulnerabilidad critica de seguridad por inyeccion SQL.",
    "score": 40
  },
  "findings": [
    {
      "severity": "high",
      "type": "Error",
      "title": "Vulnerabilidad de Inyeccion SQL (SQL Injection)",
      "description": "La consulta SQL se construye concatenando directamente la variable 'nombre_usuario' sin sanitizacion."
    }
  ],
  "explanations": [
    {
      "why": "Se utiliza concatenacion de cadenas para insertar datos de entrada directamente en la instruccion SQL.",
      "impact": "Permite a un atacante ejecutar comandos SQL arbitrarios en la base de datos.",
      "how_to_fix": "Usar consultas parametrizadas pasando los valores en una tupla en el metodo execute."
    }
  ],
  "suggested_code": {
    "improved_code": "def buscar_usuario(cursor, nombre_usuario):\n    query = \"SELECT * FROM usuarios WHERE nombre = %s\"\n    cursor.execute(query, (nombre_usuario,))\n    return cursor.fetchall()",
    "changes_summary": "Se reemplazo la concatenacion de strings por una consulta parametrizada con %s."
  },
  "suggested_tests": [
    "buscar_usuario(cursor, 'admin')"
  ],
  "warnings": [
    "Asegurate de que el driver de base de datos soporte el marcador de posicion adecuado (%s o ?).",
    "El codigo debe ser validado en un entorno de ejecucion real."
  ]
}
"""

```

### 4.4 Ejemplo de Entrada Real (Ejemplo de Referencia Inyectado al Prompt en Reintento)

```text
[PROMPT REFORZADO CON FEW-SHOT EXAMPLES ACTIVADO POR FALLA DE VALIDACIÓN]

{SYSTEM_PROMPT}

{FEW_SHOT_EXAMPLES}

[TAREA ACTUAL A EVALUAR]
Analiza el siguiente código para el lenguaje Python, nivel Intermedio, enfocado en 'Seguridad basica':

def buscar_usuario(cursor, nombre_usuario):
    query = "SELECT * FROM usuarios WHERE nombre = '" + nombre_usuario + "'"
    cursor.execute(query)
    return cursor.fetchall()

```

### 4.5 Ejemplo de Salida Real (Garantizada tras la Inyección Few-Shot — Caso 2 de QA)

* **HTTP Status:** `200 OK`

* **JSON de Respuesta:**

```json
{
  "summary": {
    "overall_assessment": "El codigo cumple con su objetivo logico de consultar la base de datos, pero presenta una vulnerabilidad critica de seguridad debido a la construccion de consultas SQL mediante concatenacion de cadenas.",
    "score": 40
  },
  "findings": [
    {
      "severity": "high",
      "type": "Error",
      "title": "Vulnerabilidad de Inyeccion SQL (SQL Injection)",
      "description": "La consulta SQL se construye concatenando directamente la variable 'nombre_usuario' sin ningun tipo de sanitizacion o parametrizacion."
    },
    {
      "severity": "medium",
      "type": "Improvement",
      "title": "Falta de manejo de excepciones",
      "description": "No se contemplan bloques try-except para capturar posibles errores de conexion o fallos durante la ejecucion de la consulta en la base de datos."
    }
  ],
  "explanations": [
    {
      "why": "Ocurre porque se utiliza concatenacion de cadenas (operador +) para insertar datos ingresados por el usuario directamente dentro de la sentencia SQL.",
      "impact": "Un usuario malintencionado podria introducir codigo SQL manipulado en la variable 'nombre_usuario' para alterar la consulta, obteniendo acceso no autorizado, modificando o eliminando datos de la base de datos.",
      "how_to_fix": "Utilizar consultas parametrizadas pasando los valores como una tupla o lista separada en el metodo execute del cursor, en lugar de concatenar cadenas."
    },
    {
      "why": "Ocurre porque la funcion asume que la base de datos siempre respondera correctamente sin que ocurran interrupciones de conexion o errores de sintaxis externos.",
      "impact": "Si ocurre un error en la base de datos, la aplicacion puede detenerse abruptamente (crash) o filtrar informacion sensible del sistema a traves del rastreo de errores.",
      "how_to_fix": "Envolver la ejecucion de la base de datos en un bloque try-except para manejar los errores de forma adecuada y asegurar el cierre de recursos si es necesario."
    }
  ],
  "suggested_code": {
    "improved_code": "def buscar_usuario(cursor, nombre_usuario):\n    query = \"SELECT * FROM usuarios WHERE nombre = %s\"\n    try:\n        cursor.execute(query, (nombre_usuario,))\n        return cursor.fetchall()\n    except Exception as e:\n        print(f\"Error al buscar el usuario: {e}\")\n        return []",
    "changes_summary": "Se reemplazo la concatenacion de cadenas por una consulta parametrizada usando '%s' para prevenir la inyeccion SQL. Se agrego un bloque try-except para manejar de forma segura los errores posibles durante la ejecucion de la consulta."
  },
  "suggested_tests": [
    "Prueba de busqueda normal: Llamar pasando 'Juan'. -> Resultado esperado: Retornar lista con registros coincidentes.",
    "Prueba de inyeccion SQL basica: Llamar pasando \"' OR '1'='1\". -> Resultado esperado: Tratar el input literalmente y retornar lista vacia."
  ],
  "warnings": [
    "Asegurate de que el conector de base de datos que utilices soporte el marcador de posicion adecuado (por ejemplo, '%s' para MySQL/PostgreSQL o '?' para SQLite).",
    "Recuerda que este codigo no ha sido ejecutado en un entorno real y debes probarlo junto con tu conexion a la base de datos.",
    "El codigo debe ser validado en un entorno de ejecucion real."
  ]
}

```

---

## 5. JSON Schema de Respuesta (`schemas/response_schema.json`)

Para garantizar la interoperabilidad con el frontend y validar que las respuestas del LLM cumplan con el contrato técnico sin romper la interfaz, se utiliza el siguiente archivo de esquema (`schemas/response_schema.json`):

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ReviewResponse",
  "type": "object",
  "required": [
    "summary",
    "findings",
    "explanations",
    "suggested_code",
    "suggested_tests",
    "warnings"
  ],
  "properties": {
    "summary": {
      "type": "object",
      "required": ["overall_assessment", "score"],
      "properties": {
        "overall_assessment": { "type": "string" },
        "score": { "type": "integer", "minimum": 0, "maximum": 100 }
      }
    },
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["severity", "type", "title", "description"],
        "properties": {
          "severity": { "type": "string", "enum": ["high", "medium", "low"] },
          "type": { "type": "string" },
          "title": { "type": "string" },
          "description": { "type": "string" }
        }
      }
    },
    "explanations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["why", "impact", "how_to_fix"],
        "properties": {
          "why": { "type": "string" },
          "impact": { "type": "string" },
          "how_to_fix": { "type": "string" }
        }
      }
    },
    "suggested_code": {
      "type": "object",
      "required": ["improved_code", "changes_summary"],
      "properties": {
        "improved_code": { "type": "string" },
        "changes_summary": { "type": "string" }
      }
    },
    "suggested_tests": {
      "type": "array",
      "items": { "type": "string" }
    },
    "warnings": {
      "type": "array",
      "items": { "type": "string" }
    }
  }
}

```

---

## 📊 6. Matriz de Evidencia de Pruebas de QA y Trazabilidad (5 Casos Reales)

La siguiente tabla consolida la trazabilidad completa entre los prompts del sistema, los 5 casos de prueba reales ejecutados contra el servidor local (`http://127.0.0.1:5050`) y registrados por el rol de QA en `evidencia_pruebas.md`:

| Caso # | Tipo de Defecto Probado       | `review_type`      | `review_id` Real                       | Timestamp (`created_at`)     | Status Decisión Humana  | Comentario Registrado por el Estudiante (`student_comment`) |
| :----: | :---------------------------- | :----------------- | :------------------------------------- | :--------------------------- | :---------------------: | :---------------------------------------------------------- |
| **1**  | Sintaxis básica (falta de `:`) | `Errores`          | `0997bdd3-9cc2-4ea1-aedc-bd9baacaf460` | `2026-07-23T03:00:48.181Z`   | `accepted`              | *"Correcto, me faltó el dos puntos al final del def."* |
| **2**  | Vulnerabilidad Inyección SQL  | `Seguridad basica` | `9f5f26be-c326-4d4d-9876-3ea43544552a` | `2026-07-23T03:00:54.975Z`   | `accepted`              | *"Voy a corregirlo usando parámetros en la consulta."* |
| **3**  | Legibilidad / Anidamiento     | `Legibilidad`      | `77aa646c-43be-4fcc-8208-d2e543c9530c` | `2026-07-23T03:00:59.877Z`   | `pending`               | *"De acuerdo con lo de los nombres poco descriptivos..."* |
| **4**  | Rendimiento / O(n²)           | `Rendimiento`      | `25ed4259-bab2-43c0-b6a4-a955f3bf21a1` | `2026-07-23T03:01:04.721Z`   | `discarded`             | *"Para este ejercicio en particular prefiero mantener O(n²)..."* |
| **5**  | Lógica / Condición Invertida  | `Errores`          | `9dd24dd5-3820-43d2-9718-32ee1638e9b3` | `2026-07-23T03:01:09.212Z`   | `accepted` + Regenerado | *"Tenía la condición invertida..."* -> Regenerado por eficiencia |

 |
