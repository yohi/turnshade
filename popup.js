'use strict';
let selectedTabId = null;
const $ = id => document.getElementById(id);
function timestamp(t) {return t ? new Date(t).toLocaleTimeString('ja-JP') : '未検出';}
async function currentTabId() {
  const tabs = await chrome.tabs.query({active:true, currentWindow:true});
  return tabs[0]?.id ?? null;
}
function message(data) {
  return chrome.runtime.sendMessage(data);
}
async function refresh() {
  try {
    selectedTabId = await currentTabId();
    if (selectedTabId == null) { $('status').textContent = 'アクティブなタブを確認できません。';return; }
    const r = await message({type:'STS_GET_STATUS',tabId:selectedTabId});
    if (!r.ok) throw Error(r.error || '状態取得に失敗');
    $('fallback').checked = r.twoTabFallback;
    $('reverse').checked = r.reverseArrows;
    if (!r.validTab) {
      $('status').textContent = 'このタブは対象外です。ChatGPTまたはGeminiの画面を選んでください。';
      return;
    }
    const pair = r.paired ? `認識済み (${r.source === 'split' ? 'Chrome標準Split View' : '通常タブ2枚'})` : '未認識';
    const doc = r.page ? '読み込み済み' : '応答なし（拡張の再読み込み後にChatGPTも再読み込みしてください）';
    const detail = r.page || {};
    $('status').textContent = [
      `ペア: ${pair}`,
      `プロバイダー: ${r.provider ?? '不明'} / 相手: ${r.partnerProvider ?? '不明'}`,
      `Chrome Split ID: ${r.chromeSplitId ?? 'なし'}`,
      `相手タブ: ${r.partnerTabId ?? '未特定'}`,
      `拡張のページ監視: ${doc}`,
      `送信ボタン: ${detail.sendButtonDetected ? '検出' : '未検出'} / 入力欄: ${detail.editorDetected ? '検出' : '未検出'}`,
      `ユーザーメッセージ: ${detail.userMessages ?? '?'}件`,
      `直近の検出: ${detail.lastEvent ?? 'なし'}`,
      `反映結果: ${detail.lastTransport ?? '不明'}`,
      `最後の送信: ${timestamp(detail.lastSentAt)}`,
      `赤枠表示: ${detail.shaded ? 'ON' : 'OFF'}`,
      `矢印の向き: ${detail.shaded ? (detail.arrowDirection === 'right' ? '→' : detail.arrowDirection === 'left' ? '←' : '判定不可') : '非表示'}`, 
    ].join('\n');
  } catch (e) { $('status').textContent = `エラー: ${String(e)}`; }
}
async function run(action) {
  $('feedback').textContent = '';
  try {
    if (selectedTabId === null) await refresh();
    const result = await message({type:action,tabId:selectedTabId});
    if (!result?.ok) throw Error(result?.error || '操作失敗');
    if (action === 'STS_MANUAL_SHADE' && !result.applied) {
      $('feedback').textContent = 'ペア未認識。Chrome標準のSplit Viewか、通常タブ2枚モードを確認してください。';
    }
    await refresh();
  } catch(e) { $('feedback').textContent = String(e); }
}
$('test').addEventListener('click',()=>run('STS_MANUAL_SHADE'));
$('reset').addEventListener('click',()=>run('STS_RESET'));
$('refresh').addEventListener('click',refresh);
$('reverse').addEventListener('change', async event => {
  $('feedback').textContent = '';
  try {
    const r = await message({type:'STS_SET_REVERSE_ARROWS',value:event.target.checked});
    if (!r?.ok) throw Error(r?.error || '左右の反転設定を保存できません');
    await refresh();
  } catch (e) { $('feedback').textContent = String(e); }
});
$('fallback').addEventListener('change',async event=>{
  $('feedback').textContent = '';
  try {
    const r = await message({type:'STS_SET_FALLBACK',value:event.target.checked});
    if (!r?.ok) throw Error(r?.error || '設定を保存できません');
    await refresh();
  }catch(e){$('feedback').textContent=String(e);}
});
void refresh();
