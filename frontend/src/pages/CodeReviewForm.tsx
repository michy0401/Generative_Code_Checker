import { useState } from 'react';
import apiFetch from '../utils/apiFetch'; 
import DiffViewer from '../components/DiffViewer';

interface AiReviewResponse {
  review_id?: string | number; // Necesario para el PATCH (Gap 4)
  session_id?: string;
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
  explanation: Array<{
    concept?: string;
    title?: string;
    description?: string;
    details?: string;
    [key: string]: unknown;
  }>;
  suggested_code: {
    improved_code?: string;
    [key: string]: unknown;
  };
  tests: Array<{
    test_name?: string;
    title?: string;
    description?: string;
    [key: string]: unknown;
  }>;
  warnings: string[];
}

export default function CodeReviewForm() {
  const [language, setLanguage] = useState('Python');
  const [level, setLevel] = useState('Intermedio');
  const [reviewType, setReviewType] = useState('Buenas practicas');
  const [exercise, setExercise] = useState('');
  const [studentCode, setStudentCode] = useState('');
  
  // GAP 16: Sesión persistente en el frontend
  const [sessionId] = useState(() => {
    let stored = localStorage.getItem('review_session_id');
    if (!stored) {
      stored = crypto.randomUUID ? crypto.randomUUID() : `sess_${Date.now()}`;
      localStorage.setItem('review_session_id', stored);
    }
    return stored;
  });
  
  const [loading, setLoading] = useState(false);
  const [aiResponse, setAiResponse] = useState<AiReviewResponse | null>(null); 
  const [error, setError] = useState<string | null>(null);

  // GAP 4: Estados para la acción humana
  const [studentComment, setStudentComment] = useState('');
  const [actionStatus, setActionStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [actionMessage, setActionMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setAiResponse(null);
    setActionStatus('idle'); // Reiniciamos el estado de acción
    setStudentComment('');
    
    const payload = { 
      language, 
      level, 
      review_type: reviewType, 
      exercise, 
      student_code: studentCode,
      session_id: sessionId // Se envía el ID persistido
    };

    try {
      const response = await apiFetch('/api/review', {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || `Error del servidor: ${response.status}`);
      }

      const data = await response.json();
      setAiResponse(data);
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

  // GAP 4: Lógica para enviar el PATCH
  const handleAction = async (status: 'accepted' | 'discarded') => {
    if (!aiResponse?.review_id) return;
    
    setActionStatus('loading');
    try {
      const response = await apiFetch(`/api/reviews/${aiResponse.review_id}`, {
        method: 'PATCH',
        body: JSON.stringify({ 
          status, 
          student_comment: studentComment 
        })
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || `Error al actualizar: ${response.status}`);
      }

      setActionStatus('success');
      setActionMessage(
        status === 'accepted' 
          ? '¡Revisión aceptada y guardada exitosamente!' 
          : 'Revisión descartada. Gracias por el feedback.'
      );
    } catch (err: unknown) {
      setActionStatus('error');
      if (err instanceof Error) {
        alert(err.message); // Usamos un alert simple para no romper el layout
      } else {
        alert("Error de conexión al intentar guardar la decisión.");
      }
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
              <select value={language} onChange={(e) => setLanguage(e.target.value)} className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none">
                <option value="Python">Python</option>
                <option value="JavaScript">JavaScript</option>
                <option value="Java">Java</option>
                <option value="C#">C#</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Nivel Esperado</label>
              <select value={level} onChange={(e) => setLevel(e.target.value)} className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none">
                <option value="Principiante">Principiante</option>
                <option value="Intermedio">Intermedio</option>
                <option value="Avanzado">Avanzado</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Criterio</label>
              <select value={reviewType} onChange={(e) => setReviewType(e.target.value)} className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none">
                <option value="Errores">Errores</option>
                <option value="Buenas practicas">Buenas practicas</option>
                <option value="Seguridad basica">Seguridad basica</option>
                <option value="Rendimiento">Rendimiento</option>
                <option value="Legibilidad">Legibilidad</option>
                <option value="Estructura">Estructura</option>
                <option value="Pruebas sugeridas">Pruebas sugeridas</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">Objetivo del Ejercicio</label>
            <textarea required rows={2} value={exercise} onChange={(e) => setExercise(e.target.value)} placeholder="Ej. Crear una función que calcule la serie de Fibonacci recursivamente..." className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none" />
          </div>

          <div>
            {/* GAP 17: Validaciones y límite de caracteres explícito */}
            <div className="flex justify-between items-center mb-2">
              <label className="block text-sm font-semibold text-gray-700">Código Fuente a Revisar</label>
              <span className={`text-xs font-bold ${studentCode.length > 19500 ? 'text-red-500' : 'text-gray-500'}`}>
                {studentCode.length}/20000
              </span>
            </div>
            <textarea
              required
              maxLength={20000}
              rows={8}
              value={studentCode}
              onChange={(e) => setStudentCode(e.target.value)}
              placeholder="Pega tu código aquí..."
              className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none font-mono text-sm bg-gray-50"
            />
          </div>

          <div className="flex justify-end pt-4 border-t">
            <button type="submit" disabled={loading} className="px-6 py-3 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 transition duration-200 disabled:opacity-50 flex items-center">
              {loading ? 'Analizando con IA...' : 'Generar Diagnóstico'}
            </button>
          </div>
        </form>

        {aiResponse && (
          <div className="px-8 pb-8 space-y-6">
            
            <div className="bg-green-50 border border-green-200 rounded-xl p-6">
              <h3 className="text-lg font-bold text-green-800">Puntuación: {aiResponse.summary?.score ?? 'N/A'}/100</h3>
              <p className="text-green-700 text-sm mt-1">{aiResponse.summary?.overall_assessment}</p>
            </div>

            {aiResponse.explanation && aiResponse.explanation.length > 0 && (
              <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
                <h4 className="font-bold text-gray-800 mb-4">Explicación Educativa</h4>
                <div className="space-y-4">
                  {aiResponse.explanation.map((exp, index) => (
                    <div key={index} className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                      <strong className="text-blue-900 block mb-1">{exp.concept || exp.title || 'Concepto'}</strong>
                      <p className="text-sm text-blue-800">{exp.description || exp.details || JSON.stringify(exp)}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {aiResponse.tests && aiResponse.tests.length > 0 && (
              <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
                <h4 className="font-bold text-gray-800 mb-4">Pruebas Sugeridas</h4>
                <ul className="list-disc pl-5 space-y-2 text-sm text-gray-700">
                  {aiResponse.tests.map((test, index) => (
                    <li key={index}><strong>{test.test_name || test.title || `Prueba ${index + 1}`}:</strong> {test.description || JSON.stringify(test)}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
              <h4 className="font-bold text-gray-800 mb-4">Hallazgos y Mejoras</h4>
              <ul className="space-y-3">
                {aiResponse.findings?.map((finding) => (
                  <li key={finding.id} className="p-3 bg-gray-50 rounded-lg border border-gray-100">
                    <span className={`px-2 py-1 text-xs font-bold rounded-full mr-2 ${finding.severity === 'High' ? 'bg-red-100 text-red-700' : finding.severity === 'Medium' ? 'bg-yellow-100 text-yellow-700' : 'bg-blue-100 text-blue-700'}`}>
                      {finding.severity}
                    </span>
                    <strong className="text-sm text-gray-800">{finding.title}: </strong>
                    <span className="text-sm text-gray-600">{finding.description} (Línea {finding.line})</span>
                  </li>
                ))}
              </ul>
            </div>

            {aiResponse.suggested_code?.improved_code && (
              <DiffViewer originalCode={studentCode} suggestedCode={aiResponse.suggested_code.improved_code} />
            )}

            {/* GAP 4: Interfaz conectada de Aceptar/Descartar/Comentar */}
            <div className="bg-gray-50 p-6 rounded-xl border border-gray-200 mt-6">
              {actionStatus === 'success' ? (
                <div className="text-center p-4 bg-green-100 text-green-800 font-bold rounded-lg border border-green-200">
                  {actionMessage}
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Comentario Humano (Opcional)</label>
                    <textarea 
                      rows={2} 
                      value={studentComment}
                      onChange={(e) => setStudentComment(e.target.value)}
                      placeholder="¿Qué opinas de esta revisión? ¿Te sirvió?" 
                      className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none text-sm" 
                    />
                  </div>
                  <div className="flex justify-end space-x-4">
                    <button 
                      onClick={() => handleAction('discarded')}
                      disabled={actionStatus === 'loading'}
                      className="px-6 py-2 border border-red-300 text-red-700 bg-red-50 hover:bg-red-100 rounded-lg font-bold transition disabled:opacity-50"
                    >
                      {actionStatus === 'loading' ? 'Guardando...' : 'Descartar'}
                    </button>
                    <button 
                      onClick={() => handleAction('accepted')}
                      disabled={actionStatus === 'loading'}
                      className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-bold transition disabled:opacity-50"
                    >
                      {actionStatus === 'loading' ? 'Guardando...' : 'Aceptar Revisión'}
                    </button>
                  </div>
                </div>
              )}
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