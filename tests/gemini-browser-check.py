"""Gemini synthetic DOM smoke test; no network and no logged-in real Gemini session."""
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
    page = browser.new_page()
    page.set_content('''<!doctype html><html><body>
      <main id="conversation"><user-query><div class="query-text">Older question</div></user-query></main>
      <input-area-v2><rich-textarea><div class="ql-editor textarea" contenteditable="true" role="textbox"></div></rich-textarea>
      <button class="send-button" aria-label="Send message">Send</button></input-area-v2>
      </body></html>''')
    page.evaluate("""() => {
      window.__messages = [];
      window.__listeners = [];
      window.chrome = {
        runtime: {
          onMessage: {addListener: fn => window.__listeners.push(fn)},
          sendMessage: async m => {window.__messages.push(m); return {ok:true,paired:true,applied:true,source:'split'};}
        }
      };
    }""")
    source = (root / 'content.js').read_text(encoding='utf-8')
    assert "location.hostname === 'gemini.google.com'" in source
    # Switch only the test-loaded script to the Gemini provider branch.
    page.add_script_tag(content=source.replace("location.hostname === 'gemini.google.com'", 'true'))
    page.wait_for_timeout(300)
    assert page.evaluate('window.__messages[0].type') == 'STS_SYNC'
    diagnostics = page.evaluate("""() => {
      let status;
      window.__listeners[0]({type:'STS_DIAGNOSTICS'}, {}, x => status=x);
      return status;
    }""")
    assert diagnostics['provider'] == 'gemini' and diagnostics['editorDetected'] and diagnostics['sendButtonDetected'], diagnostics
    page.locator('.ql-editor').fill('Gemini prompt')
    page.locator('.send-button').click()
    page.evaluate("""() => {
      const q=document.createElement('user-query'); q.innerHTML='<div class="query-text">Gemini prompt</div>';
      document.querySelector('#conversation').append(q);
    }""")
    page.wait_for_timeout(300)
    assert page.evaluate('window.__messages.filter(x=>x.type==="STS_SENT").length') == 1
    page.evaluate("""() => window.__listeners[0]({type:'STS_SET_SHADE',shaded:true},{},()=>{})""")
    assert page.locator('#chatgpt-split-turn-shade-overlay').evaluate('(el) => getComputedStyle(el).display') == 'block'
    page.evaluate("""() => window.__listeners[0]({type:'STS_SET_SHADE',shaded:false},{},()=>{})""")
    assert page.locator('#chatgpt-split-turn-shade-overlay').evaluate('(el) => getComputedStyle(el).display') == 'none'
    # Gemini's assistant output must not be counted as an outgoing user turn.
    page.evaluate("""() => {
      const r=document.createElement('model-response');r.textContent='Gemini response';
      document.querySelector('#conversation').append(r);
    }""")
    page.wait_for_timeout(300)
    assert page.evaluate('window.__messages.filter(x=>x.type==="STS_SENT").length') == 1
    page.wait_for_timeout(1900)
    page.evaluate("""() => {
      const q=document.createElement('user-query'); q.textContent='Automated Gemini prompt';
      document.querySelector('#conversation').append(q);
    }""")
    page.wait_for_timeout(300)
    assert page.evaluate('window.__messages.filter(x=>x.type==="STS_SENT").length') == 2
    print('GEMINI_BROWSER_SMOKE_PASS: explicit send, passive DOM, assistant-ignore, overlay toggle')
    browser.close()
