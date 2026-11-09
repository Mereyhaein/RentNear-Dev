import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ApiError, api, parseApiErrors } from "../api";
import { useAuth } from "../auth";
import AuthLayout from "../components/AuthLayout";
import { validateLogin } from "../validation";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setSession } = useAuth();
  const [values, setValues] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update(event) {
    const { name, value } = event.target;
    setValues((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: undefined }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    const nextErrors = validateLogin(values);
    setErrors(nextErrors);
    setFormError("");
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      const data = await api("/api/auth/login", {
        method: "POST",
        body: {
          email: values.email.trim(),
          password: values.password,
        },
      });
      setSession(data.token, data.user);
      const from = location.state?.from;
      navigate(typeof from === "string" && from.startsWith("/") && !from.startsWith("//") ? from : "/", { replace: true });
    } catch (error) {
      if (error instanceof ApiError && error.data) {
        const parsed = parseApiErrors(error.data);
        setErrors(parsed.fields);
        setFormError(parsed.form.join(" "));
      } else {
        setFormError(error.message || "Could not log in.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="Log in"
      subtitle="Use the email and password for your RentNear account."
      footer={
        <p>
          New to RentNear? <Link to="/register">Create an account</Link>
        </p>
      }
    >
      <form onSubmit={onSubmit} noValidate>
        {formError ? (
          <p className="alert" role="alert">
            {formError}
          </p>
        ) : null}
        <label>
          Email
          <input
            name="email"
            type="email"
            autoComplete="email"
            value={values.email}
            onChange={update}
            aria-invalid={Boolean(errors.email)}
          />
          {errors.email ? <span className="field-error">{errors.email}</span> : null}
        </label>
        <label>
          Password
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            value={values.password}
            onChange={update}
            aria-invalid={Boolean(errors.password)}
          />
          {errors.password ? <span className="field-error">{errors.password}</span> : null}
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? "Signing in…" : "Log in"}
        </button>
      </form>
    </AuthLayout>
  );
}
