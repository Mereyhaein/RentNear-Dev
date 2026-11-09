import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, api, parseApiErrors } from "../api";
import { useAuth } from "../auth";
import AuthLayout from "../components/AuthLayout";
import { validateRegister } from "../validation";

const INITIAL = {
  name: "",
  email: "",
  phone: "",
  password: "",
  confirmPassword: "",
};

export default function RegisterPage() {
  const navigate = useNavigate();
  const { setSession } = useAuth();
  const [values, setValues] = useState(INITIAL);
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
    const nextErrors = validateRegister(values);
    setErrors(nextErrors);
    setFormError("");
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      const data = await api("/api/auth/register", {
        method: "POST",
        body: {
          name: values.name.trim(),
          email: values.email.trim(),
          phone: values.phone.trim(),
          password: values.password,
        },
      });
      setSession(data.token, data.user);
      navigate("/", { replace: true });
    } catch (error) {
      if (error instanceof ApiError && error.data) {
        const parsed = parseApiErrors(error.data);
        setErrors(parsed.fields);
        setFormError(parsed.form.join(" "));
      } else {
        setFormError(error.message || "Could not create the account.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Use your email and a password. No payment details are collected."
      footer={
        <p>
          Already have an account? <Link to="/login">Log in</Link>
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
          Name
          <input
            name="name"
            autoComplete="name"
            value={values.name}
            onChange={update}
            aria-invalid={Boolean(errors.name)}
          />
          {errors.name ? <span className="field-error">{errors.name}</span> : null}
        </label>
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
          Phone <span className="optional">optional</span>
          <input
            name="phone"
            type="tel"
            autoComplete="tel"
            value={values.phone}
            onChange={update}
            aria-invalid={Boolean(errors.phone)}
          />
          {errors.phone ? <span className="field-error">{errors.phone}</span> : null}
        </label>
        <label>
          Password
          <input
            name="password"
            type="password"
            autoComplete="new-password"
            value={values.password}
            onChange={update}
            aria-invalid={Boolean(errors.password)}
          />
          {errors.password ? <span className="field-error">{errors.password}</span> : null}
        </label>
        <label>
          Confirm password
          <input
            name="confirmPassword"
            type="password"
            autoComplete="new-password"
            value={values.confirmPassword}
            onChange={update}
            aria-invalid={Boolean(errors.confirmPassword)}
          />
          {errors.confirmPassword ? (
            <span className="field-error">{errors.confirmPassword}</span>
          ) : null}
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? "Creating account…" : "Create account"}
        </button>
      </form>
    </AuthLayout>
  );
}
