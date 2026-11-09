import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function HomePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  async function onLogout() {
    setSubmitting(true);
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <main className="account-screen">
      <header className="account-bar">
        <p className="brand-mark">RentNear</p>
        <button type="button" onClick={onLogout} disabled={submitting}>
          {submitting ? "Signing out…" : "Log out"}
        </button>
      </header>
      <section className="account-card">
        <p className="eyebrow">Signed in</p>
        <h1>{user.name || user.email}</h1>
        <dl>
          <div>
            <dt>Email</dt>
            <dd>{user.email}</dd>
          </div>
          <div>
            <dt>Phone</dt>
            <dd>{user.phone || "Not provided"}</dd>
          </div>
        </dl>
        <p className="lede">Listings, search, and booking will be added in the next stories.</p>
      </section>
    </main>
  );
}
