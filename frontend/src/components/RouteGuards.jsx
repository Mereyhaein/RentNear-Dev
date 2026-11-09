import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth";

export function ProtectedRoute({ children }) {
  const { user, token, loading, sessionError } = useAuth();
  const location = useLocation();

  if (loading) return <p className="screen-status">Checking your session…</p>;
  if (sessionError && token && !user) {
    return (
      <p className="screen-status" role="alert">
        {sessionError}
      </p>
    );
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return children;
}

export function GuestRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <p className="screen-status">Checking your session…</p>;
  if (user) return <Navigate to="/" replace />;
  return children;
}
