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

  // Función para reiniciar todo el formulario y volver al estado inicial
  const handleResetForm = () => {
    setLanguage('Python');
    setLevel('Intermedio');
    setReviewType('Buenas practicas');
    setExercise('');
    setStudentCode('');
    setAiResponse(null);
    setError(null);
    setActionStatus('idle');
    setStudentComment('');
  };

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

  const handleAction = async (actionType: 'accepted' | 'discarded' | 'comment_only') => {
    if (!aiResponse?.review_id) return;
    
    setActionStatus('loading');
    try {
      const bodyPayload: Record<string, unknown> = { 
        student_comment: studentComment,
        session_id: sessionId 
      };
      
      if (actionType !== 'comment_only') {
        bodyPayload.status = actionType;
      }

      const response = await apiFetch(`/api/reviews/${aiResponse.review_id}`, {
        method: 'PATCH',
        body: JSON.stringify(bodyPayload)
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || `Error al actualizar: ${response.status}`);
      }

      setActionStatus('success');
      setActionMessage(
        actionType === 'accepted' ? '¡Revisión aceptada exitosamente!' : 
        actionType === 'discarded' ? 'Revisión descartada. Gracias por el feedback.' :
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
    <div className="min-h-screen bg-slate-50 py-12 px-4 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-5xl mx-auto bg-white rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100 overflow-hidden">
        
        {/* Cabecera del Formulario */}
        <div className="px-10 py-8 bg-slate-900 text-white relative overflow-hidden">
          <div className="absolute top-0 right-0 -mt-10 -mr-10 w-40 h-40 bg-indigo-500 rounded-full opacity-10 blur-3xl"></div>
          <h2 className="text-3xl font-extrabold tracking-tight relative z-10">Nueva Revisión de Código</h2>
          <p className="text-slate-400 text-sm mt-2 font-medium relative z-10">Ingresa tu código y el contexto del ejercicio para que la IA genere un diagnóstico detallado.</p>
        </div>

        {/* Formulario Principal */}
        <form onSubmit={handleSubmit} className="p-10 space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-2">Lenguaje</label>
              <select value={language} onChange={(e) => setLanguage(e.target.value)} className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all duration-200 text-sm font-medium text-slate-700">
                <option value="Python">Python</option>
                <option value="JavaScript">JavaScript</option>
                <option value="Java">Java</option>
                <option value="C#">C#</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-2">Nivel Esperado</label>
              <select value={level} onChange={(e) => setLevel(e.target.value)} className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all duration-200 text-sm font-medium text-slate-700">
                <option value="Principiante">Principiante</option>
                <option value="Intermedio">Intermedio</option>
                <option value="Avanzado">Avanzado</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-2">Criterio Principal</label>
              <select value={reviewType} onChange={(e) => setReviewType(e.target.value)} className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all duration-200 text-sm font-medium text-slate-700">
                <option value="Errores">Errores y Bugs</option>
                <option value="Buenas practicas">Buenas Prácticas</option>
                <option value="Seguridad basica">Seguridad Básica</option>
                <option value="Rendimiento">Rendimiento</option>
                <option value="Legibilidad">Legibilidad</option>
                <option value="Estructura">Estructura</option>
                <option value="Pruebas sugeridas">Pruebas Sugeridas</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2">Objetivo del Ejercicio</label>
            <textarea required rows={2} value={exercise} onChange={(e) => setExercise(e.target.value)} placeholder="Ej. Crear una función que calcule la serie de Fibonacci recursivamente..." className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all duration-200 text-sm resize-none" />
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="block text-sm font-bold text-slate-700">Código Fuente a Revisar</label>
              <span className={`text-xs font-bold px-2 py-1 rounded-md ${studentCode.length > 19500 ? 'bg-red-100 text-red-600' : 'bg-slate-100 text-slate-500'}`}>
                {studentCode.length} / 20000
              </span>
            </div>
            <textarea required maxLength={20000} rows={10} value={studentCode} onChange={(e) => setStudentCode(e.target.value)} placeholder="// Pega tu código aquí..." className="w-full px-4 py-4 bg-slate-800 text-slate-100 border border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-200 font-mono text-sm leading-relaxed shadow-inner" />
          </div>

          <div className="flex justify-end pt-4">
            <button type="submit" disabled={loading} className="px-8 py-3.5 bg-indigo-600 text-white font-bold rounded-xl shadow-md shadow-indigo-200 hover:bg-indigo-700 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-50 disabled:transform-none flex items-center">
              {loading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  Analizando con IA...
                </>
              ) : 'Generar Diagnóstico'}
            </button>
          </div>
        </form>

        {/* Resultados */}
        {aiResponse && (
          <div className="px-10 pb-10 space-y-8 animate-fade-in-up">
            
            {/* Score */}
            <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-100 rounded-2xl p-8 shadow-sm">
              <h3 className="text-xl font-extrabold text-emerald-900 flex items-center">
                <span className="bg-emerald-200 text-emerald-800 px-3 py-1 rounded-lg mr-3 text-2xl">{aiResponse.summary?.score ?? 'N/A'}</span>
                Puntuación Global
              </h3>
              <p className="text-emerald-800 text-sm mt-3 font-medium leading-relaxed">{aiResponse.summary?.overall_assessment}</p>
            </div>

            {/* Explicación Educativa */}
            {aiResponse.explanation && aiResponse.explanation.length > 0 && (
              <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm">
                <h4 className="font-extrabold text-slate-900 mb-6 text-lg">Explicación Educativa</h4>
                <div className="space-y-4">
                  {aiResponse.explanation.map((exp, index) => (
                    <div key={index} className="p-5 bg-indigo-50/50 rounded-xl border border-indigo-100/50 transition hover:bg-indigo-50">
                      <strong className="text-indigo-900 block mb-3 text-sm uppercase tracking-wider">
                        {exp.finding_id ? `Hallazgo asociado: #${exp.finding_id}` : 'Concepto Clave'}
                      </strong>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="bg-white p-3 rounded-lg border border-indigo-100 shadow-sm"><strong className="block text-xs text-indigo-400 uppercase mb-1">Por qué ocurre</strong><span className="text-sm text-slate-700">{exp.why}</span></div>
                        <div className="bg-white p-3 rounded-lg border border-indigo-100 shadow-sm"><strong className="block text-xs text-indigo-400 uppercase mb-1">Impacto</strong><span className="text-sm text-slate-700">{exp.impact}</span></div>
                        <div className="bg-white p-3 rounded-lg border border-indigo-100 shadow-sm"><strong className="block text-xs text-indigo-400 uppercase mb-1">Cómo arreglarlo</strong><span className="text-sm text-slate-700">{exp.how_to_fix}</span></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Hallazgos */}
            <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm">
              <h4 className="font-extrabold text-slate-900 mb-6 text-lg">Hallazgos y Mejoras</h4>
              <ul className="space-y-4">
                {aiResponse.findings?.map((finding) => (
                  <li key={finding.id} className="p-4 bg-slate-50 rounded-xl border border-slate-100 flex items-start">
                    <span className={`px-2.5 py-1 text-xs font-bold rounded-md mr-4 mt-0.5 border ${
                      finding.severity === 'High' ? 'bg-rose-100 text-rose-700 border-rose-200' : 
                      finding.severity === 'Medium' ? 'bg-amber-100 text-amber-700 border-amber-200' : 
                      'bg-sky-100 text-sky-700 border-sky-200'
                    }`}>
                      {finding.severity}
                    </span>
                    <div>
                      <strong className="text-sm text-slate-900 block mb-1">{finding.title} <span className="text-slate-400 font-normal ml-2">(Línea {finding.line})</span></strong>
                      <span className="text-sm text-slate-600 leading-relaxed">{finding.description}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {/* Pruebas */}
            {aiResponse.tests && aiResponse.tests.length > 0 && (
              <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm">
                <h4 className="font-extrabold text-slate-900 mb-6 text-lg">Pruebas Sugeridas</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {aiResponse.tests.map((test, index) => (
                    <div key={index} className="p-4 bg-slate-50 border border-slate-100 rounded-xl">
                      <strong className="text-sm text-slate-800 block mb-1">{test.test_name || test.title || `Prueba ${index + 1}`}</strong>
                      <p className="text-sm text-slate-600">{test.description || JSON.stringify(test)}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Diff Viewer */}
            {aiResponse.suggested_code?.improved_code && (
              <div className="border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
                <div className="bg-slate-50 px-6 py-3 border-b border-slate-200">
                  <h4 className="font-bold text-slate-700 text-sm">Comparativa de Código</h4>
                </div>
                <DiffViewer originalCode={studentCode} suggestedCode={aiResponse.suggested_code.improved_code} />
              </div>
            )}

            {/* Acciones Humanas */}
            <div className="bg-slate-50 p-8 rounded-2xl border border-slate-200 mt-8 shadow-inner">
              {actionStatus === 'success' ? (
                <div className="text-center p-8 bg-emerald-100 text-emerald-800 font-bold rounded-xl border border-emerald-200 flex flex-col items-center justify-center">
                  <svg className="w-14 h-14 mb-3 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                  <p className="text-lg">{actionMessage}</p>
                  
                  {/* Botón de Nueva Revisión en Estado de Éxito */}
                  <button onClick={handleResetForm} className="mt-6 px-8 py-3 bg-emerald-600 hover:bg-emerald-700 text-white shadow-md shadow-emerald-200 rounded-xl font-bold transition-all duration-200 hover:-translate-y-0.5">
                    Hacer una Nueva Revisión
                  </button>
                </div>
              ) : (
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-bold text-slate-700 mb-2">Comentario Humano (Feedback Opcional)</label>
                    <textarea rows={2} value={studentComment} onChange={(e) => setStudentComment(e.target.value)} placeholder="¿Qué opinas de esta revisión? ¿La IA acertó?" className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-200 resize-none text-sm" />
                  </div>
                  
                  <div className="flex flex-col sm:flex-row flex-wrap justify-end gap-3 pt-2">
                    {/* Botón de Nueva Revisión Rápida (Abandona la actual) */}
                    <button onClick={handleResetForm} type="button" className="px-5 py-2.5 border border-slate-300 text-slate-700 bg-white hover:bg-slate-100 rounded-xl font-bold transition-all duration-200 text-sm shadow-sm">
                      Nueva Revisión
                    </button>
                    
                    <button onClick={handleRegenerate} disabled={actionStatus === 'loading'} className="px-5 py-2.5 border border-purple-200 text-purple-700 bg-purple-50 hover:bg-purple-100 rounded-xl font-bold transition-all duration-200 disabled:opacity-50 text-sm">
                      <span className="flex items-center">
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                        Regenerar
                      </span>
                    </button>
                    <button onClick={() => handleAction('comment_only')} disabled={actionStatus === 'loading'} className="px-5 py-2.5 border border-slate-300 text-slate-700 bg-white hover:bg-slate-50 hover:border-slate-400 rounded-xl font-bold transition-all duration-200 disabled:opacity-50 text-sm shadow-sm">
                      Solo Comentar
                    </button>
                    
                    <div className="flex-grow hidden lg:block"></div>
                    
                    <button onClick={() => handleAction('discarded')} disabled={actionStatus === 'loading'} className="px-6 py-2.5 border border-rose-200 text-rose-700 bg-rose-50 hover:bg-rose-100 rounded-xl font-bold transition-all duration-200 disabled:opacity-50 text-sm">
                      Descartar Sugerencia
                    </button>
                    <button onClick={() => handleAction('accepted')} disabled={actionStatus === 'loading'} className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white shadow-md shadow-emerald-200 rounded-xl font-bold transition-all duration-200 disabled:opacity-50 text-sm hover:-translate-y-0.5">
                      Aceptar y Aplicar
                    </button>
                  </div>
                </div>
              )}
            </div>

          </div>
        )}

        {error && (
          <div className="px-10 pb-10">
            <div className="bg-red-50 border border-red-100 rounded-2xl p-6 flex items-start">
              <svg className="w-6 h-6 text-red-600 mr-3 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              <div>
                <h3 className="text-lg font-bold text-red-800">Error en el Análisis</h3>
                <p className="text-red-700 text-sm font-medium mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}