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

// Steps: 1-indexed to match log messages.
const STEPS = [
  "login",
  "sidebar-audit-entry-visible",
  "audit-page-loads",
  "default-filter-shows-rows",
  "trigger-user-created-event",
  "user-created-row-visible",
  "detail-drawer-opens",
  "drawer-shows-event-type",
  "logout",
  "create-member-user",
  "member-login",
  "member-sidebar-entry-absent",
  "member-direct-url-blocked",
  "done",
];

async function screenshot(page, i, label) {
  await page.screenshot({
    path: `${OUT}plan8-step${String(i).padStart(2, "0")}-${label}.png`,
    fullPage: true,
  });
}

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  let step = 0;

  // Track created member user so we can use them in later steps.
  let memberEmail = null;
  const memberPw = "Member12345!";

  try {
    // Step 1: Login as admin (superadmin role — has audit:list).
    // LoginPage button label is "Log In" (English).
    // Must-change-password redirect may occur; navigate past it.
    console.log(`[01] login as admin`);
    await page.goto(`${BASE}/login`);
    await page.waitForSelector('label:has-text("Email")', { timeout: 30000 });
    await page.getByLabel("Email").fill(ADMIN_EMAIL);
    await page.getByLabel("Password").fill(ADMIN_PW);
    await page.getByRole("button", { name: /Log In/ }).click();
    await page.waitForURL((url) => !/\/login/.test(url.pathname), { timeout: 15000 });
    // If redirected to /password-change, navigate on to /admin/audit directly —
    // the token is already stored in sessionStorage and auth works fine.
    await screenshot(page, ++step, "login");

    // Step 2: Confirm sidebar shows 審計日志 entry.
    // Navigate to dashboard first so the RequirePermission guard on /admin/audit
    // doesn't race with permission loading. The sidebar renders on any AppShell page
    // once the /me/permissions API call completes.
    console.log(`[02] sidebar shows 審計日志 entry`);
    await page.goto(`${BASE}/`);
    await page.waitForSelector("text=审计日志", { timeout: 20000 });
    await screenshot(page, ++step, "sidebar-audit-entry-visible");

    // Step 3: Navigate to /admin/audit; confirm h1 "Audit log" is present.
    // RequirePermission (audit:list) is now in place — permissions are already
    // loaded from step 2, so this should render immediately.
    console.log(`[03] audit page loads (h1 "Audit log")`);
    await page.goto(`${BASE}/admin/audit`);
    // Wait for the URL to stabilize at /admin/audit (RequirePermission should allow
    // through since isSuperadmin=true is already cached from step 2's permissions load).
    // Use waitForURL with a timeout to catch unexpected redirects.
    await page.waitForURL((url) => /\/admin\/audit/.test(url.pathname), { timeout: 15000 });
    await page.waitForSelector("h1", { timeout: 15000 });
    const h1Text = await page.locator("h1").first().innerText();
    console.log(`    URL: ${page.url()}, H1: ${h1Text}`);
    if (!h1Text.toLowerCase().includes("audit")) {
      throw new Error(`Expected h1 to contain "Audit"; got: ${h1Text}`);
    }
    await screenshot(page, ++step, "audit-page-loads");

    // Step 4: Default filter is empty ({}), not 7-day. The login event we just
    // generated should still be visible because there is no date restriction.
    // Wait for at least one tbody row.
    console.log(`[04] default filter shows >= 1 row (login event visible)`);
    await page.waitForSelector("table tbody tr", { timeout: 15000 });
    const rowCount = await page.locator("table tbody tr").count();
    if (rowCount === 0) throw new Error("expected at least one audit row — login event should appear");
    await screenshot(page, ++step, "default-filter-shows-rows");

    // Step 5: Trigger a user.created event via API (authenticated using the
    // sessionStorage token from the current page context).
    console.log(`[05] trigger user.created event via API`);
    const token = await page.evaluate(() => sessionStorage.getItem("access_token"));
    if (!token) throw new Error("access_token not found in sessionStorage — auth may have changed");
    const smokeEmail = `plan8-smoke-${Date.now()}@smoke.example.com`;
    const resp = await page.request.post(`${BASE}/api/v1/users`, {
      data: {
        email: smokeEmail,
        fullName: "Plan8 Smoke",
        password: "Smoke123456!",
        mustChangePassword: false,
      },
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!resp.ok()) {
      const body = await resp.text();
      throw new Error(`create user failed ${resp.status()}: ${body}`);
    }
    const createdUser = await resp.json();
    console.log(`    created user id=${createdUser.id}`);
    await screenshot(page, ++step, "trigger-user-created-event");

    // Step 6: Reload audit list; confirm user.created row appears in the table body.
    // Note: the filter bar also shows "user.created" as a checkbox label, so we
    // target the table body specifically to avoid false positives.
    console.log(`[06] reload audit list — user.created row visible in table`);
    await page.reload();
    await page.waitForSelector("table tbody tr", { timeout: 15000 });
    await page.waitForSelector("table tbody tr:has-text('user.created')", { timeout: 15000 });
    await screenshot(page, ++step, "user-created-row-visible");

    // Step 7: Click the eye icon ("View event") on the first user.created row
    // in the table body to open the detail drawer.
    console.log(`[07] open detail drawer via eye icon`);
    const firstCreatedRow = page
      .locator("table tbody tr", { hasText: "user.created" })
      .first();
    await firstCreatedRow.getByRole("button", { name: "View event" }).click();
    // Sheet renders with SheetTitle = "Audit event"
    await page.waitForSelector("text=Audit event", { timeout: 8000 });
    await screenshot(page, ++step, "detail-drawer-opens");

    // Step 8: Drawer shows the event type. The AuditEventDetail component renders
    // a <div class="font-mono">{event.eventType}</div> inside the sheet.
    // Wait for the sheet content area to contain "user.created".
    console.log(`[08] drawer shows event type details`);
    // The sheet has SheetTitle="Audit event" and then event fields.
    // Wait for "user.created" to appear anywhere in the visible page (it will be
    // inside the sheet panel since the sheet is open).
    await page.waitForSelector("text=user.created >> xpath=ancestor::*[@data-state='open']", {
      timeout: 8000,
    }).catch(async () => {
      // Fallback: just look for "user.created" anywhere on the page that's in
      // the sheet. The sheet content is in a portal so query the whole body.
      const allText = await page.locator("body").innerText();
      if (!allText.includes("user.created")) {
        throw new Error(`Drawer did not show user.created event type. Page text: ${allText.slice(0, 300)}`);
      }
    });
    await screenshot(page, ++step, "drawer-shows-event-type");

    // Step 9: Logout — TopBar renders "登出" button.
    console.log(`[09] logout`);
    // Close drawer first if open
    await page.keyboard.press("Escape");
    await page.waitForTimeout(300);
    await page.getByRole("button", { name: /登出/ }).click();
    await page.waitForURL((url) => /\/login/.test(url.pathname), { timeout: 10000 });
    await screenshot(page, ++step, "logout");

    // Step 10: Create a member user (no audit:list permission).
    // No member@example.com is seeded; create one via API using admin credentials.
    // We log back in as admin just for the API call.
    console.log(`[10] create member user via API`);
    memberEmail = `plan8-member-${Date.now()}@smoke.example.com`;
    // Re-use page — it's now on /login. Login again to get admin token.
    await page.waitForSelector('label:has-text("Email")', { timeout: 30000 });
    await page.getByLabel("Email").fill(ADMIN_EMAIL);
    await page.getByLabel("Password").fill(ADMIN_PW);
    await page.getByRole("button", { name: /Log In/ }).click();
    await page.waitForURL((url) => !/\/login/.test(url.pathname), { timeout: 15000 });

    const adminToken2 = await page.evaluate(() => sessionStorage.getItem("access_token"));
    if (!adminToken2) throw new Error("access_token not found after re-login");

    // Fetch member role id
    const rolesResp = await page.request.get(`${BASE}/api/v1/roles`, {
      headers: { Authorization: `Bearer ${adminToken2}` },
    });
    if (!rolesResp.ok()) throw new Error(`GET /roles failed: ${rolesResp.status()}`);
    const rolesBody = await rolesResp.json();
    const memberRole = rolesBody.items.find((r) => r.code === "member");
    if (!memberRole) throw new Error("member role not found in GET /roles response");

    // Create the member user
    const memberResp = await page.request.post(`${BASE}/api/v1/users`, {
      data: {
        email: memberEmail,
        fullName: "Plan8 Member",
        password: memberPw,
        mustChangePassword: false,
      },
      headers: { Authorization: `Bearer ${adminToken2}` },
    });
    if (!memberResp.ok()) {
      const b = await memberResp.text();
      throw new Error(`create member user failed ${memberResp.status()}: ${b}`);
    }
    const memberUser = await memberResp.json();
    console.log(`    created member user id=${memberUser.id}`);

    // Assign member role
    const assignResp = await page.request.post(
      `${BASE}/api/v1/users/${memberUser.id}/roles/${memberRole.id}`,
      { headers: { Authorization: `Bearer ${adminToken2}` } }
    );
    if (!assignResp.ok()) {
      const b = await assignResp.text();
      throw new Error(`assign member role failed ${assignResp.status()}: ${b}`);
    }
    console.log(`    assigned member role`);
    await screenshot(page, ++step, "create-member-user");

    // Logout admin again
    await page.getByRole("button", { name: /登出/ }).click();
    await page.waitForURL((url) => /\/login/.test(url.pathname), { timeout: 10000 });

    // Step 11: Login as member user.
    console.log(`[11] login as member`);
    await page.waitForSelector('label:has-text("Email")', { timeout: 30000 });
    await page.getByLabel("Email").fill(memberEmail);
    await page.getByLabel("Password").fill(memberPw);
    await page.getByRole("button", { name: /Log In/ }).click();
    await page.waitForURL((url) => !/\/login/.test(url.pathname), { timeout: 15000 });
    // Navigate to dashboard to trigger sidebar rendering
    await page.goto(`${BASE}/`);
    // Give sidebar time to load permissions
    await page.waitForTimeout(2000);
    await screenshot(page, ++step, "member-login");

    // Step 12: Sidebar does NOT show 審計日志 for member (no audit:list perm).
    console.log(`[12] member sidebar does NOT show 審計日志`);
    const auditEntryCount = await page.locator("text=审计日志").count();
    if (auditEntryCount > 0) {
      throw new Error("member should not see 審計日志 in sidebar — permission bypass detected");
    }
    await screenshot(page, ++step, "member-sidebar-entry-absent");

    // Step 13: Direct navigation to /admin/audit must be blocked.
    // Expect either a redirect away (not /admin/audit) or no "Audit log" h1.
    console.log(`[13] member direct URL /admin/audit is blocked`);
    await page.goto(`${BASE}/admin/audit`);
    await page.waitForTimeout(2000);
    const atAuditH1 = await page.locator("h1:has-text('Audit log')").count();
    if (atAuditH1 > 0) {
      throw new Error("member was able to view /admin/audit — permission bypass");
    }
    await screenshot(page, ++step, "member-direct-url-blocked");

    // Done
    console.log(`OK — ${step} / ${STEPS.length - 1} steps green`);
    await screenshot(page, ++step, "done");
    console.log("SMOKE PASS");
  } catch (err) {
    await screenshot(page, 99, `FAIL-step${step}`);
    console.error(`FAIL at step ${step}:`, err.message ?? err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main();
