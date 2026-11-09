const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

function messageFromValue(value) {
  if (Array.isArray(value)) {
    return value.map((item) => (typeof item === "string" ? item : JSON.stringify(item))).join(" ");
  }
  if (typeof value === "string") return value;
  return "Check this field.";
}

export function parseApiErrors(data) {
  const fields = {};
  const form = [];
  if (!data || typeof data !== "object") {
    return { form: ["Something went wrong. Try again."], fields };
  }
  for (const [key, value] of Object.entries(data)) {
    const message = messageFromValue(value);
    if (key === "detail" || key === "non_field_errors") form.push(message);
    else fields[key] = message;
  }
  if (form.length === 0 && Object.keys(fields).length === 0) {
    form.push("Something went wrong. Try again.");
  }
  return { form, fields };
}

export async function api(path, { method = "GET", body, token } = {}) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers: {
        ...(body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...(token ? { Authorization: `Token ${token}` } : {}),
      },
      body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Cannot reach the RentNear server. Check that the API is running.", 0, null);
  }

  if (response.status === 204) return null;

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: "Unexpected response from the server." };
    }
  }

  if (!response.ok) {
    const parsed = parseApiErrors(data);
    throw new ApiError(parsed.form[0] || "Request failed.", response.status, data);
  }
  return data;
}
