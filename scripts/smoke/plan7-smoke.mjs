import { chromium } from "playwright";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

// Use nginx at 18080 — it proxies /api/* to backend and / to Vite dev server.
const BASE = process.env.SMOKE_BASE_URL ?? "http://localhost:18080";
const ADMIN_EMAIL = process.env.ADMIN_EMAIL ?? "admin@example.com";
const ADMIN_PW = process.env.ADMIN_PW ?? "Admin12345!";
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const OUT = join(__dirname, "out") + "/";

const STEPS = [
  "login",
  "roles-page-loads",
  "builtin-roles-visible",
  "new-role-nav",
  "form-filled",
  "user-read-global-granted",
  "saved-redirected",
  "new-role-in-list",
  "edit-nav",
  "dept-read-own-granted",
  "edit-saved",
  "plan7-smoke-still-visible",
  "delete-dialog-opened",
  "typed-role-code",
  "delete-confirmed",
  "builtin-delete-disabled",
  "logout",
  "done",
];

async function screenshot(page, i, label) {
  await page.screenshot({
    path: `${OUT}step${String(i).padStart(2, "0")}-${label}.png`,
    fullPage: true,
  });
}

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  let step = 0;

  try {
    // 1. Login — LoginPage renders "Email" / "Password" / "Log In" (English schema titles)
    //    Admin has mustChangePassword=true so login redirects to /password-change, but
    //    the auth token is stored in sessionStorage and all protected routes remain reachable.
    await page.goto(`${BASE}/login`);
    await page.getByLabel("Email").fill(ADMIN_EMAIL);
    await page.getByLabel("Password").fill(ADMIN_PW);
    await page.getByRole("button", { name: /Log In/ }).click();
    // Wait until we leave /login (may land on / or /password-change)
    await page.waitForURL((url) => !/\/login/.test(url.pathname), { timeout: 15000 });
    await screenshot(page, ++step, "login");

    // 2. Navigate directly to /admin/roles (sidebar may not be visible on /password-change)
    await page.goto(`${BASE}/admin/roles`);
    await page.waitForURL(/\/admin\/roles/);
    // Wait for the DataTable to populate — admin role is always present
    await page.waitForSelector("text=admin", { timeout: 15000 });
    await screenshot(page, ++step, "roles-page-loads");

    // 3. Verify built-in roles are visible in the table — wait for all three to appear
    await page.waitForSelector("text=member", { timeout: 10000 });
    await page.waitForSelector("text=superadmin", { timeout: 10000 });
    await screenshot(page, ++step, "builtin-roles-visible");

    // 4. Click "+ New role" link → navigate to /admin/roles/new
    await page.getByRole("link", { name: /\+ New role/ }).click();
    await page.waitForURL(/\/admin\/roles\/new/, { timeout: 10000 });
    await screenshot(page, ++step, "new-role-nav");

    // 5. Fill Code and Name (FormRenderer renders labels from schema title: "Code" / "Name")
    await page.getByLabel("Code").fill("plan7_smoke");
    await page.getByLabel("Name").fill("Plan 7 Smoke");
    await screenshot(page, ++step, "form-filled");

    // 6. Grant user:read at scope global
    //    RolePermissionMatrix aria-label pattern: `${p.code} ${c.label}`
    //    SCOPE_CHOICES labels: "Not granted" | "own" | "dept" | "dept_tree" | "global"
    await page.getByRole("radio", { name: "user:read global" }).click();
    await screenshot(page, ++step, "user-read-global-granted");

    // 7. Click Save, wait for navigation back to /admin/roles
    await page.getByRole("button", { name: /^Save$/ }).click();
    await page.waitForURL(/\/admin\/roles$/, { timeout: 15000 });
    await screenshot(page, ++step, "saved-redirected");

    // 8. Verify plan7_smoke appears in the list
    await page.waitForSelector("text=plan7_smoke", { timeout: 10000 });
    await screenshot(page, ++step, "new-role-in-list");

    // 9. Click "Edit" on the plan7_smoke row
    const plan7Row = page.locator("tr", { hasText: "plan7_smoke" });
    await plan7Row.getByRole("link", { name: /^Edit$/ }).click();
    await page.waitForURL(/\/admin\/roles\/[^/]+$/, { timeout: 10000 });
    await screenshot(page, ++step, "edit-nav");

    // 10. Add department:read at scope own
    await page.getByRole("radio", { name: "department:read own" }).click();
    await screenshot(page, ++step, "dept-read-own-granted");

    // 11. Click Save, wait for navigation back
    await page.getByRole("button", { name: /^Save$/ }).click();
    await page.waitForURL(/\/admin\/roles$/, { timeout: 15000 });
    await screenshot(page, ++step, "edit-saved");

    // 12. Verify plan7_smoke still visible
    await page.waitForSelector("text=plan7_smoke", { timeout: 10000 });
    await screenshot(page, ++step, "plan7-smoke-still-visible");

    // 13. Click "Delete" on the plan7_smoke row → confirmation dialog opens
    const plan7RowDel = page.locator("tr", { hasText: "plan7_smoke" });
    await plan7RowDel.getByRole("button", { name: /^Delete$/ }).click();
    await page.waitForSelector('[role="dialog"]', { timeout: 8000 });
    await screenshot(page, ++step, "delete-dialog-opened");

    // 14. Type the role code into the confirmation input
    //     Label: "Type the role code plan7_smoke to confirm" → input id="confirm-role-code"
    await page.locator("#confirm-role-code").fill("plan7_smoke");
    await screenshot(page, ++step, "typed-role-code");

    // 15. Click "Confirm delete" — dialog closes, role disappears from list
    await page.getByRole("button", { name: /Confirm delete/ }).click();
    // Dialog should close
    await page.waitForSelector('[role="dialog"]', { state: "detached", timeout: 10000 });
    // plan7_smoke row should disappear
    await page.waitForSelector("text=plan7_smoke", { state: "detached", timeout: 10000 });
    await screenshot(page, ++step, "delete-confirmed");

    // 16. Verify built-in "admin" role's Delete button is disabled
    const adminRow = page.locator("tr", { hasText: /^admin/ }).first();
    const adminDeleteBtn = adminRow.getByRole("button", { name: /^Delete$/ });
    const isDisabled = await adminDeleteBtn.isDisabled();
    if (!isDisabled) throw new Error("Expected admin role Delete button to be disabled but it was enabled");
    await screenshot(page, ++step, "builtin-delete-disabled");

    // 17. Logout — TopBar renders "登出" button
    await page.getByRole("button", { name: /登出/ }).click();
    await page.waitForURL((url) => /\/login/.test(url.pathname), { timeout: 10000 });
    await screenshot(page, ++step, "logout");

    // 18. Done
    console.log(`OK — ${step} / ${STEPS.length - 1} steps green`);
    await screenshot(page, ++step, "done");
  } catch (err) {
    await screenshot(page, 99, `FAIL-step${step}`);
    console.error(`FAIL at step ${step}:`, err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main();
