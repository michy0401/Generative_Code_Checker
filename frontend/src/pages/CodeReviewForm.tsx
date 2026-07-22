import { useState } from 'react';
import apiFetch from '../utils/apiFetch'; 
import DiffViewer from '../components/DiffViewer';

// Definimos la estructura del JSON detallando los campos que vamos a usar en la UI
interface AiReviewResponse {
  summary: {
    score?: number;
    overall_assessment?: string;
    [key: string]: unknown;
  };
  findings: Array<{
    id: number;
    severity: string;
    title: string;
    description: string;
    line: number;
    [key: string]: unknown;
  }>;
  explanation: Array<Record<string, unknown>>;
  suggested_code: {
    improved_code?: string;
    [key: string]: unknown;
  };
  tests: Array<Record<string, unknown>>;
  warnings: string[];
}

export default function CodeReviewForm() {
  const [language, setLanguage] = useState('Python');
  const [level, setLevel] = useState('Intermedio');
  const [reviewType, setReviewType] = useState('Buenas Prácticas');
  const [exercise, setExercise] = useState('');
  const [studentCode, setStudentCode] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [aiResponse, setAiResponse] = useState<AiReviewResponse | null>(null); 
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setAiResponse(null);
    
    const payload = { 
      language, 
      level, 
      review_type: reviewType, 
      exercise, 
      student_code: studentCode 
    };
    
    console.log("Datos enviados al backend:", payload);

    try {
      const response = await apiFetch('/api/review', {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Error del servidor: ${response.status}`);
      }

      const data = await response.json();
      setAiResponse(data);
      console.log("Respuesta de la IA estructurada:", data);

    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Ocurrió un error al contactar al servidor.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto bg-white rounded-xl shadow-lg overflow-hidden">
        
        <div className="px-8 py-6 bg-gray-900 text-white">
          <h2 className="text-2xl font-bold">Nueva Revisión de Código</h2>
          <p className="text-gray-400 text-sm mt-1">
            Ingresa tu código y el contexto del ejercicio para que la IA genere el diagnóstico.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-8 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Lenguaje</label>
              <select 
                value={language} 
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              >
                <option value="Python">Python</option>
                <option value="JavaScript">JavaScript</option>
                <option value="Java">Java</option>
                <option value="C#">C#</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Nivel Esperado</label>
              <select 
                value={level} 
                onChange={(e) => setLevel(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              >
                <option value="Principiante">Principiante</option>
                <option value="Intermedio">Intermedio</option>
                <option value="Avanzado">Avanzado</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Criterio</label>
              <select 
                value={reviewType} 
                onChange={(e) => setReviewType(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              >
                <option value="Errores y Bugs">Errores y Bugs</option>
                <option value="Buenas Prácticas">Buenas Prácticas</option>
                <option value="Seguridad">Seguridad Básica</option>
                <option value="Rendimiento">Rendimiento</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Objetivo del Ejercicio
            </label>
            <textarea
              required
              rows={2}
              value={exercise}
              onChange={(e) => setExercise(e.target.value)}
              placeholder="Ej. Crear una función que calcule la serie de Fibonacci recursivamente..."
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Código Fuente a Revisar
            </label>
            <textarea
              required
              rows={8}
              value={studentCode}
              onChange={(e) => setStudentCode(e.target.value)}
              placeholder="Pega tu código aquí..."
              className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none font-mono text-sm bg-gray-50"
            />
          </div>

          <div className="flex justify-end pt-4 border-t">
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-3 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 transition duration-200 disabled:opacity-50 flex items-center"
            >
              {loading ? 'Analizando con IA...' : 'Generar Diagnóstico'}
            </button>
          </div>
        </form>

        {/* --- RESULTADOS DEL DIAGNÓSTICO --- */}
        {aiResponse && (
          <div className="px-8 pb-8 space-y-6">
            
            {/* Resumen y Puntuación */}
            <div className="bg-green-50 border border-green-200 rounded-xl p-6">
              <h3 className="text-lg font-bold text-green-800">
                Puntuación: {aiResponse.summary?.score ?? 'N/A'}/100
              </h3>
              <p className="text-green-700 text-sm mt-1">
                {aiResponse.summary?.overall_assessment}
              </p>
            </div>

            {/* Listado de Hallazgos (Findings) */}
            <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
              <h4 className="font-bold text-gray-800 mb-4">Hallazgos y Mejoras</h4>
              <ul className="space-y-3">
                {aiResponse.findings?.map((finding) => (
                  <li key={finding.id} className="p-3 bg-gray-50 rounded-lg border border-gray-100">
                    <span className={`px-2 py-1 text-xs font-bold rounded-full mr-2 ${
                      finding.severity === 'High' ? 'bg-red-100 text-red-700' :
                      finding.severity === 'Medium' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-blue-100 text-blue-700'
                    }`}>
                      {finding.severity}
                    </span>
                    <strong className="text-sm text-gray-800">{finding.title}: </strong>
                    <span className="text-sm text-gray-600">{finding.description} (Línea {finding.line})</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* El Visor de Diferencias */}
            {aiResponse.suggested_code?.improved_code && (
              <DiffViewer 
                originalCode={studentCode} 
                suggestedCode={aiResponse.suggested_code.improved_code} 
              />
            )}

            {/* Botones de Acción */}
            <div className="flex justify-end space-x-4 pt-4">
              <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 font-semibold transition">
                Descartar Revisión
              </button>
              <button className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-semibold transition">
                Aceptar y Guardar
              </button>
            </div>

          </div>
        )}

        {error && (
          <div className="px-8 pb-8">
            <div className="bg-red-50 border border-red-200 rounded-xl p-6">
              <h3 className="text-lg font-bold text-red-800">Error de Conexión</h3>
              <p className="text-red-700 text-sm font-bold mt-1">{error}</p>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}