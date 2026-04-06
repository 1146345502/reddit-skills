/**
 * Reddit Bridge - Background Service Worker
 *
 * Connects to Python bridge server (ws://localhost:9334), receives commands and executes:
 * - navigate / wait_for_load: chrome.tabs.update + onUpdated
 * - evaluate / has_element etc: chrome.scripting.executeScript (MAIN world)
 * - click / input etc DOM ops: MAIN world injection
 * - screenshot: chrome.tabs.captureVisibleTab
 * - get_cookies: chrome.cookies.getAll
 */

const BRIDGE_URL = "ws://localhost:9334";
let ws = null;

chrome.alarms.create("keepAlive", { periodInMinutes: 0.4 });
chrome.alarms.onAlarm.addListener(() => {
  if (!ws || ws.readyState !== WebSocket.OPEN) connect();
});

// ───────────────────────── WebSocket ─────────────────────────

function connect() {
  if (
    ws &&
    (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)
  )
    return;

  ws = new WebSocket(BRIDGE_URL);

  ws.onopen = () => {
    console.log("[Reddit Bridge] Connected to bridge server");
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

  ws.onclose = () => {
    console.log("[Reddit Bridge] Disconnected, reconnecting in 3s...");
    setTimeout(connect, 3000);
  };

  ws.onerror = (e) => {
    console.error("[Reddit Bridge] WS error", e);
  };
}

// ───────────────────────── Command Router ─────────────────────────

async function handleCommand(msg) {
  const { method, params = {} } = msg;

  switch (method) {
    case "navigate":
      return await cmdNavigate(params);

    case "wait_for_load":
      return await cmdWaitForLoad(params);

    case "screenshot_element":
      return await cmdScreenshot(params);

    case "set_file_input":
      return await cmdSetFileInputViaDebugger(params);

    case "get_cookies":
      return await cmdGetCookies(params);

    case "evaluate":
      return await cmdEvaluateViaDebugger(params);

    case "wait_dom_stable":
    case "wait_for_selector":
    case "has_element":
    case "get_elements_count":
    case "get_element_text":
    case "get_element_attribute":
    case "get_scroll_top":
    case "get_viewport_height":
    case "get_url":
      return await cmdEvaluateInMainWorld(method, params);

    default:
      return await cmdDomInMainWorld(method, params);
  }
}

// ───────────────────────── Navigation ─────────────────────────

async function cmdNavigate({ url }) {
  const tab = await getOrOpenRedditTab();
  await chrome.tabs.update(tab.id, { url });
  await waitForTabComplete(tab.id, url, 60000);
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
      if (id !== tabId) return;
      if (info.status !== "complete") return;
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

// ───────────────────────── Screenshot ─────────────────────────

async function cmdScreenshot() {
  const tab = await getOrOpenRedditTab();
  const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, {
    format: "png",
  });
  return { data: dataUrl.split(",")[1] };
}

// ───────────────────────── Cookies ─────────────────────────

async function cmdGetCookies({ domain = "reddit.com" }) {
  return await chrome.cookies.getAll({ domain });
}

// ───────────────────────── JS evaluation via Debugger (bypasses CSP) ────────

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
      const desc =
        resp.exceptionDetails.exception?.description ||
        resp.exceptionDetails.text ||
        "JS evaluation failed";
      throw new Error(desc);
    }
    return resp.result?.value ?? null;
  } finally {
    await chrome.debugger.detach(target).catch(() => {});
  }
}

// ───────────────────────── MAIN world JS execution ─────────────────────────

async function cmdEvaluateInMainWorld(method, params) {
  const tab = await getOrOpenRedditTab();
  const results = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    world: "MAIN",
    func: mainWorldExecutor,
    args: [method, params],
  });
  const r = results?.[0]?.result;
  if (r && typeof r === "object" && "__reddit_error" in r) {
    throw new Error(r.__reddit_error);
  }
  return r;
}

