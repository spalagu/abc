'use strict';
const $ = id => document.getElementById(id);
function randomID(){const b=new Uint8Array(16);crypto.getRandomValues(b);return [...b].map(x=>x.toString(16).padStart(2,'0')).join('');}
let token='',client='',revision='',semanticRevision='',busy=false,timer=null,lastStatus={},stats={rx:0,tx:0,frames:0,actions:0,errors:[]};
try{token=sessionStorage.getItem('wc-token')||'';client=sessionStorage.getItem('wc-client')||randomID();sessionStorage.setItem('wc-client',client);}catch{client=randomID();}
const fragment=new URLSearchParams(location.hash.slice(1));
if(fragment.has('token')){token=fragment.get('token');history.replaceState(null,'',location.pathname);try{sessionStorage.setItem('wc-token',token);}catch{}}
let feedbackTimer;
function note(text,error=false){
 $('notice').textContent=text;$('notice').classList.toggle('error',error);
 const local=$('inputStatus');local.textContent=text;local.classList.toggle('error',error);
 const feedback=$('feedback');feedback.textContent=text;feedback.classList.toggle('error',error);feedback.hidden=false;
 clearTimeout(feedbackTimer);feedbackTimer=setTimeout(()=>feedback.hidden=true,error?12000:7000);
}
function bytes(n){return n<1024?`${n} B`:`${(n/1024).toFixed(2)} KiB`;}
async function api(path,data={}){
 const body=JSON.stringify(data);stats.tx+=new TextEncoder().encode(body).length;
 const abort=new AbortController(),timeout=setTimeout(()=>abort.abort(),18000);
 try{const r=await fetch('/api/'+path,{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+token,'X-WC-Client':client},body,signal:abort.signal,credentials:'omit',cache:'no-store'});const raw=await r.arrayBuffer();stats.rx+=raw.byteLength;
 if(!r.ok){const e=JSON.parse(new TextDecoder().decode(raw));throw Object.assign(new Error(e.message),{code:e.error});}
 return r.headers.get('content-type').includes('tiles')?raw:JSON.parse(new TextDecoder().decode(raw));
 }catch(e){if(e.name==='AbortError')throw Object.assign(new Error('请求超时，操作结果可能未知；先核对原窗口，不自动重试。'),{code:'timeout'});throw e;}finally{clearTimeout(timeout);}
}
async function run(fn){
 if(busy){note('上一请求尚未结束；本次操作未发送，也不会排队稍后执行。',true);return;}
 busy=true;
 const controls=[...document.querySelectorAll('button, #window, #width, #quality, #roi, #inputRoute, #pointerButton')];
 const disabled=controls.map(el=>el.disabled);controls.forEach(el=>el.disabled=true);
 try{await fn();}catch(e){
  note(e.message,true);stats.errors.push({time:new Date().toISOString(),code:e.code||e.name});stats.errors=stats.errors.slice(-30);stopAuto();
  if(e.code==='auth'||e.code==='expired'){$('pair').hidden=false;$('linkState').textContent='需重新连接';}
 }finally{busy=false;controls.forEach((el,i)=>{if(el.isConnected)el.disabled=disabled[i];});}
}
function resetView(){revision='';semanticRevision='';$('canvas').style.display='none';$('empty').hidden=false;$('nodes').replaceChildren();$('clickMode').checked=false;$('inputRoute').value='background';$('pointerButton').value='left';stopAuto();}
async function status(){lastStatus=await api('status');const s=lastStatus;const p=s.permissions;$('permissions').textContent=`辅助功能：${p.accessibility?'已授权':'未授权'} · 屏幕录制：${p.screen_recording?'已授权':'未授权'}${p.fixture?' · ⚠ 合成测试环境，不是真实 Mac':''}`;$('target').textContent=s.window?`${s.window.app} / ${s.window.title||'无标题'} · 窗口 ${s.window.id}`:'尚未选择';$('version').textContent=`WORK CONTINUITY · ${s.version}`;$('linkState').textContent=s.control?'已连接 · 有控制权':'已连接 · 只读';$('budget').textContent=`画面预算：${bytes(s.budget.used)} / ${bytes(s.budget.limit)} · 被阻止 ${s.budget.blocked} 次`;$('progress').max=s.budget.limit;$('progress').value=s.budget.used;$('traffic').textContent=`Host 累计正文：接收 ${bytes(s.traffic.rx_body)} / 发送 ${bytes(s.traffic.tx_body)}。当前页面 API：接收 ${bytes(stats.rx)} / 发送 ${bytes(stats.tx)}（不含初始页面和请求头）。`;}
async function windows(){const r=await api('windows');const select=$('window');select.replaceChildren(new Option('选择 Mac 上已经打开的窗口',''));for(const w of r.windows)select.add(new Option(`${w.app} · ${w.title||'无标题'} [${w.id}]`,w.id));if(lastStatus.window)select.value=String(lastStatus.window.id);}
async function connect(){await status();$('pair').hidden=true;await windows();note(location.protocol==='https:'?'已连接。默认手动更新；先选窗口，再读取文字或画面。':'当前是 HTTP。仅用于本机、可信 Wi-Fi 或已加密私网；不要把此端口暴露到公网。');}
async function frame(){const raw=await api('frame',{base:revision,width:Number($('width').value),quality:Number($('quality').value),roi:$('roi').value.split(',').map(Number)});const view=new DataView(raw);if(raw.byteLength<4)throw new Error('无效画面包');const len=view.getUint32(0);if(len>raw.byteLength-4)throw new Error('无效画面头');const h=JSON.parse(new TextDecoder().decode(raw.slice(4,4+len)));if(!h.full&&h.base!==revision){revision='';throw new Error('画面基线不一致，请重新刷新');}const canvas=$('canvas');if(h.full){canvas.width=h.width;canvas.height=h.height;}const ctx=canvas.getContext('2d');let offset=4+len;try{for(const tile of h.tiles){if(offset+tile.bytes>raw.byteLength)throw new Error('画面块不完整');const blob=new Blob([raw.slice(offset,offset+tile.bytes)],{type:'image/jpeg'});offset+=tile.bytes;const url=URL.createObjectURL(blob);try{const image=new Image();image.src=url;await image.decode();ctx.drawImage(image,tile.x,tile.y);}finally{URL.revokeObjectURL(url);}}if(offset!==raw.byteLength)throw new Error('多余画面数据');revision=h.revision;}catch(e){revision='';throw e;}canvas.style.display='block';$('empty').hidden=true;$('frameInfo').textContent=`${h.full?'完整基线':'局部增量'} · ${h.tiles.length} 块 · 本次 ${bytes(raw.byteLength)} · ${new Date().toLocaleTimeString()}`;stats.frames++;await status();}
async function action(data){
 const result=await api('action',{...data,request_id:randomID()});stats.actions++;
 stats.lastDelivery={route:result.route||data.mode||data.action,delivery:result.delivery||'api_returned',foreground_changed:result.foreground_changed||false};
 note(result.message||'接口已返回；请核对原窗口，没有自动重试。',result.delivery==='submitted_unconfirmed');return result;
}
async function visual(data,scene=revision){
 if(!scene)throw Object.assign(new Error('尚无有效画面，请先刷新；没有发送输入。'),{code:'no_frame'});
 await action({mode:'visual',input_route:$('inputRoute').value,revision:scene,...data});
 try{await frame();}catch(e){throw Object.assign(new Error('动作请求已返回，但后续画面刷新失败：'+e.message+' 请先核对，不要直接重复操作。'),{code:e.code||'refresh_after_action'});}
}
async function semantics(){const result=await api('semantics');semanticRevision=result.revision;const wrap=$('nodes');wrap.replaceChildren();$('warnings').textContent=result.warnings.join(' ');for(const node of result.nodes){const row=document.createElement('div');row.className='node';const role=document.createElement('div');role.className='role';role.textContent=node.role;row.append(role);const label=document.createElement('strong');label.textContent=node.label;row.append(label);if(node.editable){const input=document.createElement('textarea');input.value=node.value;input.disabled=!node.enabled;const save=document.createElement('button');save.textContent='写入原控件（替换全文，不提交）';save.disabled=!node.enabled;save.onclick=()=>run(async()=>{await action({mode:'semantic',action:'set',node:node.id,revision:semanticRevision,text:input.value});revision='';await semantics();});row.append(input,save);}else if(node.value){const val=document.createElement('pre');val.textContent=node.value;row.append(val);}if(node.pressable){const button=document.createElement('button');button.textContent='操作此控件';button.disabled=!node.enabled;button.onclick=()=>run(async()=>{if(!confirm(`在 Mac 真实操作：${node.label||node.role}？`))return;await action({mode:'semantic',action:'press',node:node.id,revision:semanticRevision});revision='';await semantics();});row.append(button);}wrap.append(row);}filterNodes();await status();}
function filterNodes(){const q=$('filter').value.toLowerCase();for(const row of $('nodes').children)row.hidden=!row.textContent.toLowerCase().includes(q)&&![...row.querySelectorAll('textarea')].some(x=>x.value.toLowerCase().includes(q));}
function stopAuto(){clearTimeout(timer);timer=null;$('auto').checked=false;}
function schedule(){clearTimeout(timer);if($('auto').checked&&!document.hidden)timer=setTimeout(async()=>{if(!busy)await run(frame);if($('auto').checked)schedule();},3000);}
$('connect').onclick=()=>run(async()=>{token=$('token').value.trim()||token;try{sessionStorage.setItem('wc-token',token);}catch{}$('token').value='';await connect();});
$('windows').onclick=()=>run(windows);$('status').onclick=()=>run(status);$('semantics').onclick=()=>run(semantics);$('frame').onclick=()=>run(frame);
$('window').onchange=()=>run(async()=>{resetView();if(!$('window').value)return;await api('select',{window:Number($('window').value)});await status();note('已选择真实窗口。切换呈现方式不会启动第二份应用。');});
$('claim').onclick=()=>run(async()=>{await api('claim');await status();note('已取得控制权。文字写入、点击和快捷键会作用于你的 Mac。');});$('release').onclick=()=>run(async()=>{await api('release');await status();});
$('activate').onclick=()=>run(async()=>{if(!confirm('这会主动把目标窗口切到 Mac 前台。后台操作不需要点这个按钮，是否继续？'))return;await action({action:'activate'});revision='';await frame();});$('filter').oninput=filterNodes;
// Capture the displayed scene at pointer-down. Never apply a queued click to a new scene.
let pointerScene=null;
$('canvas').addEventListener('pointerdown',e=>{pointerScene={id:e.pointerId,revision};});
$('canvas').addEventListener('pointercancel',()=>{pointerScene=null;});
function canvasInput(e,button){
 if(!$('clickMode').checked){note('画面当前只读：先勾选“允许点画面操作”。未发送输入。');return;}
 if(busy){note('正在处理上一请求，本次画面操作未发送。完成后再点；不会排队盲点。',true);return;}
 const r=$('canvas').getBoundingClientRect();
 const x=(e.clientX-r.left)/r.width,y=(e.clientY-r.top)/r.height;
 if(!Number.isFinite(x)||!Number.isFinite(y)||x<0||y<0||x>1||y>1)return;
 const scene=pointerScene?.revision||revision;pointerScene=null;
 note(`${button==='right'?'右键':'左键'}请求发送中…`);
 run(()=>visual({action:'click',button,x,y},scene));
}
$('canvas').onclick=e=>{
 // macOS Ctrl+click is delivered by contextmenu; do not send a second left click.
 if(e.button!==0||e.ctrlKey)return;
 canvasInput(e,$('pointerButton').value);
};
$('canvas').oncontextmenu=e=>{
 if(!$('clickMode').checked)return; // Reading mode keeps the browser's own menu.
 e.preventDefault();e.stopPropagation();
 canvasInput(e,'right');
};
$('canvas').onauxclick=e=>{if($('clickMode').checked)e.preventDefault();};
$('inputRoute').onchange=()=>{
 if($('inputRoute').value==='direct'&&!confirm('实验模式只向目标进程投递，不主动置前；macOS 不返回应用执行回执，部分应用会忽略事件或自行改变焦点。仅用于无风险测试，继续？'))$('inputRoute').value='background';
 note($('inputRoute').value==='background'?'后台控件优先：不主动置前；没有对应能力时明确拒绝，不偷偷降级。':$('inputRoute').value==='direct'?'后台定向键鼠（实验）：已提交不等于应用执行成功。':'前台兼容方式：目标必须已经在前台，本程序不会自动激活。');
};
$('clickMode').onchange=()=>note($('clickMode').checked?'画面操作已启用：左键/右键发送给所选窗口；手机可在“点击按钮”选择右键再点画面。':'画面恢复只读；右键使用浏览器菜单。');
$('send').onclick=()=>run(async()=>{const text=$('text').value;if(!text)return;await visual({action:'text',text});$('text').value='';});
for(const b of document.querySelectorAll('[data-key]'))b.onclick=()=>run(()=>visual({action:'key',key:b.dataset.key}));
for(const b of document.querySelectorAll('[data-scroll]'))b.onclick=()=>run(()=>visual({action:'scroll',delta:Number(b.dataset.scroll)}));
$('auto').onchange=()=>{if($('auto').checked){note('已主动开启 3 秒刷新；预算耗尽、出错或页面隐藏时停止。');schedule();}else stopAuto();};
document.addEventListener('visibilitychange',()=>{if(document.hidden)stopAuto();});
for(const id of ['width','quality','roi'])$(id).onchange=()=>{revision='';note('参数已更改。下一次刷新需要新基线；不会自动发送画面。');};
$('export').onclick=()=>{const report={version:'0.1.1-demo',time:new Date().toISOString(),client:stats,host:{version:lastStatus.version,permissions:lastStatus.permissions,budget:lastStatus.budget,traffic:lastStatus.traffic},scope:'No token, window title, text, screenshot, IP or user-agent. HTTP bodies, not carrier bytes.'};const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='continuity-diagnostic.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
$('disconnect').onclick=()=>run(async()=>{stopAuto();try{await api('release');}catch{}token='';try{sessionStorage.removeItem('wc-token');sessionStorage.removeItem('wc-client');}catch{}resetView();$('pair').hidden=false;$('linkState').textContent='已断开';note('仅断开访问端；Mac 的应用和任务继续运行。');});
if(token)run(connect);
