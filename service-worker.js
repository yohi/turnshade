'use strict';

// Only metadata is stored. No ChatGPT message contents, cookies or tokens.
const STATES_KEY = 'splitTurnShadeStatesV2';
const OPTIONS_KEY = 'splitTurnShadeOptionsV2';
const SPLIT_NONE = chrome.tabs.SPLIT_VIEW_ID_NONE ?? -1;
let queue = Promise.resolve();
let lastError = '';

function enqueue(work) {
  const result = queue.then(work);
  queue = result.catch(error => {
    lastError = String(error);
    console.warn('[Split Turn Shade]', error);
  });
  return result;
}

function isChatGptUrl(url) {
  try {
    const u = new URL(url);
    return u.protocol === 'https:' && (u.hostname === 'chatgpt.com' || u.hostname === 'chat.openai.com');
  } catch { return false; }
}
function isSplitId(id) { return Number.isInteger(id) && id !== SPLIT_NONE; }
function isSamePair(a, b) {
  return Boolean(a && b && a.tabIds?.length === 2 && b.tabIds?.length === 2 &&
    a.tabIds[0] === b.tabIds[0] && a.tabIds[1] === b.tabIds[1]);
}
async function readStates() { return (await chrome.storage.session.get(STATES_KEY))[STATES_KEY] ?? {}; }
async function saveStates(states) { await chrome.storage.session.set({[STATES_KEY]: states}); }
async function readOptions() { return (await chrome.storage.local.get(OPTIONS_KEY))[OPTIONS_KEY] ?? {}; }

// Native Chrome Split View is preferred; manual fallback requires user opt-in.
async function getPair(tabId) {
  const tab = await chrome.tabs.get(tabId).catch(() => null);
  if (!tab || !isChatGptUrl(tab.url)) return null;
  const nearby = await chrome.tabs.query({ windowId: tab.windowId });
  if (isSplitId(tab.splitViewId)) {
    const members = nearby.filter(t => t.splitViewId === tab.splitViewId);
    if (members.length === 2 && members.every(t => isChatGptUrl(t.url))) {
      return {
        key: `split:${tab.windowId}:${tab.splitViewId}`,
        source: 'split', windowId: tab.windowId, splitViewId: tab.splitViewId,
        tabIds: members.map(t => t.id).sort((a,b) => a-b)
      };
    }
  }
  const options = await readOptions();
  if (options.twoTabFallback) {
    const members = nearby.filter(t => isChatGptUrl(t.url) && !isSplitId(t.splitViewId));
    if (members.length === 2 && members.some(t => t.id === tabId)) {
      return {
        key: `fallback:${tab.windowId}`, source: 'fallback', windowId: tab.windowId,
        splitViewId: SPLIT_NONE, tabIds: members.map(t => t.id).sort((a,b) => a-b)
      };
    }
  }
  return null;
}

async function sendStyle(tabId, shaded) {
  try {
    await chrome.tabs.sendMessage(tabId, {type:'STS_SET_SHADE', shaded});
    return true;
  } catch {
    // A tab may still be navigating, or may need reload following installation.
    return false;
  }
}

async function onSent(tabId, cause = 'dom') {
  const pair = await getPair(tabId);
  if (!pair) return {applied:false, reason:'no-recognized-pair'};
  const states = await readStates();
  states[pair.key] = {...pair, shadedTabId:tabId, cause, updatedAt:Date.now()};
  await saveStates(states);
  const results = await Promise.all(pair.tabIds.map(id => sendStyle(id, id === tabId)));
  return {applied:true, delivered:results, source:pair.source};
}

async function onSync(tabId) {
  const pair = await getPair(tabId);
  if (!pair) {
    await sendStyle(tabId, false);
    return {paired:false, shaded:false, reason:'no-recognized-pair'};
  }
  const states = await readStates();
  const record = states[pair.key];
  const shaded = Boolean(isSamePair(pair, record) && record.shadedTabId === tabId);
  await sendStyle(tabId, shaded);
  return {paired:true, shaded, source:pair.source};
}

async function resetPair(tabId) {
  const pair = await getPair(tabId);
  if (!pair) {await sendStyle(tabId, false); return {cleared:true, paired:false};}
  const states = await readStates();
  delete states[pair.key];
  await saveStates(states);
  await Promise.all(pair.tabIds.map(id => sendStyle(id, false)));
  return {cleared:true, paired:true};
}

