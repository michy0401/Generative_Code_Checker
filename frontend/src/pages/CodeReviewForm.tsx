import { useState } from 'react';
import apiFetch from '../utils/apiFetch'; 
import DiffViewer from '../components/DiffViewer';

interface AiReviewResponse {
  review_id?: string | number;
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
    finding_id?: string | number;
    why?: string;
    impact?: string;
    how_to_fix?: string;
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

  const [studentComment, setStudentComment] = useState('');
  const [actionStatus, setActionStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [actionMessage, setActionMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setAiResponse(null);
    setActionStatus('idle');
    setStudentComment('');
    
    const payload = { 
      language, 
      level, 
      review_type: reviewType, 
      exercise, 
      student_code: studentCode,
      session_id: sessionId
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

  const handleAction = async (status: 'accepted' | 'discarded' | 'pending') => {
    if (!aiResponse?.review_id) return;
    
    setActionStatus('loading');
    try {
      const response = await apiFetch(`/api/reviews/${aiResponse.review_id}`, {
        method: 'PATCH',
        body: JSON.stringify({ 
          status, 
          student_comment: studentComment,
          session_id: sessionId // GAP 18: El session_id vital para que no tire 403
        })
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || `Error al actualizar: ${response.status}`);
      }

      setActionStatus('success');
      setActionMessage(
        status === 'accepted' ? '¡Revisión aceptada exitosamente!' : 
        status === 'discarded' ? 'Revisión descartada. Gracias por el feedback.' :
        'Comentario guardado exitosamente.'
      );
    } catch (err: unknown) {
      setActionStatus('error');
      if (err instanceof Error) {
        alert(err.message);
      } else {
        alert("Error de conexión al intentar guardar la decisión.");
      }
    }
  };

  const handleRegenerate = async () => {
    if (!aiResponse?.review_id) return;
    setActionStatus('loading');
    try {
      const response = await apiFetch(`/api/reviews/${aiResponse.review_id}/regenerate`, {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId })
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || `Error al regenerar: ${response.status}`);
      }

      const data = await response.json();
      setAiResponse(data);
      setActionStatus('idle');
      alert("¡Diagnóstico regenerado con éxito!");
    } catch (err: unknown) {
      setActionStatus('error');
      if (err instanceof Error) {
        alert(err.message);
      } else {
        alert("Error al intentar regenerar el diagnóstico.");
      }
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="px-8 py-6 bg-gray-900 text-white">
          <h2 className="text-2xl font-bold">Nueva Revisión de Código</h2>
          <p className="text-gray-400 text-sm mt-1">Ingresa tu código y el contexto del ejercicio para que la IA genere el diagnóstico.</p>
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
            <textarea required rows={2} value={exercise} onChange={(e) => setExercise(e.target.value)} className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none" />
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="block text-sm font-semibold text-gray-700">Código Fuente a Revisar</label>
              <span className={`text-xs font-bold ${studentCode.length > 19500 ? 'text-red-500' : 'text-gray-500'}`}>
                {studentCode.length}/20000
              </span>
            </div>
            <textarea required maxLength={20000} rows={8} value={studentCode} onChange={(e) => setStudentCode(e.target.value)} className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none font-mono text-sm bg-gray-50" />
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
                  {/* GAP 19: Keys correctas del schema de Gemini */}
                  {aiResponse.explanation.map((exp, index) => (
                    <div key={index} className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                      <strong className="text-blue-900 block mb-2 text-lg">
                        {exp.finding_id ? `Hallazgo asociado: ${exp.finding_id}` : 'Concepto Clave'}
                      </strong>
                      <p className="text-sm text-blue-900 mb-2"><strong>Por qué ocurre:</strong> {exp.why}</p>
                      <p className="text-sm text-blue-900 mb-2"><strong>Impacto:</strong> {exp.impact}</p>
                      <p className="text-sm text-blue-900"><strong>Cómo arreglarlo:</strong> {exp.how_to_fix}</p>
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

            <div className="bg-gray-50 p-6 rounded-xl border border-gray-200 mt-6">
              {actionStatus === 'success' ? (
                <div className="text-center p-4 bg-green-100 text-green-800 font-bold rounded-lg border border-green-200">
                  {actionMessage}
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Comentario Humano (Opcional)</label>
                    <textarea rows={2} value={studentComment} onChange={(e) => setStudentComment(e.target.value)} placeholder="¿Qué opinas de esta revisión? ¿Te sirvió?" className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none text-sm" />
                  </div>
                  <div className="flex flex-wrap justify-end gap-3">
                    {/* GAP 4: Botones individuales de acción */}
                    <button onClick={handleRegenerate} disabled={actionStatus === 'loading'} className="px-4 py-2 border border-purple-300 text-purple-700 bg-purple-50 hover:bg-purple-100 rounded-lg font-bold transition disabled:opacity-50">
                      Regenerar Diagnóstico
                    </button>
                    <button onClick={() => handleAction('pending')} disabled={actionStatus === 'loading'} className="px-4 py-2 border border-blue-300 text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg font-bold transition disabled:opacity-50">
                      Solo Comentar
                    </button>
                    <button onClick={() => handleAction('discarded')} disabled={actionStatus === 'loading'} className="px-4 py-2 border border-red-300 text-red-700 bg-red-50 hover:bg-red-100 rounded-lg font-bold transition disabled:opacity-50">
                      Descartar
                    </button>
                    <button onClick={() => handleAction('accepted')} disabled={actionStatus === 'loading'} className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-bold transition disabled:opacity-50">
                      Aceptar Revisión
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