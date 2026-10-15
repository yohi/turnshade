'use strict';

(() => {
  if (window !== window.top || window.__splitTurnShadeV11Loaded) return;
  window.__splitTurnShadeV11Loaded = true;

  const MESSAGE_SELECTOR = '[data-message-author-role="user"]';
  const EDITOR_SELECTOR = '#prompt-textarea, [data-testid="composer-input"], [contenteditable="true"][role="textbox"]';
  const SEND_SELECTOR = [
    'button[data-testid="send-button"]',
    'button[data-testid="composer-submit-button"]',
    'button[data-testid*="send"]',
    'button[aria-label="Send prompt"]',
    'button[aria-label="Send message"]',
    'button[aria-label="送信"]',
    'button[aria-label="プロンプトを送信"]',
    'form button[type="submit"]'
  ].join(',');
  const TIMEOUT_MS = 20000;
  const ROUTE_GUARD_MS = 1800;
  let pageHref = location.href;
  let lastRouteChange = Date.now();
  let current = capture();
  let pending = null;
  let overlayHost = null;
  let shaded = false;
  let scheduled = false;
  let lastEvent = '初期化';
  let lastSentAt = null;
  let lastTransport = '未送信';

  function hashText(s) {
    // Internal fingerprint only: never sent or persisted; no message text leaves the page.
    let hash = 2166136261;
    for (let i = 0; i < s.length; i++) hash = Math.imul(hash ^ s.charCodeAt(i), 16777619);
    return (hash >>> 0).toString(16);
  }
  function capture() {
    const messages = document.querySelectorAll(MESSAGE_SELECTOR);
    const last = messages[messages.length - 1];
    if (!last) return {count:0, signature:'', last:null};
    const id = last.closest('[data-message-id]')?.getAttribute('data-message-id') ||
      last.getAttribute('data-message-id') || '';
    const content = last.textContent || '';
    return {count:messages.length, signature:`${id}|${content.length}|${hashText(content)}`, last};
  }
  function newMessage(before, after, allowReplace) {
    if (!after.count) return false;
    if (after.count > before.count) return true;
    return allowReplace && after.signature !== before.signature &&
      (after.count !== before.count || after.last !== before.last || after.signature !== before.signature);
  }

  function ensureOverlay() {
    if (overlayHost?.isConnected) return;
    overlayHost = document.createElement('div');
    overlayHost.id = 'chatgpt-split-turn-shade-overlay';
    overlayHost.setAttribute('aria-hidden', 'true');
    overlayHost.style.cssText = [
      'position:fixed!important', 'inset:0!important', 'z-index:2147483647!important',
      'pointer-events:none!important', 'display:none',
      'margin:0!important','padding:0!important','border:0!important'
    ].join(';');
    const root = overlayHost.attachShadow({mode:'closed'});
    const veil = document.createElement('div');
    veil.style.cssText = 'position:absolute;inset:0;background:rgba(72,72,72,.32);pointer-events:none';
    const label = document.createElement('div');
    label.textContent = '送信済み  ·  次は反対側';
    label.style.cssText = [
      'position:absolute','top:12px','right:14px','font:600 12px/1.4 system-ui,sans-serif',
      'background:rgba(45,45,45,.80)','color:white','border-radius:8px',
      'padding:5px 10px','pointer-events:none','box-shadow:0 2px 8px rgba(0,0,0,.2)'
    ].join(';');
    root.append(veil,label);
    (document.body || document.documentElement).appendChild(overlayHost);
  }
  function setShade(value) {
    shaded = Boolean(value);
    ensureOverlay();
    overlayHost.style.display = shaded ? 'block' : 'none';
  }

  function clearPending() {
    if (pending?.timer) clearTimeout(pending.timer);
    pending = null;
  }
  function editorLength() {
    const el = document.querySelector(EDITOR_SELECTOR);
    return ((el?.value ?? el?.textContent) || '').trim().length;
  }
  function arm(trigger) {
    if (pending) return;
    lastEvent = trigger;
    pending = {before:capture(), trigger, timer:null, started:Date.now(), editorBefore:editorLength()};
    pending.timer = setTimeout(clearPending, TIMEOUT_MS);
    // Some ChatGPT UI revisions omit the usual user-message selector.
    // A genuine composer clear after an explicit send action is a secondary signal.
    setTimeout(scheduleCheck, 700);
    scheduleCheck();
  }
  function sent(cause) {
    lastEvent = `送信を検出 (${cause})`;
    lastSentAt = Date.now();
    chrome.runtime.sendMessage({type:'STS_SENT', cause}).then(response => {
      if (!response?.ok) lastTransport = response?.error || 'バックグラウンド通信エラー';
      else if (!response.applied) lastTransport = 'ペア未認識';
      else lastTransport = `反映済み (${response.source})`;
    }).catch(error => { lastTransport = String(error); });
  }
  function examine() {
    scheduled = false;
    // Route change (SPA) must not be mistaken for a new outgoing user message.
    if (location.href !== pageHref) {
      pageHref = location.href;
      lastRouteChange = Date.now();
      // When a genuine send changes the route, preserve the pre-send baseline.
      if (!pending) current = capture();
    }
    const next = capture();
    if (pending && newMessage(pending.before, next, true)) {
      const trigger = pending.trigger;
      clearPending();
      current = next;
      sent(trigger);
      return;
    }
    if (pending && pending.editorBefore > 0 && editorLength() === 0 &&
        Date.now() - pending.started >= 650) {
      const trigger = pending.trigger;
      clearPending();
      current = next;
      sent(`${trigger} + 入力欄クリア`);
      return;
    }
    if (!pending && Date.now() - lastRouteChange > ROUTE_GUARD_MS &&
        newMessage(current, next, false)) {
      current = next;
      sent('DOMに新しいユーザーメッセージ');
      return;
    }
    // Preserve baseline on non-send rerenders; avoid updating a baseline during an active send.
    if (!pending) current = next;
  }
  function scheduleCheck() {
    if (scheduled) return;
    scheduled = true;
    setTimeout(examine, 90);
  }

  function isEditor(target) {
    if (!(target instanceof Element)) return false;
    return Boolean(target.closest(EDITOR_SELECTOR) ||
      (target.closest('form')?.querySelector(EDITOR_SELECTOR) &&
        target.matches('textarea, [contenteditable="true"], [role="textbox"]')));
  }
  function editorHasInput(target) {
    const node = target.closest(EDITOR_SELECTOR) || target;
    return Boolean(((node.value ?? node.textContent) || '').trim());
  }
  function looksLikeSend(button) {
    if (!button || button.disabled || button.getAttribute('aria-disabled') === 'true') return false;
    if (button.matches(SEND_SELECTOR)) return true;
    const label = `${button.getAttribute('aria-label') || ''} ${button.getAttribute('title') || ''}`;
    return /^(?:send|submit|送信)/i.test(label.trim()) &&
      Boolean(button.closest('form, [data-testid*="composer"], #thread-bottom-container'));
  }

  document.addEventListener('pointerdown', event => {
    if (event.button !== 0 || !(event.target instanceof Element)) return;
    if (looksLikeSend(event.target.closest('button'))) arm('送信ボタン');
  }, true);
  document.addEventListener('click', event => {
    if (!(event.target instanceof Element)) return;
    if (looksLikeSend(event.target.closest('button'))) arm('送信ボタン');
  }, true);
  document.addEventListener('keydown', event => {
    if (event.key !== 'Enter' || event.shiftKey || event.ctrlKey || event.metaKey ||
        event.altKey || event.isComposing || event.keyCode === 229 ||
        !isEditor(event.target) || !editorHasInput(event.target)) return;
    arm('Enter');
  }, true);
  document.addEventListener('submit', event => {
    if (event.target instanceof HTMLFormElement && event.target.querySelector(EDITOR_SELECTOR))
      arm('フォーム送信');
  }, true);

  // Works even for externally automated sends without DOM click/keyboard events.
  const observer = new MutationObserver(() => {
    if (shaded && overlayHost && !overlayHost.isConnected) ensureOverlay();
    scheduleCheck();
  });
  observer.observe(document.documentElement, {childList:true, subtree:true, characterData:true});
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === 'STS_SET_SHADE') {setShade(message.shaded); return false;}
    if (message?.type === 'STS_DIAGNOSTICS') {
      const s = capture();
      sendResponse({
        loaded:true, shaded, userMessages:s.count,
        editorDetected:Boolean(document.querySelector(EDITOR_SELECTOR)),
        sendButtonDetected:Boolean(document.querySelector(SEND_SELECTOR)),
        lastEvent, lastSentAt, lastTransport, pending:Boolean(pending)
      });
      return false;
    }
    return false;
  });
  // Restore state on reload; report unsupported pair via popup rather than silently failing.
  chrome.runtime.sendMessage({type:'STS_SYNC'}).then(response => {
    if (!response?.ok) {
      lastTransport = '初期同期エラー';
      setShade(false);
    } else if (!response.paired) lastTransport = 'ペア未認識';
  }).catch(error => {lastTransport = String(error); setShade(false);});
})();
