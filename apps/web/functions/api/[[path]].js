// Every /api/* request on the Pages origin goes to the API Worker through its service binding,
// unchanged: same method, headers and body. The Worker routes by pathname, so it does not care
// which host the request came in on. Nothing is logged here. The share cards under /api/share/*
// are static files and never reach this function: public/_routes.json keeps them out.
export async function onRequest({ request, env }) {
  return env.API.fetch(request);
}
