// The web server's port, read in one place (UPDATE_30 section 1 item 5). WEB_PORT moves it for
// the Playwright config, the tests, the design check and the screen scripts; package.json's dev and
// start read the same variable. 3100 is the default, so make e2e and make dev work as before.
// make judge-check sets WEB_PORT to a free port it picked, so a busy 3100 cannot fail it.
const raw = process.env.WEB_PORT ?? "";
const port = raw === "" ? 3100 : Number(raw);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error(`WEB_PORT must be a port number from 1 to 65535, not "${raw}"`);
}

export const WEB_PORT = port;
export const WEB_ORIGIN = `http://127.0.0.1:${port}`;
