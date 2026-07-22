import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './AuthContext';
import ProtectedRoute from './components/ProtectedRoute';

import Navbar from './components/Navbar'; // <-- IMPORTA EL NAVBAR AQUÍ
import Login from './pages/Login';
import Register from './pages/Register';
import CodeReviewForm from './pages/CodeReviewForm';
import Dashboard from './pages/Dashboard';
import History from './pages/History';

export default function App() {
  return (
    <AuthProvider>
      <Router>
        {/* EL NAVBAR VA AQUÍ ADENTRO DEL ROUTER */}
        <Navbar /> 
        
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/review" element={<CodeReviewForm />} />

          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />

          <Route path="*" element={<Navigate to="/review" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}