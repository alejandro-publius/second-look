// The landing page wakes the API with GET /health before anyone needs it. Same origin now.
export async function onRequest({ request, env }) {
  return env.API.fetch(request);
}
