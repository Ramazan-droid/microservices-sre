const API = "";

export async function api(endpoint, options = {}) {
  const res = await fetch(API + endpoint, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await res.json().catch(() => ({}));
  return { res, data };
}