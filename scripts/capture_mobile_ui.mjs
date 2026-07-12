import fs from "node:fs";

const debugPort = Number(process.env.OMS_CHROME_DEBUG_PORT || 9224);
const baseUrl = process.env.OMS_CAPTURE_URL || "http://127.0.0.1:8790/";
const outputPath = process.env.OMS_CAPTURE_OUTPUT || "mobile-ui-check.png";
const routeHash = process.env.OMS_CAPTURE_HASH || "";

const target = await fetch(`http://127.0.0.1:${debugPort}/json/new?${encodeURIComponent(baseUrl)}`, { method: "PUT" }).then((response) => response.json());
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});

let requestId = 0;
const pending = new Map();
socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (!message.id || !pending.has(message.id)) return;
  const { resolve, reject } = pending.get(message.id);
  pending.delete(message.id);
  if (message.error) reject(new Error(message.error.message));
  else resolve(message.result);
});

function command(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++requestId;
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  const result = await command("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}

await command("Page.enable");
await command("Runtime.enable");
await command("Network.enable");
if (process.env.OMS_CAPTURE_IDENTITY) {
  const identity = JSON.parse(process.env.OMS_CAPTURE_IDENTITY);
  await command("Network.setUserAgentOverride", { userAgent: "Mozilla/5.0 Feishu Mobile OMS" });
  await command("Page.addScriptToEvaluateOnNewDocument", {
    source: `window.h5sdk = window.h5sdk || {}; window.tt = { requestAccess() {} }; window.OMS_USER_CONTEXT = ${JSON.stringify(identity)};`,
  });
}
await command("Emulation.setDeviceMetricsOverride", {
  width: 390,
  height: 844,
  deviceScaleFactor: 1,
  mobile: true,
});
await command("Page.navigate", { url: baseUrl });
await new Promise((resolve) => setTimeout(resolve, 5500));
if (routeHash) {
  await evaluate(`window.location.hash = ${JSON.stringify(routeHash.replace(/^#/, ""))}`);
  await new Promise((resolve) => setTimeout(resolve, 900));
}
if (process.env.OMS_CAPTURE_CLICK_PATH) {
  const labels = JSON.parse(process.env.OMS_CAPTURE_CLICK_PATH);
  for (const label of labels) {
    await evaluate(`(() => {
      const nodes = [...document.querySelectorAll(".mobile-primary-card strong, .mobile-secondary-card strong")];
      const node = nodes.find((entry) => entry.textContent.trim() === ${JSON.stringify(label)});
      if (!node) throw new Error("未找到手机菜单：" + ${JSON.stringify(label)});
      node.closest("a").click();
      return true;
    })()`);
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
}
if (process.env.OMS_CAPTURE_OPEN_DRAWER === "1") {
  await evaluate(`document.querySelector("#mobileMenuButton")?.click()`);
  await new Promise((resolve) => setTimeout(resolve, 350));
}

const pageState = await evaluate(`(() => ({
  width: document.documentElement.clientWidth,
  bodyWidth: document.body.scrollWidth,
  title: document.querySelector("#mobilePageTitle")?.textContent || "",
  user: document.querySelector("#mobileUserSummary")?.textContent || "",
  route: document.querySelector("#mobileWorkspaceRoot")?.dataset.mobileRoute || "",
  primaryMenus: [...document.querySelectorAll(".mobile-primary-card strong")].map((node) => node.textContent),
  secondaryMenus: [...document.querySelectorAll(".mobile-secondary-card strong")].map((node) => node.textContent),
  drawerMenus: [...document.querySelectorAll("#businessNavigationDrawer .navigation-parent span:last-child")].map((node) => node.textContent),
  drawerOpen: document.body.classList.contains("mobile-navigation-open"),
  visibleForeignWords: [...new Set((document.body.innerText.match(/[A-Za-z][A-Za-z_-]*/g) || []).filter((word) => word !== "OMS"))],
  desktopSidebarPosition: document.querySelector("#businessNavigationDrawer") ? getComputedStyle(document.querySelector("#businessNavigationDrawer")).transform : "missing",
  documentTitle: document.title,
  location: location.href,
}))()`);

const screenshot = await command("Page.captureScreenshot", { format: "png", fromSurface: true });
fs.writeFileSync(outputPath, Buffer.from(screenshot.data, "base64"));
console.log(JSON.stringify(pageState));
socket.close();
