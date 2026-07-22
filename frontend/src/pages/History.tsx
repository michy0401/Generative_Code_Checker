import { useState, useEffect } from 'react';
import apiFetch from '../utils/apiFetch';

// ACTUALIZADO: Ahora coincide con el contrato real del backend de Michelle
interface ReviewRecord {
  review_id: string; // <-- Cambiado de 'id' a 'review_id'
  created_at: string;
  language: string;
  review_type: string;
  status: string;
  prompt_sent?: string;
  response?: string;
  student_code?: string;
}

export default function History() {
  const [reviews, setReviews] = useState<ReviewRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await apiFetch('/api/reviews/mine');
        if (!response.ok) throw new Error('Error al cargar historial');
        
        const data = await response.json();
        setReviews(data);
      } catch {
        // MOCK ACTUALIZADO con review_id
        setReviews([
          { review_id: '1', created_at: '2026-07-20T10:00:00Z', language: 'Python', review_type: 'Errores y Bugs', status: 'Aceptado' },
          { review_id: '2', created_at: '2026-07-21T14:30:00Z', language: 'JavaScript', review_type: 'Buenas Prácticas', status: 'Regenerado' },
          { review_id: '3', created_at: '2026-07-21T16:45:00Z', language: 'Java', review_type: 'Rendimiento', status: 'Descartado' },
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  if (loading) {
    return <div className="flex h-screen items-center justify-center font-bold text-gray-600">Cargando tu historial...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        
        <div className="px-6 py-5 border-b border-gray-200 bg-gray-900">
          <h2 className="text-xl font-bold text-white">Mi Historial de Revisiones</h2>
        </div>

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
                // Usamos review_id en lugar de id
                <tr key={review.review_id} className="hover:bg-gray-50 transition">
                  <td className="px-6 py-4 text-sm text-gray-800">
                    {new Date(review.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{review.language}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{review.review_type}</td>
                  <td className="px-6 py-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                      review.status === 'Aceptado' ? 'bg-green-100 text-green-800' :
                      review.status === 'Regenerado' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {review.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button className="text-blue-600 hover:text-blue-800 text-sm font-semibold">Ver Detalle</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {reviews.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              No tienes revisiones registradas todavía.
            </div>
          )}
        </div>

      </div>
    </div>
  );
}