import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { supabase } from '../supabaseClient';

export default function Navbar() {
  const { session } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await supabase.auth.signOut();
    navigate('/login');
  };

  return (
    <nav className="sticky top-0 z-50 bg-slate-900/95 backdrop-blur-md border-b border-slate-800 text-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          
          <div className="flex items-center space-x-8">
            <h1 className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
              IA CodeReview
            </h1>
            <div className="hidden md:flex space-x-2">
              <Link to="/review" className="hover:bg-slate-800 hover:text-indigo-300 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200">
                Nueva Revisión
              </Link>
              {/* Solo mostramos estos enlaces si hay sesión activa */}
              {session && (
                <>
                  <Link to="/dashboard" className="hover:bg-slate-800 hover:text-indigo-300 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200">
                    Dashboard
                  </Link>
                  <Link to="/history" className="hover:bg-slate-800 hover:text-indigo-300 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200">
                    Mi Historial
                  </Link>
                </>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {session ? (
              <button 
                onClick={handleLogout}
                className="text-slate-300 hover:text-red-400 hover:bg-slate-800 px-4 py-2 rounded-lg text-sm font-bold transition-all duration-200"
              >
                Cerrar Sesión
              </button>
            ) : (
              <Link to="/login" className="bg-indigo-600 hover:bg-indigo-500 shadow-md shadow-indigo-900/20 px-5 py-2 rounded-lg text-sm font-bold transition-all duration-200 hover:-translate-y-0.5">
                Iniciar Sesión
              </Link>
            )}
          </div>

        </div>
      </div>
    </nav>
  );
}