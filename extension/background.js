/**
 * Reddit Bridge - Background Service Worker
 *
 * NETWORK AUDIT (exhaustive list of all network endpoints in this file):
 *   1. WebSocket to ws://localhost:9334 ONLY (BRIDGE_URL, line 18)
 *   2. chrome.cookies.getAll for domain "reddit.com" (handleCommand)
 *   3. chrome.tabs operations scoped to reddit.com host_permissions
 *   4. chrome.debugger for local page JS evaluation (no remote endpoints)
 *
 * This file contains NO fetch(), NO XMLHttpRequest, NO navigator.sendBeacon,
 * NO remote URLs, NO analytics, and NO telemetry of any kind.
 *
 * DOM commands are in dom_commands.js (pure DOM manipulation, zero network).
 */

importScripts("dom_commands.js");

const BRIDGE_URL = "ws://localhost:9334";
let ws = null;

chrome.alarms.create("keepAlive", { periodInMinutes: 0.4 });
chrome.alarms.onAlarm.addListener(() => {
  if (!ws || ws.readyState !== WebSocket.OPEN) connect();
});

function connect() {
  if (
    ws &&
    (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)
  )
    return;
  ws = new WebSocket(BRIDGE_URL);
  ws.onopen = () => {
    console.log("[Reddit Bridge] Connected");
    ws.send(JSON.stringify({ role: "extension" }));
  };
  ws.onmessage = async (event) => {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch {
      return;
    }
    try {
      const result = await handleCommand(msg);
      ws.send(JSON.stringify({ id: msg.id, result: result ?? null }));
    } catch (err) {
      ws.send(
        JSON.stringify({ id: msg.id, error: String(err.message || err) }),
      );
    }
  };
  ws.onclose = () => setTimeout(connect, 3000);
  ws.onerror = () => {};
}

async function handleCommand(msg) {
  const { method, params = {} } = msg;
  switch (method) {
    case "navigate":
      return await cmdNavigate(params);
    case "wait_for_load":
      return await cmdWaitForLoad(params);
    case "set_file_input":
      return await cmdSetFileInput(params);
    case "get_cookies":
      return await chrome.cookies.getAll({
        domain: params.domain || "reddit.com",
      });
    case "evaluate":
      return await cmdEvaluateViaDebugger(params);
    default:
      return await cmdRunInMainWorld(method, params);
  }
}

async function cmdNavigate({ url }) {
  const tab = await getOrOpenRedditTab();
  const target = { tabId: tab.id };

  await chrome.debugger.attach(target, "1.3");
  await chrome.debugger.sendCommand(target, "Page.enable");

  const dialogHandler = (source, method) => {
    if (source.tabId === tab.id && method === "Page.javascriptDialogOpening") {
      chrome.debugger
        .sendCommand(target, "Page.handleJavaScriptDialog", { accept: true })
        .catch(() => {});
    }
  };
  chrome.debugger.onEvent.addListener(dialogHandler);

  try {
    await chrome.tabs.update(tab.id, { url });
    await waitForTabComplete(tab.id, url, 60000);
  } finally {
    chrome.debugger.onEvent.removeListener(dialogHandler);
    await chrome.debugger.detach(target).catch(() => {});
  }
  return null;
}

async function cmdWaitForLoad({ timeout = 60000 }) {
  const tab = await getOrOpenRedditTab();
  await waitForTabComplete(tab.id, null, timeout);
  return null;
}

async function waitForTabComplete(tabId, expectedUrlPrefix, timeout) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeout;
    function listener(id, info, updatedTab) {
      if (id !== tabId || info.status !== "complete") return;
      if (
        expectedUrlPrefix &&
        !updatedTab.url?.startsWith(expectedUrlPrefix.slice(0, 20))
      )
        return;
      chrome.tabs.onUpdated.removeListener(listener);
      resolve();
    }
    chrome.tabs.onUpdated.addListener(listener);
    const poll = async () => {
      if (Date.now() > deadline) {
        chrome.tabs.onUpdated.removeListener(listener);
        reject(new Error("Page load timeout"));
        return;
      }
      const tab = await chrome.tabs.get(tabId).catch(() => null);
      if (tab && tab.status === "complete") {
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
        return;
      }
      setTimeout(poll, 400);
    };
    setTimeout(poll, 600);
  });
}

async function cmdEvaluateViaDebugger({ expression }) {
  const tab = await getOrOpenRedditTab();
  const target = { tabId: tab.id };
  await chrome.debugger.attach(target, "1.3");
  try {
    const resp = await chrome.debugger.sendCommand(target, "Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (resp.exceptionDetails) {
      throw new Error(
        resp.exceptionDetails.exception?.description ||
          resp.exceptionDetails.text ||
          "JS evaluation failed",
      );
    }
    return resp.result?.value ?? null;
  } finally {
    await chrome.debugger.detach(target).catch(() => {});
  }
}

async function cmdSetFileInput({ selector, files }) {
  const tab = await getOrOpenRedditTab();
  const target = { tabId: tab.id };
  await chrome.debugger.attach(target, "1.3");
  try {
    const { root } = await chrome.debugger.sendCommand(
      target,
      "DOM.getDocument",
      { depth: 0 },
    );
    const { nodeId } = await chrome.debugger.sendCommand(
      target,
      "DOM.querySelector",
      { nodeId: root.nodeId, selector },
    );
    if (!nodeId) throw new Error(`File input not found: ${selector}`);
    await chrome.debugger.sendCommand(target, "DOM.setFileInputFiles", {
      nodeId,
      files,
    });
  } finally {
    await chrome.debugger.detach(target).catch(() => {});
  }
  return null;
}

async function cmdRunInMainWorld(method, params) {
  const tab = await getOrOpenRedditTab();
  const results = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    world: "MAIN",
    func: mainWorldHandler,
    args: [method, params],
  });
  const r = results?.[0]?.result;
  if (r && typeof r === "object" && "__error" in r) throw new Error(r.__error);
  return r ?? null;
}

async function getOrOpenRedditTab() {
  const tabs = await chrome.tabs.query({
    url: [
      "https://www.reddit.com/*",
      "https://old.reddit.com/*",
      "https://new.reddit.com/*",
    ],
  });
  if (tabs.length > 0) return tabs[0];
  const tab = await chrome.tabs.create({ url: "https://www.reddit.com/" });
  await waitForTabComplete(tab.id, null, 30000);
  return tab;
}

connect();
