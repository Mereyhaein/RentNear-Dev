export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <main className="auth-screen">
      <section className="brand-panel">
        <p className="brand-mark">RentNear</p>
        <h1>Borrow what you need from people nearby.</h1>
        <p>
          A peer-to-peer rental marketplace for students and young adults. Create an account to
          list items and book rentals.
        </p>
      </section>
      <section className="form-panel">
        <h2>{title}</h2>
        <p className="lede">{subtitle}</p>
        {children}
        <div className="form-footer">{footer}</div>
      </section>
    </main>
  );
}
