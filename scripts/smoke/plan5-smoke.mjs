import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

const BASE = "http://localhost:18080";
const ADMIN = { email: "admin@example.com", password: "Admin12345!" };
const OUT = new URL("./out/", import.meta.url).pathname.replace(/^\//, "");
mkdirSync(OUT, { recursive: true });

const results = [];
let stepNum = 0;
async function step(page, name, fn) {
  stepNum++;
  const label = `${String(stepNum).padStart(2, "0")} ${name}`;
  try {
    await fn();
    await page.screenshot({ path: join(OUT, `${label.replace(/[^a-z0-9]+/gi, "_")}.png`), fullPage: true });
    results.push({ label, status: "PASS" });
    console.log(`PASS  ${label}`);
  } catch (err) {
    try { await page.screenshot({ path: join(OUT, `FAIL_${label.replace(/[^a-z0-9]+/gi, "_")}.png`), fullPage: true }); } catch {}
    results.push({ label, status: "FAIL", error: String(err?.message ?? err) });
    console.log(`FAIL  ${label}  — ${err?.message ?? err}`);
    throw err;
  }
}

async function login(page, email, password) {
  await page.goto(`${BASE}/login`);
  await page.fill('input[type="email"], input#email', email);
  await page.fill('input[type="password"], input#password', password);
  await Promise.all([
    page.waitForURL(/\/(dashboard|admin|password-change)/, { timeout: 10_000 }),
    page.click('button[type="submit"]'),
  ]);
}

const browser = await chromium.launch({ channel: "chrome", headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
page.on("pageerror", (e) => console.log("PAGEERROR:", e.message));
page.on("console", (msg) => { if (msg.type() === "error") console.log("CONSOLE.ERROR:", msg.text()); });

// Generate a unique email once so entire flow references the same user.
const uniq = `newuser_${Date.now()}@ex.com`;
const uniqName = "烟雾测试新用户";
const initialPass = "TempPass12345!";
const newPass = "PermPass12345!";

try {
  // 1. Login as admin
  await step(page, "admin login", async () => {
    await login(page, ADMIN.email, ADMIN.password);
  });

  // 2. Sidebar shows 仪表盘 + 用户管理
  await step(page, "sidebar renders", async () => {
    await page.waitForSelector('text=仪表盘', { timeout: 5000 });
    await page.waitForSelector('text=用户管理', { timeout: 5000 });
  });

  // 3. Navigate to user list
  await step(page, "navigate to user list", async () => {
    await page.click('text=用户管理');
    await page.waitForURL(/\/admin\/users/, { timeout: 5000 });
    await page.waitForSelector('table', { timeout: 5000 });
  });

  // 4. Create new user
  await step(page, "open create-user form", async () => {
    await page.click('text=新建用户');
    await page.waitForURL(/\/admin\/users\/new/, { timeout: 5000 });
    await page.waitForSelector('text=新建用户');
  });

  await step(page, "fill + submit create form", async () => {
    await page.fill('input#email', uniq);
    await page.fill('input#fullName', uniqName);
    await page.fill('input#password', initialPass);
    await page.click('button:has-text("创建")');
    await page.waitForURL(/\/admin\/users\/[0-9a-f-]+$/, { timeout: 10_000 });
  });

  // 5. Edit: RoleAssignmentPanel renders + toggle a role
  const newUserUrl = page.url();
  const newUserId = newUserUrl.split("/").pop();

  await step(page, "role panel renders", async () => {
    // shadcn Checkbox is a Radix button with role="checkbox"
    await page.waitForSelector('[role="checkbox"]', { timeout: 5000 });
    const count = await page.locator('[role="checkbox"]').count();
    if (count < 1) throw new Error(`expected at least one role checkbox, got ${count}`);
  });

  await step(page, "assign a role + save", async () => {
    const boxes = page.locator('[role="checkbox"]');
    const n = await boxes.count();
    let toggled = false;
    for (let i = 0; i < n; i++) {
      const box = boxes.nth(i);
      const state = await box.getAttribute("data-state");
      if (state !== "checked") {
        await box.click();
        toggled = true;
        break;
      }
    }
    if (!toggled) throw new Error("no unchecked role to toggle");
    await page.click('button:has-text("保存")');
    await page.waitForURL(/\/admin\/users$/, { timeout: 10_000 });
  });

  // 6. Logout admin
  await step(page, "admin logout", async () => {
    const logout = page.getByRole("button", { name: /退出/ });
    if (await logout.count() > 0) {
      await logout.first().click();
      await page.waitForURL(/\/login/, { timeout: 5000 });
    } else {
      await context.clearCookies();
      await page.evaluate(() => { sessionStorage.clear(); localStorage.clear(); });
      await page.goto(`${BASE}/login`);
    }
  });

  // 7. Login as new user → mustChangePassword redirect
  await step(page, "new user login → password-change redirect", async () => {
    await page.goto(`${BASE}/login`);
    await page.fill('input#email', uniq);
    await page.fill('input#password', initialPass);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/password-change/, { timeout: 10_000 });
  });

  // 8. Change password
  await step(page, "change password", async () => {
    await page.fill('input#currentPassword, input[name="currentPassword"]', initialPass);
    await page.fill('input#newPassword, input[name="newPassword"]', newPass);
    await page.fill('input#confirm, input[name="confirm"]', newPass);
    await page.click('button[type="submit"]');
    await page.waitForURL((url) => !/\/password-change/.test(url.pathname), { timeout: 10_000 });
  });

  // 9. Re-login as admin, revisit user, verify role persisted
  await step(page, "admin re-login + inspect new user", async () => {
    await context.clearCookies();
    await page.evaluate(() => { sessionStorage.clear(); localStorage.clear(); });
    await login(page, ADMIN.email, ADMIN.password);
    await page.goto(`${BASE}/admin/users/${newUserId}`);
    await page.waitForSelector('[role="checkbox"][data-state="checked"]', { timeout: 5000 });
  });

  // 10. Attempt self-delete → blocked with 自我保护 message
  await step(page, "self-delete blocked by SelfProtection", async () => {
    await page.goto(`${BASE}/admin/users`);
    await page.waitForSelector('table', { timeout: 5000 });
    // Find admin's own row
    const row = page.locator('tr', { hasText: ADMIN.email });
    await row.waitFor({ timeout: 5000 });
    const del = row.getByRole("button", { name: /删除|Delete/ });
    if (await del.count() === 0) {
      console.log("note: delete button hidden for admin self; SelfProtection also enforced at guard layer");
      return;
    }
    page.once("dialog", (d) => d.accept());
    await del.first().click();
    await page.getByText(/自我保护|self-protection/).waitFor({ timeout: 5000 });
  });

  // 11. Soft-delete filter (?is_active=false)
  await step(page, "soft-delete filter URL works", async () => {
    await page.goto(`${BASE}/admin/users?is_active=false`);
    await page.waitForSelector('table', { timeout: 5000 });
  });

  // 12. Done
  await step(page, "smoke complete", async () => { /* noop */ });

} catch (err) {
  console.log("\nABORTED:", err?.message ?? err);
} finally {
  await browser.close();
  const passed = results.filter((r) => r.status === "PASS").length;
  const failed = results.filter((r) => r.status === "FAIL").length;
  console.log(`\n=== SMOKE SUMMARY ===`);
  console.log(`PASSED: ${passed} / ${results.length}`);
  console.log(`FAILED: ${failed}`);
  if (failed > 0) process.exitCode = 1;
}
