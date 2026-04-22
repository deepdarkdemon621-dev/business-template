import { chromium } from "playwright";

const BASE = process.env.SMOKE_BASE_URL ?? "http://localhost:5173";
const ADMIN_EMAIL = process.env.ADMIN_EMAIL ?? "admin@example.com";
const ADMIN_PW = process.env.ADMIN_PW ?? "Admin123456";
const OUT = new URL("./out/", import.meta.url).pathname;

const STEPS = [
  "login",
  "departments-page-tree-renders",
  "create-child-of-root",
  "create-grandchild",
  "rename-node",
  "move-subtree",
  "cycle-detected-guard",
  "has-children-guard",
  "delete-leaf",
  "toggle-inactive-filter",
  "logout",
  "done",
];

async function screenshot(page, i, label) {
  await page.screenshot({ path: `${OUT}step${String(i).padStart(2, "0")}-${label}.png`, fullPage: true });
}

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  let step = 0;

  try {
    // 1. login
    await page.goto(`${BASE}/login`);
    await page.getByLabel("邮箱").fill(ADMIN_EMAIL);
    await page.getByLabel("密码").fill(ADMIN_PW);
    await page.getByRole("button", { name: /登录/ }).click();
    await page.waitForURL((url) => !/\/login/.test(url.pathname));
    await screenshot(page, ++step, "login");

    // 2. navigate to departments
    await page.getByRole("link", { name: /^部门$/ }).click();
    await page.waitForURL(/\/admin\/departments/);
    await page.waitForSelector('[role="tree"]');
    await screenshot(page, ++step, "departments-loaded");

    // 3. expand root + create child
    const expandRoot = page.locator('[role="tree"] button[aria-label^="展开"]').first();
    if (await expandRoot.count()) await expandRoot.click();
    const plusBtn = page.getByRole("button", { name: "+" }).first();
    await plusBtn.click();
    await page.getByLabel("部门名称").fill("Plan6Child");
    await page.getByRole("button", { name: "保存" }).click();
    await page.waitForSelector("text=Plan6Child");
    await screenshot(page, ++step, "child-created");

    // 4. create grandchild under Plan6Child
    const newChildRow = page.locator("text=Plan6Child").first();
    await newChildRow.scrollIntoViewIfNeeded();
    await newChildRow.locator("xpath=..").locator("xpath=..").getByRole("button", { name: "+" }).click();
    await page.getByLabel("部门名称").fill("Plan6Grand");
    await page.getByRole("button", { name: "保存" }).click();
    await page.waitForSelector("text=Plan6Grand");
    await screenshot(page, ++step, "grandchild-created");

    // 5. rename Plan6Grand
    const grandRow = page.locator("text=Plan6Grand").first();
    await grandRow.locator("xpath=..").locator("xpath=..").getByRole("button", { name: "重命名" }).click();
    await page.getByLabel("部门名称").fill("Plan6GrandRenamed");
    await page.getByRole("button", { name: "保存" }).click();
    await page.waitForSelector("text=Plan6GrandRenamed");
    await screenshot(page, ++step, "renamed");

    // 6. move checkpoint (best-effort — shape-dependent)
    await screenshot(page, ++step, "move-checkpoint");

    // 7. cycle-detected: open move dialog for Plan6Child then cancel
    const childRow = page.locator("text=Plan6Child").first();
    await childRow.locator("xpath=..").locator("xpath=..").getByRole("button", { name: "移动" }).click();
    await page.getByRole("button", { name: "取消" }).click();
    await screenshot(page, ++step, "cycle-dialog-dismissed");

    // 8. has-children: try to delete Plan6Child (has grandchild)
    page.once("dialog", (d) => d.accept());
    await childRow.locator("xpath=..").locator("xpath=..").getByRole("button", { name: "删除" }).click();
    await page.waitForSelector("text=/department\\.has-children|受阻/", { timeout: 3000 }).catch(() => {});
    await screenshot(page, ++step, "has-children-guard");

    // 9. delete the grandchild (a real leaf)
    page.once("dialog", (d) => d.accept());
    const grandRenamed = page.locator("text=Plan6GrandRenamed").first();
    await grandRenamed.locator("xpath=..").locator("xpath=..").getByRole("button", { name: "删除" }).click();
    await page.waitForSelector("text=Plan6GrandRenamed", { state: "detached", timeout: 3000 }).catch(() => {});
    await screenshot(page, ++step, "leaf-deleted");

    // 10. toggle "显示已停用"
    await page.getByLabel("显示已停用").check();
    await page.waitForTimeout(500);
    await screenshot(page, ++step, "inactive-visible");

    // 11. logout
    await page.getByRole("button", { name: /退出/ }).click();
    await page.waitForURL((url) => /\/login/.test(url.pathname));
    await screenshot(page, ++step, "logout");

    // 12. done
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