function mainWorldExecutor(method, params) {
  function poll(check, interval, timeout) {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      (function tick() {
        const result = check();
        if (result !== false && result !== null && result !== undefined) {
          resolve(result);
          return;
        }
        if (Date.now() - start >= timeout) {
          reject(new Error("Timeout"));
          return;
        }
        setTimeout(tick, interval);
      })();
    });
  }

  switch (method) {
    case "has_element":
      return document.querySelector(params.selector) !== null;

    case "get_elements_count":
      return document.querySelectorAll(params.selector).length;

    case "get_element_text": {
      const el = document.querySelector(params.selector);
      return el ? el.textContent : null;
    }

    case "get_element_attribute": {
      const el = document.querySelector(params.selector);
      return el ? el.getAttribute(params.attr) : null;
    }

    case "get_scroll_top":
      return window.pageYOffset || document.documentElement.scrollTop || 0;

    case "get_viewport_height":
      return window.innerHeight;

    case "get_url":
      return window.location.href;

    case "wait_dom_stable": {
      const timeout = params.timeout || 10000;
      const interval = params.interval || 500;
      return new Promise((resolve) => {
        let last = -1;
        const start = Date.now();
        (function tick() {
          const size = document.body ? document.body.innerHTML.length : 0;
          if (size === last && size > 0) {
            resolve(null);
            return;
          }
          last = size;
          if (Date.now() - start >= timeout) {
            resolve(null);
            return;
          }
          setTimeout(tick, interval);
        })();
      });
    }

    case "wait_for_selector": {
      const timeout = params.timeout || 30000;
      return poll(
        () => (document.querySelector(params.selector) ? true : false),
        200,
        timeout,
      ).catch(() => {
        throw new Error(`Timeout waiting for element: ${params.selector}`);
      });
    }

    default:
      return { __reddit_error: `Unknown MAIN world method: ${method}` };
  }
}

// ───────────────────────── File upload (chrome.debugger + CDP) ─────────

async function cmdSetFileInputViaDebugger({ selector, files }) {
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
      {
        nodeId: root.nodeId,
        selector,
      },
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

// ───────────────────────── DOM operations (MAIN world) ────────────────────

async function cmdDomInMainWorld(method, params) {
  const tab = await getOrOpenRedditTab();
  const results = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    world: "MAIN",
    func: domExecutor,
    args: [method, params],
  });
  const r = results?.[0]?.result;
  if (r && typeof r === "object" && "__reddit_error" in r) {
    throw new Error(r.__reddit_error);
  }
  return r ?? null;
}

