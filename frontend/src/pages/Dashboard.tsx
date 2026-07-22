import { useState, useEffect } from 'react';
import apiFetch from '../utils/apiFetch';

// Definimos la estructura de datos basada en el RF-10
interface DashboardMetrics {
  total_reviews: number;
  accepted_reviews: number;
  top_language: string;
  most_common_error: string;
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        // Intentamos pegarle al endpoint que construirá Fernando
        const response = await apiFetch('/api/metrics');
        
        if (!response.ok) {
          throw new Error('Error al cargar métricas');
        }
        
        const data = await response.json();
        setMetrics(data);
      } catch {
        // MOCK: Datos de prueba para que puedas ver el diseño mientras el backend termina su parte
        setMetrics({
          total_reviews: 42,
          accepted_reviews: 35,
          top_language: 'Python',
          most_common_error: 'Falta de validación de inputs'
        });
        console.warn("Usando datos simulados. El endpoint /api/metrics no está disponible aún.");
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, []);

  if (loading) {
    return <div className="flex h-screen items-center justify-center font-bold text-gray-600">Cargando panel de métricas...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Dashboard de Análisis</h1>
          <p className="text-gray-500 mt-2">Métricas globales del uso de Inteligencia Artificial en el código.</p>
        </div>

        {/* Grid de Tarjetas de Métricas */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Revisiones Totales</h3>
            <p className="text-3xl font-black text-gray-800 mt-2">{metrics?.total_reviews}</p>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Tasa de Aceptación</h3>
            <p className="text-3xl font-black text-green-600 mt-2">
              {metrics ? Math.round((metrics.accepted_reviews / metrics.total_reviews) * 100) : 0}%
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Lenguaje Principal</h3>
            <p className="text-2xl font-bold text-blue-600 mt-2">{metrics?.top_language}</p>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Error más común</h3>
            <p className="text-sm font-bold text-red-600 mt-2 leading-tight">{metrics?.most_common_error}</p>
          </div>

        </div>

      </div>
    </div>
  );
}