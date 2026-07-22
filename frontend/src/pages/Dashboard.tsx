import { useState, useEffect } from 'react';
import apiFetch from '../utils/apiFetch';

interface DashboardMetrics {
  total_reviews: number;
  reviews_by_language: Record<string, number>;
  reviews_by_status: Record<string, number>;
  regenerated_count: number;
  most_frequent_findings: Array<string | Record<string, unknown>>; 
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await apiFetch('/api/dashboard/metrics');
        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.error || `Error del servidor: ${response.status}`);
        }
        
        const data = await response.json();
        setMetrics(data);
      } catch (err: unknown) {
        // CORREGIDO GAP 8: Adiós mock data.
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Error de conexión al cargar las métricas.");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, []);

  // CORREGIDO GAP 2: Usamos 'accepted' en minúsculas y en inglés
  const accepted = metrics?.reviews_by_status?.['accepted'] || 0;
  const acceptanceRate = metrics?.total_reviews 
    ? Math.round((accepted / metrics.total_reviews) * 100) 
    : 0;

  const getTopLanguage = () => {
    if (!metrics?.reviews_by_language) return 'N/A';
    const entries = Object.entries(metrics.reviews_by_language);
    if (entries.length === 0) return 'N/A';
    return entries.reduce((a, b) => a[1] > b[1] ? a : b)[0];
  };

  const getTopError = () => {
    if (!metrics?.most_frequent_findings || metrics.most_frequent_findings.length === 0) return 'N/A';
    const topError = metrics.most_frequent_findings[0];
    return typeof topError === 'string' ? topError : (String(topError.title) || 'Error detectado');
  };

  if (loading) return <div className="flex h-screen items-center justify-center font-bold text-gray-600">Cargando panel de métricas...</div>;

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Dashboard de Análisis</h1>
          <p className="text-gray-500 mt-2">Métricas globales del uso de Inteligencia Artificial en el código.</p>
        </div>

        {error ? (
          <div className="p-8 text-center text-red-600 font-bold bg-red-50 rounded-xl border border-red-200">{error}</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Revisiones Totales</h3>
              <p className="text-3xl font-black text-gray-800 mt-2">{metrics?.total_reviews}</p>
            </div>
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Tasa de Aceptación</h3>
              <p className="text-3xl font-black text-green-600 mt-2">{acceptanceRate}%</p>
            </div>
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Lenguaje Principal</h3>
              <p className="text-2xl font-bold text-blue-600 mt-2">{getTopLanguage()}</p>
            </div>
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Error más común</h3>
              <p className="text-sm font-bold text-red-600 mt-2 leading-tight">{getTopError()}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}