function domExecutor(method, params) {
  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  function requireEl(selector) {
    const el = document.querySelector(selector);
    if (!el) return { __reddit_error: `Element not found: ${selector}` };
    return el;
  }

  switch (method) {
    case "click_element": {
      const el = requireEl(params.selector);
      if (el.__reddit_error) return el;
      el.scrollIntoView({ block: "center" });
      el.focus();
      el.click();
      return null;
    }

    case "input_text": {
      const el = requireEl(params.selector);
      if (el.__reddit_error) return el;
      el.focus();
      const nativeInputValueSetter =
        Object.getOwnPropertyDescriptor(
          window.HTMLInputElement.prototype,
          "value",
        )?.set ||
        Object.getOwnPropertyDescriptor(
          window.HTMLTextAreaElement.prototype,
          "value",
        )?.set;
      if (nativeInputValueSetter) {
        nativeInputValueSetter.call(el, params.text);
      } else {
        el.value = params.text;
      }
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return null;
    }

    case "input_content_editable": {
      return new Promise(async (resolve) => {
        const el = document.querySelector(params.selector);
        if (!el) {
          resolve({ __reddit_error: `Element not found: ${params.selector}` });
          return;
        }
        el.focus();
        document.execCommand("selectAll", false, null);
        document.execCommand("delete", false, null);
        await sleep(80);
        const lines = params.text.split("\n");
        for (let i = 0; i < lines.length; i++) {
          if (lines[i]) document.execCommand("insertText", false, lines[i]);
          if (i < lines.length - 1) {
            document.execCommand("insertParagraph", false, null);
            await sleep(30);
          }
        }
        resolve(null);
      });
    }

    case "set_file_input": {
      return new Promise((resolve) => {
        const el = document.querySelector(params.selector);
        if (!el) {
          resolve({
            __reddit_error: `File input not found: ${params.selector}`,
          });
          return;
        }

        function makeFiles() {
          const dt = new DataTransfer();
          for (const f of params.files) {
            const bytes = Uint8Array.from(atob(f.data), (c) => c.charCodeAt(0));
            dt.items.add(new File([bytes], f.name, { type: f.type }));
          }
          return dt;
        }

        try {
          const dt = makeFiles();
          Object.defineProperty(el, "files", {
            value: dt.files,
            configurable: true,
            writable: true,
          });
          el.dispatchEvent(new Event("change", { bubbles: true }));
          el.dispatchEvent(new Event("input", { bubbles: true }));
        } catch (e) {}

        const dropTarget =
          el.closest('[class*="upload"]') ||
          el.closest('[class*="Upload"]') ||
          el.parentElement;
        if (dropTarget) {
          try {
            const dt2 = makeFiles();
            dropTarget.dispatchEvent(
              new DragEvent("dragenter", {
                bubbles: true,
                cancelable: true,
                dataTransfer: dt2,
              }),
            );
            dropTarget.dispatchEvent(
              new DragEvent("dragover", {
                bubbles: true,
                cancelable: true,
                dataTransfer: dt2,
              }),
            );
            dropTarget.dispatchEvent(
              new DragEvent("drop", {
                bubbles: true,
                cancelable: true,
                dataTransfer: dt2,
              }),
            );
          } catch (e) {}
        }

        resolve(null);
      });
    }

    case "scroll_by":
      window.scrollBy(params.x || 0, params.y || 0);
      return null;
    case "scroll_to":
      window.scrollTo(params.x || 0, params.y || 0);
      return null;
    case "scroll_to_bottom":
      window.scrollTo(0, document.body.scrollHeight);
      return null;

    case "scroll_element_into_view": {
      const el = document.querySelector(params.selector);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      return null;
    }
    case "scroll_nth_element_into_view": {
      const els = document.querySelectorAll(params.selector);
      if (els[params.index])
        els[params.index].scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      return null;
    }

    case "dispatch_wheel_event": {
      const target = document.documentElement;
      target.dispatchEvent(
        new WheelEvent("wheel", {
          deltaY: params.deltaY || 0,
          deltaMode: 0,
          bubbles: true,
          cancelable: true,
        }),
      );
      return null;
    }

    case "mouse_move":
      document.dispatchEvent(
        new MouseEvent("mousemove", {
          clientX: params.x,
          clientY: params.y,
          bubbles: true,
        }),
      );
      return null;

    case "mouse_click": {
      const el = document.elementFromPoint(params.x, params.y);
      if (el) {
        ["mousedown", "mouseup", "click"].forEach((t) =>
          el.dispatchEvent(
            new MouseEvent(t, {
              clientX: params.x,
              clientY: params.y,
              bubbles: true,
            }),
          ),
        );
      }
      return null;
    }

    case "press_key": {
      const active = document.activeElement || document.body;
      const keyMap = {
        Enter: { key: "Enter", code: "Enter", keyCode: 13 },
        ArrowDown: { key: "ArrowDown", code: "ArrowDown", keyCode: 40 },
        Tab: { key: "Tab", code: "Tab", keyCode: 9 },
        Backspace: { key: "Backspace", code: "Backspace", keyCode: 8 },
        Escape: { key: "Escape", code: "Escape", keyCode: 27 },
      };
      const info = keyMap[params.key] || {
        key: params.key,
        code: params.key,
        keyCode: 0,
      };
      active.dispatchEvent(
        new KeyboardEvent("keydown", { ...info, bubbles: true }),
      );
      active.dispatchEvent(
        new KeyboardEvent("keyup", { ...info, bubbles: true }),
      );
      return null;
    }

    case "type_text": {
      return new Promise(async (resolve) => {
        const active = document.activeElement || document.body;
        const inCE = active.isContentEditable;
        for (const char of params.text) {
          if (inCE) {
            document.execCommand("insertText", false, char);
          } else {
            active.dispatchEvent(
              new KeyboardEvent("keydown", { key: char, bubbles: true }),
            );
            active.dispatchEvent(
              new KeyboardEvent("keypress", { key: char, bubbles: true }),
            );
            active.dispatchEvent(
              new KeyboardEvent("keyup", { key: char, bubbles: true }),
            );
          }
          await sleep(params.delayMs || 50);
        }
        resolve(null);
      });
    }

    case "remove_element": {
      const el = document.querySelector(params.selector);
      if (el) el.remove();
      return null;
    }

    case "hover_element": {
      const el = document.querySelector(params.selector);
      if (el) {
        const rect = el.getBoundingClientRect();
        const x = rect.left + rect.width / 2,
          y = rect.top + rect.height / 2;
        el.dispatchEvent(
          new MouseEvent("mouseover", {
            clientX: x,
            clientY: y,
            bubbles: true,
          }),
        );
        el.dispatchEvent(
          new MouseEvent("mousemove", {
            clientX: x,
            clientY: y,
            bubbles: true,
          }),
        );
      }
      return null;
    }

    case "select_all_text": {
      const el = document.querySelector(params.selector);
      if (el) {
        el.focus();
        if (el.select) el.select();
        else document.execCommand("selectAll");
      }
      return null;
    }

    default:
      return { __reddit_error: `Unknown DOM command: ${method}` };
  }
}

// ───────────────────────── Tab Management ─────────────────────────

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

// ───────────────────────── Start ─────────────────────────

connect();
