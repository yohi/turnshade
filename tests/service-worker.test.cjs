'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const WORKER = fs.readFileSync(path.join(__dirname, '..', 'service-worker.js'), 'utf8');

function mock() {
  const tabs = new Map([
    [1,{id:1,windowId:10,splitViewId:42,url:'https://chatgpt.com/c/a'}],
    [2,{id:2,windowId:10,splitViewId:42,url:'https://gemini.google.com/app/c/b'}],
    [3,{id:3,windowId:10,splitViewId:43,url:'https://gemini.google.com/app/c/c'}],
    [4,{id:4,windowId:10,splitViewId:43,url:'https://gemini.google.com/app/c/d'}],
    [5,{id:5,windowId:11,splitViewId:-1,url:'https://chatgpt.com/c/e'}],
    [6,{id:6,windowId:11,splitViewId:-1,url:'https://gemini.google.com/app/c/f'}],
    [7,{id:7,windowId:12,splitViewId:-1,url:'https://chatgpt.com/'}],
    [8,{id:8,windowId:12,splitViewId:-1,url:'https://example.org'}]
  ]);
  const messages=[]; const handlers={}; const session={}; const local={};
  const event = name => ({addListener(fn){handlers[name]=fn;}});
  const chrome = {
    tabs: {
      SPLIT_VIEW_ID_NONE:-1,
      async get(id) {if (!tabs.has(id)) throw Error('not found');return {...tabs.get(id)};},
      async query(q) {return [...tabs.values()].filter(t=>q.windowId===undefined || q.windowId===t.windowId).map(t=>({...t}));},
      async sendMessage(id,message){messages.push({id,...message});return message.type==='STS_DIAGNOSTICS'?{loaded:true,shaded:false}:undefined;},
      onUpdated:event('updated'),onRemoved:event('removed'),onDetached:event('detached')
    },
    storage: {
      session:{async get(k){return {[k]:structuredClone(session[k])};},async set(o){Object.assign(session,structuredClone(o));}},
      local:{async get(k){return {[k]:structuredClone(local[k])};},async set(o){Object.assign(local,structuredClone(o));}}
    },
    runtime:{id:'unit-test-extension',onMessage:event('message')}
  };
  vm.runInNewContext(WORKER,{chrome,console,URL,Date,Promise,Number,Object,Boolean,Map,Set}, {filename:'service-worker.js'});
  function msg(type, tabId, opts={}) {
    return new Promise(resolve=>{
      const sender = opts.popup ? {id:chrome.runtime.id} : {tab:tabs.get(tabId)};
      const value = {type, ...(opts.popup?{tabId}:{}), ...(opts.value!==undefined?{value:opts.value}:{})};
      const asynchronous=handlers.message(value,sender,resolve);
      if (!asynchronous) resolve({unhandled:true});
    });
  }
  return {tabs, messages, handlers, session, local, msg};
}
function lastShade(m,id){return m.messages.filter(x=>x.id===id && x.type==='STS_SET_SHADE').at(-1)?.shaded;}

