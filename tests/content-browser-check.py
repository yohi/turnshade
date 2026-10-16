"""A browser DOM smoke test, not a real ChatGPT end-to-end test."""
from pathlib import Path
from playwright.sync_api import sync_playwright
p = Path(__file__).resolve().parents[1]
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
    page = browser.new_page()
    page.set_content('''<!doctype html><html><body>
      <main><section data-message-author-role="user" data-message-id="m0">Earlier question</section></main>
      <form id="composer"><div id="prompt-textarea" contenteditable="true" role="textbox"></div>
      <button type="submit" data-testid="composer-submit-button">Send</button></form>
      </body></html>''')
    page.evaluate('''() => {
       window.__messages = [];
       window.__listeners = [];
       window.chrome = {
         runtime: {
           onMessage: {addListener: (fn) => window.__listeners.push(fn)},
           sendMessage: async (m) => { window.__messages.push(m);return {ok:true,paired:true,applied:true,source:'split'}; }
         }
       };
       document.querySelector('form').addEventListener('submit', e => e.preventDefault());
    }''')
    # Expose the closed shadow root only in this test to verify the actual visual cue.
    page.evaluate("""() => {
      const original = Element.prototype.attachShadow;
      Element.prototype.attachShadow = function(init) {
        return original.call(this, {...init, mode:'open'});
      };
    }""")
    page.add_script_tag(path=str(p / 'content.js'))
    page.wait_for_timeout(300)
    assert page.evaluate('window.__messages[0].type') == 'STS_SYNC'
    page.locator('#prompt-textarea').fill('New message')
    page.locator('button').click()
    page.evaluate('''() => {
      const s = document.createElement('section');s.dataset.messageAuthorRole = 'user';
      s.dataset.messageId = 'm1';s.textContent='New message';
      document.querySelector('main').append(s);
    }''')
    page.wait_for_timeout(300)
    assert page.evaluate('window.__messages.filter(x=>x.type === "STS_SENT").length') == 1
    assert page.evaluate('window.__messages.at(-1).cause') in ('送信ボタン', 'フォーム送信')
    page.evaluate('''() => window.__listeners[0]({type:'STS_SET_SHADE',shaded:true,direction:'right'}, {}, ()=>{})''')
    overlay = page.locator('#chatgpt-split-turn-shade-overlay')
    assert overlay.evaluate('(el)=>getComputedStyle(el).display') == 'block'
    assert overlay.evaluate('(el)=>getComputedStyle(el).pointerEvents') == 'none'
    assert overlay.evaluate("(el)=>el.shadowRoot.querySelector('div').style.boxShadow.includes('#dc2626')")
    assert overlay.evaluate("(el)=>el.shadowRoot.querySelectorAll('div')[1].textContent") == '次は右へ →'
    page.evaluate('''() => window.__listeners[0]({type:'STS_SET_SHADE',shaded:true,direction:'left'}, {}, ()=>{})''')
    assert overlay.evaluate("(el)=>el.shadowRoot.querySelectorAll('div')[1].textContent") == '← 次は左へ'
    page.evaluate('''() => window.__listeners[0]({type:'STS_SET_SHADE',shaded:false}, {}, ()=>{})''')
    assert page.locator('#chatgpt-split-turn-shade-overlay').evaluate('(el)=>getComputedStyle(el).display') == 'none'
    # Programmatic insertion should still count, even when not caused by DOM events.
    page.wait_for_timeout(1900)
    page.evaluate('''() => {
      const s = document.createElement('section');s.dataset.messageAuthorRole='user';
      s.dataset.messageId='m2';s.textContent='Automated turn';document.querySelector('main').append(s);
    }''')
    page.wait_for_timeout(250)
    assert page.evaluate('window.__messages.filter(x=>x.type === "STS_SENT").length') == 2
    assert page.evaluate('window.__messages.at(-1).cause') == 'DOMに新しいユーザーメッセージ'
    # Selector-independent fallback: composer clears after an actual submit action.
    page.locator('#prompt-textarea').fill('Fallback message')
    page.locator('button').click()
    page.evaluate("document.querySelector('#prompt-textarea').textContent=''")
    page.wait_for_timeout(850)
    assert page.evaluate('window.__messages.filter(x=>x.type === \"STS_SENT\").length') == 3
    print('BROWSER_SMOKE_PASS: click -> user message, red border + both arrows, passive DOM, editor-clear fallback')
    browser.close()
