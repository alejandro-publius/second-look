import { defineConfig, devices } from "@playwright/test";
import { WEB_ORIGIN } from "./scripts/web-port.mjs";

// Tests run against a production build on port 3100 so the real CSP headers are in force.
// WEB_PORT moves it (scripts/web-port.mjs); package.json's start script reads the same variable.
// The API origin is a fake one that every test mocks with page.route; nothing is ever sent there.
export const API_ORIGIN = "http://127.0.0.1:8100";

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 2,
  // CI tries a failed test once more, to show whether it is flaky or broken, and fails the run
  // either way: a test that passes only on its retry is not green.
  retries: process.env.CI ? 1 : 0,
  failOnFlakyTests: !!process.env.CI,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    ...devices["iPhone 13"],
    browserName: "chromium",
    baseURL: WEB_ORIGIN,
    serviceWorkers: "block",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run build && npm run start",
    url: `${WEB_ORIGIN}/`,
    // This checkout's own build: when something already answers on the port (make dev, make
    // demo-offline, another session), the run stops with a port in use error instead of testing it.
    // The one exception is scripts/design-check.mjs, which starts this build on the port itself just
    // before and says so with PW_REUSE=1.
    reuseExistingServer: process.env.PW_REUSE === "1",
    timeout: 240_000,
    env: {
      NEXT_PUBLIC_API_ORIGIN: API_ORIGIN,
      NEXT_PUBLIC_SITE_URL: WEB_ORIGIN,
      NEXT_PUBLIC_BUILD_HASH: "test",
      NEXT_TELEMETRY_DISABLED: "1",
    },
  },
});