test('native Split: left/right send toggles both sides',async()=>{
  const m=mock();
  assert.equal((await m.msg('STS_SYNC',1)).paired,true);
  assert.equal((await m.msg('STS_SENT',1)).applied,true);
  assert.equal(lastShade(m,1),true);assert.equal(lastShade(m,2),false);
  assert.equal((await m.msg('STS_SENT',2)).applied,true);
  assert.equal(lastShade(m,1),false);assert.equal(lastShade(m,2),true);
});
test('different splits and different windows do not share shade',async()=>{
  const m=mock(); await m.msg('STS_SENT',1);
  assert.equal(m.messages.some(x=>[3,4,5,6].includes(x.id)),false);
  assert.equal((await m.msg('STS_SENT',7)).applied,false);
});
test('session restores state after page reload',async()=>{
  const m=mock(); await m.msg('STS_SENT',2);
  m.messages.length=0;
  assert.equal((await m.msg('STS_SYNC',2)).shaded,true);
  assert.equal(lastShade(m,2),true);
});
test('unsplitting clears overlays',async()=>{
  const m=mock(); await m.msg('STS_SENT',1);
  m.tabs.get(1).splitViewId=-1;m.tabs.get(2).splitViewId=-1;
  m.handlers.updated(1,{splitViewId:-1});
  await m.msg('STS_SYNC',1);
  assert.equal(lastShade(m,1),false);assert.equal(lastShade(m,2),false);
  assert.equal(Object.keys(m.session.splitTurnShadeStatesV2).length,0);
});
test('two-tab fallback is opt-in and only applies to exactly two ChatGPT tabs',async()=>{
  const m=mock();
  assert.equal((await m.msg('STS_SENT',5)).applied,false);
  await m.msg('STS_SET_FALLBACK',undefined,{popup:true,value:true});
  assert.equal((await m.msg('STS_SENT',5)).applied,true);
  assert.equal(lastShade(m,5),true);assert.equal(lastShade(m,6),false);
  assert.equal((await m.msg('STS_SENT',7)).applied,false);
  await m.msg('STS_SET_FALLBACK',undefined,{popup:true,value:false});
  assert.equal(lastShade(m,5),false);assert.equal(lastShade(m,6),false);
});
test('popup status/manual shade/reset with per-page diagnostics',async()=>{
  const m=mock();
  let status=await m.msg('STS_GET_STATUS',1,{popup:true});
  assert.equal(status.paired,true);
  assert.equal(status.page.loaded,true);
  assert.equal((await m.msg('STS_MANUAL_SHADE',1,{popup:true})).applied,true);
  status=await m.msg('STS_GET_STATUS',1,{popup:true});
  assert.equal(status.shadeTabId,1);
  assert.equal((await m.msg('STS_RESET',1,{popup:true})).cleared,true);
  assert.equal(lastShade(m,1),false);
});
test('navigation away clears pair and overlay',async()=>{
  const m=mock();await m.msg('STS_SENT',1);
  m.tabs.get(2).url='https://example.org/';
  m.handlers.updated(2,{url:'https://example.org/'});
  await m.msg('STS_SYNC',1);
  assert.equal(lastShade(m,1),false);
  assert.equal(Object.keys(m.session.splitTurnShadeStatesV2).length,0);
});
test('concurrent sends maintain last received event state',async()=>{
  const m=mock();await Promise.all([m.msg('STS_SENT',1),m.msg('STS_SENT',2)]);
  assert.equal(lastShade(m,1),false); assert.equal(lastShade(m,2),true);
});

test('mixed ChatGPT x Gemini pair is bidirectional, reports provider metadata',async()=>{
  const m=mock();
  let status=await m.msg('STS_GET_STATUS',1,{popup:true});
  assert.equal(status.provider,'chatgpt');assert.equal(status.partnerProvider,'gemini');
  assert.equal((await m.msg('STS_SENT',1)).applied,true);
  assert.equal(lastShade(m,1),true);assert.equal(lastShade(m,2),false);
  assert.equal((await m.msg('STS_SENT',2)).applied,true);
  assert.equal(lastShade(m,1),false);assert.equal(lastShade(m,2),true);
  status=await m.msg('STS_GET_STATUS',2,{popup:true});
  assert.equal(status.provider,'gemini');assert.equal(status.partnerProvider,'chatgpt');
});
test('native Split Gemini x Gemini remains isolated from other pairs',async()=>{
  const m=mock();
  assert.equal((await m.msg('STS_SENT',3)).applied,true);
  assert.equal(lastShade(m,3),true);assert.equal(lastShade(m,4),false);
  assert.equal(m.messages.some(x=>[1,2].includes(x.id)),false);
  assert.equal((await m.msg('STS_SENT',4)).applied,true);
  assert.equal(lastShade(m,3),false);assert.equal(lastShade(m,4),true);
});
test('fallback supports mixed providers and excludes unsupported domains',async()=>{
  const m=mock();
  await m.msg('STS_SET_FALLBACK',undefined,{popup:true,value:true});
  assert.equal((await m.msg('STS_SENT',6)).applied,true);
  assert.equal(lastShade(m,6),true);assert.equal(lastShade(m,5),false);
  m.tabs.get(5).url='https://gemini.google.com.attacker.invalid/app';
  m.handlers.updated(5,{url:m.tabs.get(5).url});
  assert.equal((await m.msg('STS_SENT',6)).applied,false);
  assert.equal((await m.msg('STS_GET_STATUS',5,{popup:true})).validTab,false);
});
test('other windows and non-HTTPS Gemini-lookalikes are rejected',async()=>{
  const m=mock();
  m.tabs.get(7).url='http://gemini.google.com/app';
  assert.equal((await m.msg('STS_SENT',7)).unhandled,true);
  assert.equal((await m.msg('STS_GET_STATUS',7,{popup:true})).provider,null);
});