async function getStatus(tabId) {
  const tab = await chrome.tabs.get(tabId).catch(() => null);
  const pair = await getPair(tabId);
  const states = await readStates();
  const options = await readOptions();
  const record = pair && states[pair.key];
  let page = null;
  if (tab && isChatGptUrl(tab.url)) {
    page = await chrome.tabs.sendMessage(tabId, {type:'STS_DIAGNOSTICS'}).catch(() => null);
  }
  return {
    validTab: Boolean(tab && isChatGptUrl(tab.url)),
    tabId,
    chromeSplitId: tab?.splitViewId ?? null,
    paired: Boolean(pair),
    source: pair?.source ?? null,
    partnerTabId: pair?.tabIds.find(id => id !== tabId) ?? null,
    shadeTabId: isSamePair(pair, record) ? record.shadedTabId : null,
    updatedAt: record?.updatedAt ?? null,
    page,
    twoTabFallback: Boolean(options.twoTabFallback),
    lastError
  };
}

async function setFallback(value) {
  await chrome.storage.local.set({[OPTIONS_KEY]:{twoTabFallback:Boolean(value)}});
  const states = await readStates();
  for (const [key, record] of Object.entries(states)) {
    if (record.source === 'fallback') {
      delete states[key];
      for (const id of record.tabIds ?? []) await sendStyle(id, false);
    }
  }
  await saveStates(states);
  return {saved:true};
}

async function pruneInvalidPairs() {
  const states = await readStates();
  if (Object.keys(states).length === 0) return;
  const allTabs = await chrome.tabs.query({});
  const byId = new Map(allTabs.map(t => [t.id,t]));
  const options = await readOptions();
  let modified = false;
  const clear = new Set();
  for (const [key, record] of Object.entries(states)) {
    const [a,b] = (record.tabIds ?? []).map(id => byId.get(id));
    const core = a && b && a.id !== b.id && a.windowId === b.windowId &&
      a.windowId === record.windowId && isChatGptUrl(a.url) && isChatGptUrl(b.url);
    const valid = Boolean(core && (record.source === 'split'
      ? isSplitId(a.splitViewId) && a.splitViewId === b.splitViewId &&
        key === `split:${a.windowId}:${a.splitViewId}`
      : options.twoTabFallback && !isSplitId(a.splitViewId) && !isSplitId(b.splitViewId) &&
        allTabs.filter(t=>t.windowId === a.windowId && isChatGptUrl(t.url) && !isSplitId(t.splitViewId)).length === 2 &&
        key === `fallback:${a.windowId}`));
    if (!valid) {
      delete states[key]; modified = true;
      for (const id of record.tabIds ?? []) clear.add(id);
    }
  }
  if (modified) await saveStates(states);
  await Promise.all([...clear].map(id=>sendStyle(id,false)));
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || typeof message.type !== 'string') return false;
  const isPage = Boolean(sender.tab?.id && isChatGptUrl(sender.tab?.url));
  const isExtension = sender.id === chrome.runtime.id && !sender.tab;
  let action;
  if (isPage && message.type === 'STS_SYNC') action = () => onSync(sender.tab.id);
  else if (isPage && message.type === 'STS_SENT') action = () => onSent(sender.tab.id, message.cause);
  else if (isExtension && Number.isInteger(message.tabId)) {
    if (message.type === 'STS_GET_STATUS') action = () => getStatus(message.tabId);
    if (message.type === 'STS_MANUAL_SHADE') action = () => onSent(message.tabId, 'manual');
    if (message.type === 'STS_RESET') action = () => resetPair(message.tabId);
  }
  if (isExtension && message.type === 'STS_SET_FALLBACK') action = () => setFallback(message.value);
  if (!action) return false;
  enqueue(action).then(
    result => sendResponse({ok:true, ...result}),
    error => sendResponse({ok:false, error:String(error)})
  );
  return true;
});
chrome.tabs.onUpdated.addListener((_tabId, info) => {
  if (Object.hasOwn(info, 'splitViewId') || Object.hasOwn(info, 'url'))
    void enqueue(pruneInvalidPairs);
});
chrome.tabs.onRemoved.addListener(() => {void enqueue(pruneInvalidPairs);});
chrome.tabs.onDetached.addListener(() => {void enqueue(pruneInvalidPairs);});
