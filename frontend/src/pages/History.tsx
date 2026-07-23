import { useState, useEffect } from 'react';
import apiFetch from '../utils/apiFetch';

interface AIResponsePayload {
  summary?: { score?: number; overall_assessment?: string };
  findings?: Array<{
    title: string;
    description: string;
    line: number;
    [key: string]: unknown;
  }>;
  suggested_code?: { improved_code?: string; [key: string]: unknown };
  tests?: Array<{ test_name?: string; title?: string; description?: string; [key: string]: unknown }>;
  warnings?: string[];
  [key: string]: unknown;
}

interface ReviewRecord {
  id: string;
  created_at: string;
  language: string;
  review_type: string;
  status: string;
  student_code?: string;
  exercise?: string;
  prompt_sent?: string;
  response?: string | AIResponsePayload;
  student_comment?: string;
  [key: string]: unknown;
}

export default function History() {
  const [reviews, setReviews] = useState<ReviewRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedReview, setSelectedReview] = useState<ReviewRecord | null>(null);
  
  // Nuevo estado para controlar nuestra alerta visual (Toast)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await apiFetch('/api/reviews/mine');
        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.error || `Error del servidor: ${response.status}`);
        }
        
        const data = await response.json();
        setReviews(data);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Error de conexión al cargar el historial.");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  const getParsedResponse = (res: unknown): AIResponsePayload | null => {
    if (!res) return null;
    if (typeof res === 'object') return res as AIResponsePayload;
    if (typeof res === 'string') {
      try {
        return JSON.parse(res) as AIResponsePayload;
      } catch {
        return null;
      }
    }
    return null;
  };

  // Función para mostrar el Toast y ocultarlo automáticamente a los 3 segundos
  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 3000);
  };

  const handleUpdateStatus = async (reviewId: string, newStatus: 'accepted' | 'discarded') => {
    try {
      const response = await apiFetch(`/api/reviews/${reviewId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus })
      });
      
      if (!response.ok) {
        throw new Error('Error al actualizar el estado');
      }

      // Actualizamos el estado local para que la UI reaccione instantáneamente
      setReviews(reviews.map(r => r.id === reviewId ? { ...r, status: newStatus } : r));
      setSelectedReview(prev => prev ? { ...prev, status: newStatus } : null);
      
      // Lanzamos la notificación bonita de éxito
      showToast(`Revisión ${newStatus === 'accepted' ? 'aceptada' : 'descartada'} exitosamente.`, 'success');
      
    } catch (error) {
      console.error("Error al actualizar la revisión:", error);
      // Lanzamos la notificación bonita de error
      showToast("Hubo un error al intentar cambiar el estado.", 'error');
    }
  };

  if (loading) return (
    <div className="flex h-screen items-center justify-center bg-slate-50">
      <div className="flex flex-col items-center">
        <svg className="animate-spin h-10 w-10 text-indigo-600 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
        <span className="font-bold text-slate-600">Cargando tu historial...</span>
      </div>
    </div>
  );

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-slate-50 py-12 px-4 sm:px-6 lg:px-8 font-sans relative">
      <div className="max-w-6xl mx-auto bg-white rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100 overflow-hidden">
        
        <div className="px-8 py-6 bg-slate-900 border-b border-slate-800 flex flex-col sm:flex-row justify-between items-center gap-4">
          <h2 className="text-2xl font-extrabold text-white tracking-tight">Registro de Auditorías</h2>
          <span className="text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-4 py-1.5 rounded-full font-bold uppercase tracking-wider">
            Total: {reviews.length} revisiones
          </span>
        </div>

        {error ? (
          <div className="p-10 text-center bg-rose-50 border-b border-rose-100">
            <h3 className="text-lg font-bold text-rose-800 mb-1">Error al cargar datos</h3>
            <p className="text-rose-600">{error}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider border-b border-slate-200">
                  <th className="px-8 py-5 font-bold">Fecha</th>
                  <th className="px-8 py-5 font-bold">Lenguaje</th>
                  <th className="px-8 py-5 font-bold">Criterio</th>
                  <th className="px-8 py-5 font-bold">Decisión</th>
                  <th className="px-8 py-5 font-bold text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {reviews.map((review) => (
                  <tr key={review.id} className="hover:bg-slate-50 transition-colors duration-150">
                    <td className="px-8 py-5 text-sm text-slate-600 font-medium">
                      {new Date(review.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-8 py-5 text-sm font-bold text-slate-900">{review.language}</td>
                    <td className="px-8 py-5 text-sm text-slate-500">{review.review_type}</td>
                    <td className="px-8 py-5">
                      <span className={`px-3 py-1.5 rounded-lg text-xs font-bold border ${
                        review.status === 'accepted' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                        review.status === 'pending' ? 'bg-amber-50 text-amber-700 border-amber-200' : 
                        'bg-rose-50 text-rose-700 border-rose-200'
                      }`}>
                        {review.status === 'accepted' ? 'ACEPTADO' : review.status === 'pending' ? 'PENDIENTE' : 'DESCARTADO'}
                      </span>
                    </td>
                    <td className="px-8 py-5 text-right">
                      <button 
                        onClick={() => setSelectedReview(review)} 
                        className="text-indigo-600 hover:text-indigo-800 text-sm font-bold bg-indigo-50 hover:bg-indigo-100 px-4 py-2 rounded-lg transition-colors cursor-pointer"
                      >
                        Evidencia
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {reviews.length === 0 && (
              <div className="text-center py-20 text-slate-400 font-medium">
                <svg className="w-12 h-12 mx-auto mb-4 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                No tienes revisiones registradas todavía.
              </div>
            )}
          </div>
        )}
      </div>

      {selectedReview && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-white rounded-3xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-slate-200 flex flex-col">
            
            <div className="px-8 py-5 bg-slate-900 text-white flex justify-between items-center sticky top-0 z-10 border-b border-slate-800">
              <div>
                <h3 className="text-lg font-bold tracking-tight">Evidencia de Auditoría</h3>
                <p className="text-xs text-slate-400 font-mono mt-1 opacity-70">REF: {selectedReview.id}</p>
              </div>
              <button 
                onClick={() => setSelectedReview(null)} 
                className="text-slate-400 hover:text-white hover:bg-slate-800 h-10 w-10 flex items-center justify-center rounded-full transition-colors cursor-pointer"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
              </button>
            </div>

            <div className="p-8 space-y-8">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-slate-50 p-6 rounded-2xl border border-slate-100 text-sm shadow-inner">
                <div><span className="text-slate-400 block text-xs uppercase font-bold tracking-wider mb-1">Lenguaje</span><strong className="text-slate-800 text-base">{selectedReview.language}</strong></div>
                <div><span className="text-slate-400 block text-xs uppercase font-bold tracking-wider mb-1">Criterio</span><strong className="text-slate-800">{selectedReview.review_type}</strong></div>
                <div><span className="text-slate-400 block text-xs uppercase font-bold tracking-wider mb-1">Fecha</span><strong className="text-slate-800">{new Date(selectedReview.created_at).toLocaleDateString()}</strong></div>
                <div>
                  <span className="text-slate-400 block text-xs uppercase font-bold tracking-wider mb-1">Estado</span>
                  <span className={`inline-block px-2.5 py-1 rounded-md text-xs font-bold border ${
                    selectedReview.status === 'accepted' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                    selectedReview.status === 'pending' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-rose-50 text-rose-700 border-rose-200'
                  }`}>
                    {selectedReview.status.toUpperCase()}
                  </span>
                </div>
              </div>

              {selectedReview.exercise && (
                <div>
                  <h4 className="text-sm font-extrabold text-slate-900 mb-2 uppercase tracking-wide">Contexto del Ejercicio</h4>
                  <p className="text-sm bg-indigo-50/50 text-indigo-900 p-4 rounded-xl border border-indigo-100">{selectedReview.exercise}</p>
                </div>
              )}

              {selectedReview.prompt_sent && (
                <div>
                  <h4 className="text-sm font-extrabold text-slate-900 mb-2 uppercase tracking-wide">Trazabilidad: Prompt LLM</h4>
                  <pre className="bg-slate-900 text-slate-300 p-5 rounded-xl font-mono text-xs overflow-x-auto max-h-48 whitespace-pre-wrap shadow-inner border border-slate-800 leading-relaxed">
                    {selectedReview.prompt_sent}
                  </pre>
                </div>
              )}

              {selectedReview.student_code && (
                <div>
                  <h4 className="text-sm font-extrabold text-slate-900 mb-2 uppercase tracking-wide">Código Original</h4>
                  <pre className="bg-slate-900 text-slate-100 p-5 rounded-xl font-mono text-xs overflow-x-auto max-h-64 shadow-inner border border-slate-800 leading-relaxed">
                    {selectedReview.student_code}
                  </pre>
                </div>
              )}

              {getParsedResponse(selectedReview.response)?.summary?.overall_assessment && (
                <div>
                  <h4 className="text-sm font-extrabold text-slate-900 mb-2 uppercase tracking-wide">Evaluación General IA</h4>
                  <p className="text-sm text-slate-800 bg-emerald-50/50 p-4 rounded-xl border border-emerald-100">
                    {getParsedResponse(selectedReview.response)?.summary?.overall_assessment}
                  </p>
                </div>
              )}

              {getParsedResponse(selectedReview.response)?.findings && (getParsedResponse(selectedReview.response)?.findings?.length ?? 0) > 0 && (
                <div>
                  <h4 className="text-sm font-extrabold text-slate-900 mb-3 uppercase tracking-wide">Hallazgos Principales</h4>
                  <div className="space-y-3">
                    {getParsedResponse(selectedReview.response)?.findings?.map((f, idx) => (
                      <div key={idx} className="p-4 bg-white border border-slate-200 rounded-xl text-sm shadow-sm">
                        <strong className="text-slate-900 block mb-1">{f.title}</strong>
                        <span className="text-slate-600">{f.description} <span className="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded ml-1">Línea {f.line}</span></span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {getParsedResponse(selectedReview.response)?.tests && (getParsedResponse(selectedReview.response)?.tests?.length ?? 0) > 0 && (
                <div>
                  <h4 className="text-sm font-extrabold text-slate-900 mb-3 uppercase tracking-wide">Pruebas Sugeridas</h4>
                  <ul className="space-y-3">
                    {getParsedResponse(selectedReview.response)?.tests?.map((test, idx) => (
                      <li key={idx} className="bg-white border border-slate-200 p-4 rounded-xl text-sm shadow-sm">
                        <strong className="block text-slate-800 mb-1">{test.test_name || test.title}:</strong> 
                        <span className="text-slate-600">{test.description}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {getParsedResponse(selectedReview.response)?.suggested_code?.improved_code && (
                <div>
                  <h4 className="text-sm font-extrabold text-slate-900 mb-2 uppercase tracking-wide">Código Sugerido</h4>
                  <pre className="bg-slate-900 text-emerald-400 p-5 rounded-xl font-mono text-xs overflow-x-auto max-h-64 shadow-inner border border-slate-800 leading-relaxed">
                    {getParsedResponse(selectedReview.response)?.suggested_code?.improved_code}
                  </pre>
                </div>
              )}

              {getParsedResponse(selectedReview.response)?.warnings && (getParsedResponse(selectedReview.response)?.warnings?.length ?? 0) > 0 && (
                <div>
                  <h4 className="text-sm font-extrabold text-amber-900 mb-3 uppercase tracking-wide">Advertencias del Modelo</h4>
                  <ul className="list-disc pl-5 space-y-2 text-sm text-amber-800 bg-amber-50/50 border border-amber-200 p-5 rounded-xl">
                    {getParsedResponse(selectedReview.response)?.warnings?.map((warn, idx) => (
                      <li key={idx}>{warn}</li>
                    ))}
                  </ul>
                </div>
              )}

              {selectedReview.student_comment && (
                <div>
                  <h4 className="text-sm font-extrabold text-slate-900 mb-2 uppercase tracking-wide">Feedback Humano Registrado</h4>
                  <p className="text-sm bg-slate-100 text-slate-700 p-4 rounded-xl border border-slate-200 italic shadow-inner">
                    "{selectedReview.student_comment}"
                  </p>
                </div>
              )}
            </div>

            <div className="px-8 py-5 bg-slate-50 border-t border-slate-200 flex justify-between items-center sticky bottom-0">
              <div className="flex gap-3">
                {selectedReview.status === 'pending' && (
                  <>
                    <button
                      onClick={() => handleUpdateStatus(selectedReview.id, 'discarded')}
                      className="px-5 py-2.5 bg-red-50 hover:bg-red-100 text-red-600 font-bold rounded-xl border border-red-200 transition-colors shadow-sm cursor-pointer"
                    >
                      Descartar
                    </button>
                    <button
                      onClick={() => handleUpdateStatus(selectedReview.id, 'accepted')}
                      className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl transition-colors shadow-md shadow-emerald-900/20 cursor-pointer"
                    >
                      Aceptar Revisión
                    </button>
                  </>
                )}
              </div>
              <button 
                onClick={() => setSelectedReview(null)} 
                className="px-6 py-2.5 bg-slate-900 hover:bg-slate-800 text-white text-sm font-bold rounded-xl shadow-md transition-colors cursor-pointer ml-auto"
              >
                Cerrar Evidencia
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Renderizado del Toast Flotante */}
      {toast && (
        <div className={`fixed top-10 left-1/2 transform -translate-x-1/2 z-[100] flex items-center gap-3 px-6 py-4 rounded-2xl shadow-2xl border animate-fade-in ${
          toast.type === 'success' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-rose-50 border-rose-200 text-rose-800'
        }`}>
          {toast.type === 'success' ? (
            <svg className="w-6 h-6 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          ) : (
            <svg className="w-6 h-6 text-rose-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          )}
          <span className="font-bold text-sm tracking-wide">{toast.message}</span>
        </div>
      )}
      
    </div>
  );
}