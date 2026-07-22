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
    <nav className="bg-gray-900 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          
          <div className="flex items-center space-x-8">
            <h1 className="text-xl font-bold tracking-wider">IA CodeReview</h1>
            <div className="hidden md:flex space-x-4">
              <Link to="/review" className="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium transition">
                Nueva Revisión
              </Link>
              {/* Solo mostramos estos enlaces si hay sesión activa */}
              {session && (
                <>
                  <Link to="/dashboard" className="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium transition">
                    Dashboard
                  </Link>
                  <Link to="/history" className="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium transition">
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
                className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-md text-sm font-bold transition"
              >
                Cerrar Sesión
              </button>
            ) : (
              <Link to="/login" className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-md text-sm font-bold transition">
                Iniciar Sesión
              </Link>
            )}
          </div>

        </div>
      </div>
    </nav>
  );
}