import { useState, useEffect } from 'react';
import apiFetch from '../utils/apiFetch';

// Definimos la forma exacta del JSON de la IA para que TypeScript no se queje
interface AIResponsePayload {
  findings?: Array<{
    title: string;
    description: string;
    line: number;
    [key: string]: unknown;
  }>;
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
  response?: string | AIResponsePayload; // 1. Adiós 'any'
  student_comment?: string;
  [key: string]: unknown;
}

export default function History() {
  const [reviews, setReviews] = useState<ReviewRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedReview, setSelectedReview] = useState<ReviewRecord | null>(null);

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

  // 2. Usamos 'unknown' en vez de 'any' y forzamos el retorno al Payload
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

  if (loading) return <div className="flex h-screen items-center justify-center font-bold text-gray-600">Cargando tu historial...</div>;

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-200 bg-gray-900 flex justify-between items-center">
          <h2 className="text-xl font-bold text-white">Mi Historial de Revisiones</h2>
          <span className="text-xs bg-gray-800 text-gray-300 px-3 py-1 rounded-full font-mono">Total: {reviews.length}</span>
        </div>

        {error ? (
          <div className="p-8 text-center text-red-600 font-bold bg-red-50">{error}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 text-gray-500 text-sm uppercase tracking-wider border-b border-gray-200">
                  <th className="px-6 py-4 font-semibold">Fecha</th>
                  <th className="px-6 py-4 font-semibold">Lenguaje</th>
                  <th className="px-6 py-4 font-semibold">Criterio</th>
                  <th className="px-6 py-4 font-semibold">Estado</th>
                  <th className="px-6 py-4 font-semibold text-right">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {reviews.map((review) => (
                  <tr key={review.id} className="hover:bg-gray-50 transition">
                    <td className="px-6 py-4 text-sm text-gray-800">
                      {new Date(review.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{review.language}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{review.review_type}</td>
                    <td className="px-6 py-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                        review.status === 'accepted' ? 'bg-green-100 text-green-800' :
                        review.status === 'pending' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {review.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button onClick={() => setSelectedReview(review)} className="text-blue-600 hover:text-blue-800 text-sm font-semibold cursor-pointer">
                        Ver Detalle
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {reviews.length === 0 && <div className="text-center py-12 text-gray-500">No tienes revisiones registradas todavía.</div>}
          </div>
        )}
      </div>

      {selectedReview && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-gray-100">
            <div className="px-6 py-4 bg-gray-900 text-white flex justify-between items-center sticky top-0">
              <div>
                <h3 className="text-lg font-bold">Detalle de la Revisión</h3>
                <p className="text-xs text-gray-400 font-mono">ID: {selectedReview.id}</p>
              </div>
              <button onClick={() => setSelectedReview(null)} className="text-gray-400 hover:text-white text-xl font-bold px-2 py-1 cursor-pointer">&times;</button>
            </div>

            <div className="p-6 space-y-6">
              <div className="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded-xl border border-gray-200 text-sm">
                <div><span className="text-gray-500 block text-xs uppercase font-semibold">Lenguaje</span><strong className="text-gray-800">{selectedReview.language}</strong></div>
                <div><span className="text-gray-500 block text-xs uppercase font-semibold">Criterio</span><strong className="text-gray-800">{selectedReview.review_type}</strong></div>
                <div>
                  <span className="text-gray-500 block text-xs uppercase font-semibold">Estado</span>
                  <span className={`inline-block px-2 py-0.5 mt-1 rounded text-xs font-bold ${
                    selectedReview.status === 'accepted' ? 'bg-green-100 text-green-800' :
                    selectedReview.status === 'pending' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {selectedReview.status}
                  </span>
                </div>
                <div><span className="text-gray-500 block text-xs uppercase font-semibold">Fecha</span><strong className="text-gray-800">{new Date(selectedReview.created_at).toLocaleString()}</strong></div>
              </div>

              {selectedReview.exercise && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-1">Objetivo del Ejercicio</h4>
                  <p className="text-sm bg-blue-50 text-blue-900 p-3 rounded-lg border border-blue-100">{selectedReview.exercise}</p>
                </div>
              )}

              {selectedReview.prompt_sent && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-1">Prompt Enviado al LLM</h4>
                  <pre className="bg-gray-800 text-gray-300 p-4 rounded-lg font-mono text-xs overflow-x-auto max-h-40 whitespace-pre-wrap">
                    {selectedReview.prompt_sent}
                  </pre>
                </div>
              )}

              {selectedReview.student_code && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-1">Código Original Analizado</h4>
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-xs overflow-x-auto max-h-48">
                    {selectedReview.student_code}
                  </pre>
                </div>
              )}

              {getParsedResponse(selectedReview.response) && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Hallazgos Principales (IA)</h4>
                  <div className="space-y-2">
                    {/* 3. Adiós '(f: any, idx: number)'. TypeScript ya infiere los tipos automáticamente gracias al Payload */}
                    {getParsedResponse(selectedReview.response)?.findings?.map((f, idx) => (
                      <div key={idx} className="p-3 bg-white border border-gray-200 rounded-lg text-sm">
                        <strong className="text-gray-800 block">{f.title}</strong>
                        <span className="text-gray-600">{f.description} (Línea {f.line})</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedReview.student_comment && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-1">Comentario Humano Registrado</h4>
                  <p className="text-sm bg-gray-100 text-gray-800 p-3 rounded-lg border border-gray-200 italic">"{selectedReview.student_comment}"</p>
                </div>
              )}
            </div>

            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end">
              <button onClick={() => setSelectedReview(null)} className="px-5 py-2 bg-gray-900 hover:bg-gray-800 text-white text-sm font-bold rounded-lg transition cursor-pointer">
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}