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

  if (loading) return (
    <div className="flex h-screen items-center justify-center bg-slate-50">
      <div className="flex flex-col items-center">
        <svg className="animate-spin h-10 w-10 text-indigo-600 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
        <span className="font-bold text-slate-600">Cargando panel de métricas...</span>
      </div>
    </div>
  );

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-slate-50 py-12 px-4 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-6xl mx-auto">
        <div className="mb-10 text-center md:text-left">
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Dashboard Analítico</h1>
          <p className="text-slate-500 mt-2 font-medium">Métricas globales y comportamiento de la IA en la revisión de código.</p>
        </div>

        {error ? (
          <div className="p-6 bg-rose-50 border border-rose-200 rounded-2xl flex items-center shadow-sm">
            <svg className="w-8 h-8 text-rose-600 mr-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <div>
              <h3 className="text-lg font-bold text-rose-800">Error al cargar datos</h3>
              <p className="text-rose-700 text-sm font-medium mt-1">{error}</p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            
            <div className="bg-white p-8 rounded-3xl shadow-lg shadow-slate-200/40 border border-slate-100 hover:-translate-y-1 transition-transform duration-300">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Revisiones Totales</h3>
                <div className="p-2 bg-indigo-50 rounded-lg text-indigo-600">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path></svg>
                </div>
              </div>
              <p className="text-4xl font-black text-slate-800">{metrics?.total_reviews}</p>
            </div>

            <div className="bg-white p-8 rounded-3xl shadow-lg shadow-slate-200/40 border border-slate-100 hover:-translate-y-1 transition-transform duration-300">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Tasa de Aceptación</h3>
                <div className="p-2 bg-emerald-50 rounded-lg text-emerald-600">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                </div>
              </div>
              <p className="text-4xl font-black text-emerald-600">{acceptanceRate}%</p>
            </div>

            <div className="bg-white p-8 rounded-3xl shadow-lg shadow-slate-200/40 border border-slate-100 hover:-translate-y-1 transition-transform duration-300">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Lenguaje Top</h3>
                <div className="p-2 bg-sky-50 rounded-lg text-sky-600">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path></svg>
                </div>
              </div>
              <p className="text-2xl font-bold text-sky-600 truncate">{getTopLanguage()}</p>
            </div>

            <div className="bg-white p-8 rounded-3xl shadow-lg shadow-slate-200/40 border border-slate-100 hover:-translate-y-1 transition-transform duration-300">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Error Frecuente</h3>
                <div className="p-2 bg-amber-50 rounded-lg text-amber-600">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                </div>
              </div>
              <p className="text-sm font-bold text-amber-700 leading-tight line-clamp-3">{getTopError()}</p>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}