/**
 * Reddit Bridge - DOM Command Handler
 *
 * Pure DOM manipulation functions injected into reddit.com pages.
 * NETWORK: This file makes ZERO network calls. No fetch, XMLHttpRequest,
 * WebSocket, sendBeacon, or any outbound communication of any kind.
 * All functions operate exclusively on the local DOM.
 */

// eslint-disable-next-line no-unused-vars
function mainWorldHandler(method, params) {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  const qel = (sel) => {
    const el = document.querySelector(sel);
    return el || { __error: `Element not found: ${sel}` };
  };

  switch (method) {
    case "has_element":
      return document.querySelector(params.selector) !== null;
    case "get_elements_count":
      return document.querySelectorAll(params.selector).length;
    case "get_element_text": {
      const e = document.querySelector(params.selector);
      return e ? e.textContent : null;
    }
    case "get_element_attribute": {
      const e = document.querySelector(params.selector);
      return e ? e.getAttribute(params.attr) : null;
    }
    case "get_scroll_top":
      return window.pageYOffset || document.documentElement.scrollTop || 0;
    case "get_viewport_height":
      return window.innerHeight;
    case "get_url":
      return window.location.href;

    case "wait_dom_stable": {
      const t = params.timeout || 10000,
        iv = params.interval || 500;
      return new Promise((resolve) => {
        let last = -1;
        const start = Date.now();
        (function tick() {
          const sz = document.body ? document.body.innerHTML.length : 0;
          if ((sz === last && sz > 0) || Date.now() - start >= t) {
            resolve(null);
            return;
          }
          last = sz;
          setTimeout(tick, iv);
        })();
      });
    }

    case "wait_for_selector": {
      const t = params.timeout || 30000;
      return new Promise((resolve, reject) => {
        const start = Date.now();
        (function tick() {
          if (document.querySelector(params.selector)) {
            resolve(true);
            return;
          }
          if (Date.now() - start >= t) {
            reject(new Error(`Timeout: ${params.selector}`));
            return;
          }
          setTimeout(tick, 200);
        })();
      });
    }

    case "click_element": {
      const e = qel(params.selector);
      if (e.__error) return e;
      e.scrollIntoView({ block: "center" });
      e.focus();
      e.click();
      return null;
    }

    case "input_text": {
      const e = qel(params.selector);
      if (e.__error) return e;
      e.focus();
      const setter =
        Object.getOwnPropertyDescriptor(
          window.HTMLInputElement.prototype,
          "value",
        )?.set ||
        Object.getOwnPropertyDescriptor(
          window.HTMLTextAreaElement.prototype,
          "value",
        )?.set;
      if (setter) setter.call(e, params.text);
      else e.value = params.text;
      e.dispatchEvent(new Event("input", { bubbles: true }));
      e.dispatchEvent(new Event("change", { bubbles: true }));
      return null;
    }

    case "input_content_editable": {
      return new Promise(async (resolve) => {
        const e = document.querySelector(params.selector);
        if (!e) {
          resolve({ __error: `Element not found: ${params.selector}` });
          return;
        }
        e.focus();
        document.execCommand("selectAll", false, null);
        document.execCommand("delete", false, null);
        await sleep(80);
        for (const [i, line] of params.text.split("\n").entries()) {
          if (line) document.execCommand("insertText", false, line);
          if (i < params.text.split("\n").length - 1) {
            document.execCommand("insertParagraph", false, null);
            await sleep(30);
          }
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
      const e = document.querySelector(params.selector);
      if (e) e.scrollIntoView({ behavior: "smooth", block: "center" });
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

    case "dispatch_wheel_event":
      document.documentElement.dispatchEvent(
        new WheelEvent("wheel", {
          deltaY: params.deltaY || 0,
          deltaMode: 0,
          bubbles: true,
          cancelable: true,
        }),
      );
      return null;

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
      const e = document.elementFromPoint(params.x, params.y);
      if (e)
        for (const t of ["mousedown", "mouseup", "click"])
          e.dispatchEvent(
            new MouseEvent(t, {
              clientX: params.x,
              clientY: params.y,
              bubbles: true,
            }),
          );
      return null;
    }

    case "press_key": {
      const active = document.activeElement || document.body;
      const map = {
        Enter: 13,
        ArrowDown: 40,
        Tab: 9,
        Backspace: 8,
        Escape: 27,
      };
      const info = {
        key: params.key,
        code: params.key,
        keyCode: map[params.key] || 0,
        bubbles: true,
      };
      active.dispatchEvent(new KeyboardEvent("keydown", info));
      active.dispatchEvent(new KeyboardEvent("keyup", info));
      return null;
    }

    case "type_text": {
      return new Promise(async (resolve) => {
        const active = document.activeElement || document.body;
        const inCE = active.isContentEditable;
        for (const ch of params.text) {
          if (inCE) document.execCommand("insertText", false, ch);
          else
            for (const t of ["keydown", "keypress", "keyup"])
              active.dispatchEvent(
                new KeyboardEvent(t, { key: ch, bubbles: true }),
              );
          await sleep(params.delayMs || 50);
        }
        resolve(null);
      });
    }

    case "remove_element": {
      const e = document.querySelector(params.selector);
      if (e) e.remove();
      return null;
    }

    case "hover_element": {
      const e = document.querySelector(params.selector);
      if (e) {
        const r = e.getBoundingClientRect(),
          cx = r.left + r.width / 2,
          cy = r.top + r.height / 2;
        e.dispatchEvent(
          new MouseEvent("mouseover", {
            clientX: cx,
            clientY: cy,
            bubbles: true,
          }),
        );
        e.dispatchEvent(
          new MouseEvent("mousemove", {
            clientX: cx,
            clientY: cy,
            bubbles: true,
          }),
        );
      }
      return null;
    }

    case "select_all_text": {
      const e = document.querySelector(params.selector);
      if (e) {
        e.focus();
        if (e.select) e.select();
        else document.execCommand("selectAll");
      }
      return null;
    }

    default:
      return { __error: `Unknown command: ${method}` };
  }
}
