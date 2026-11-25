'use strict';
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const cm=(mm,n=1)=>(mm/10).toLocaleString('de-DE',{maximumFractionDigits:n,useGrouping:false}),lies=t=>/^\s*\d+([.,]\d+)?\s*$/.test(t)?Math.round(parseFloat(t.replace(',','.'))*100)/10:null;
const PF={kamera:'M4 8h3l2-3h6l2 3h3v11H4zM12 10a3.5 3.5 0 1 0 0 7a3.5 3.5 0 0 0 0-7z',drehen:'M4 12a8 8 0 0 1 14-5.3L20 9M20 4v5h-5M20 12a8 8 0 0 1-14 5.3L4 15M4 20v-5h5',mass:'M3 9h18v7H3zM7 9v3M11 9v4M15 9v3',stift:'M4 20l1-5L16 4l4 4L9 19zM13.5 6.5l4 4',weg:'M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v5M14 11v5',zurueck:'M9 5L4 10l5 5M4 10h10a5 5 0 0 1 0 10h-3',ziel:'M12 3v4M12 17v4M3 12h4M17 12h4M12 8a4 4 0 1 0 0 8a4 4 0 0 0 0-8z',ganz:'M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5',zuschnitt:'M7 2v15h15M2 7h15v15',ja:'M4 13l5 5L20 6',nein:'M6 6l12 12M18 6L6 18',schieben:'M3 12h17M14 6l6 6-6 6',rollen:'M5 13a7 7 0 1 0 3-6L5 9M5 4v5h5',plus:'M12 5v14M5 12h14',kopf:'M5 4v16M9 12h11M15 7l5 5-5 5'};
const ic=n=>`<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="${PF[n]}"/></svg>`,ik=(id,n,name)=>`<button id="${id}" class="sy" title="${name}" aria-label="${name}">${ic(n)}</button>`;
/* Querschnitt liegend gezeichnet; die Kante der Seite ist hell: 1 oben, 2 rechts, 3 unten, 4 links */
function quer(b,k){const l=Math.max(b.breite_mm,b.hoehe_mm),s=Math.min(b.breite_mm,b.hoehe_mm),w=38,h=Math.max(13,38*s/l),x=(50-w)/2,y=(50-h)/2,e={1:`M${x} ${y}h${w}`,2:`M${x+w} ${y}v${h}`,3:`M${x} ${y+h}h${w}`,4:`M${x} ${y}v${h}`}[k];
 return `<svg class="qs" viewBox="0 0 50 50" aria-hidden="true"><rect x="${x}" y="${y}" width="${w}" height="${h}" class="holz"/><path d="${e}" class="kante"/></svg>`}
const sname=(b,k)=>{const p=b.seiten[k].plan;return `Seite ${k}${p?', '+p.art:''}`};
let S={balken:[],einstellungen:{},adressen:[]},bid=null,seite='1',jetzt=0,zeigt=null,laeuft=false,geloescht=null,mess=null,formular=false,aendern=null;
let dreh={};try{dreh=JSON.parse(localStorage.getItem('aufnahme-dreh'))||{}}catch(e){}
async function ruf(weg,daten){let a;try{a=await fetch(weg,daten===undefined?{}:{method:'POST',headers:{'X-Aufnahme':'1'},body:daten instanceof Blob?daten:JSON.stringify(daten)})}catch(e){throw Error('Das Programm auf dem Mac antwortet nicht. Im Terminal neu starten.')}
 const j=await a.json();if(!a.ok)throw Error(j.fehler);return j}
const B=()=>S.balken.find(b=>b.id===bid),SE=()=>B().seiten[seite],fotos=s=>Object.keys(s.fotos).length,fertig=s=>s.plan&&fotos(s)>=s.plan.mitten_mm.length;
const offen=()=>{const p=SE().plan;return p?p.mitten_mm.findIndex((_,i)=>!SE().fotos[i]):-1};
const ersetze=b=>{const i=S.balken.findIndex(x=>x.id===b.id);i<0?S.balken.push(b):S.balken[i]=b};
function oeffne(id){bid=id;formular=false;seite=['1','2','3','4'].find(s=>!fertig(B().seiten[s]))||'1';seiteAuf()}
function seiteAuf(){jetzt=offen();const n=Object.keys(SE().fotos).map(Number).sort((a,b)=>a-b);zeigt=n.length?n.at(-1):null;mess=schneide=null;$('#afehler').textContent='';mal()}
function maleForm(b){formular=true;aendern=b||null;$('#ftitel').textContent=b?b.id+' ändern':'Neuer Balken';$('#form .haupt').textContent=b?'Maße speichern':'Balken anlegen';const f=$('#form form');for(const k of['laenge','breite','hoehe'])f[k].value=b?cm(b[k+'_mm']):'';f.holzart.value=b?b.holzart:'';$('#form .fehler').textContent='';mal();f.laenge.focus()}
$('#form form').onsubmit=async e=>{e.preventDefault();const f=e.target,d={holzart:f.holzart.value};$('#form .fehler').textContent='';
 for(const k of['laenge','breite','hoehe'])d[k+'_mm']=lies(f[k].value);if(aendern)d.id=aendern.id;
 try{const b=await ruf('/api/balken',d);ersetze(b);oeffne(b.id);document.activeElement.blur()}catch(x){$('#form .fehler').textContent=x.message}};
function bildHtml(f){const src=`/foto/${bid}/${f.vorschau}`;return src}
function mal(){
 $('#wahl').innerHTML=(formular&&!aendern?'<option value="">Neuer Balken</option>':'')+S.balken.map(b=>{const n=Object.values(b.seiten).filter(fertig).length;return `<option value="${b.id}" ${b.id===bid&&!(formular&&!aendern)?'selected':''}>${b.id}${n?` · ${n}/4 Seiten`:''}</option>`}).join('');
 $('#wahl').hidden=!S.balken.length;$('#form').hidden=!formular;$('#aufnahme').hidden=formular;if(formular)return;
 const b=B(),s=SE(),p=s.plan;
 $('#seiten').innerHTML=['1','2','3','4'].map(k=>{const x=b.seiten[k];return `<button data-s="${k}" aria-pressed="${k===seite}" title="${sname(b,k)}" aria-label="${sname(b,k)}">${quer(b,k)}<small>${x.plan?fotos(x)+'/'+x.plan.mitten_mm.length:'–'}</small></button>`}).join('');
 lageMalen(b,p);
 const hat=fotos(s)>0;$('#vorschub').hidden=!p||p.mitten_mm.length<2;const vi=$('#vorschub input');if(p&&document.activeElement!==vi)vi.value=cm(p.schritt_mm);vi.disabled=hat;
 $('#werte').innerHTML=p?`<dt>L × B × H</dt><dd>${cm(b.laenge_mm)} × ${cm(b.breite_mm)} × ${cm(b.hoehe_mm)} cm</dd><dt>Bildfeld</dt><dd>${cm(p.laengs_mm,0)} × ${cm(p.quer_mm,0)} cm</dd>`:'';
 const w=[];if(s.fehler)w.push(s.fehler);if(p){if(p.luecke)w.push('Vorschub größer als das Bildfeld, es bleibt eine Lücke.');if(p.zu_breit)w.push('Fläche breiter als das Bildfeld.');if(!p.abstand_gemessen&&!S.einstellungen.abstand_gemessen)w.push('Abstand Linse bis Rolle noch nicht gemessen (···).')}$('#warnung').textContent=w.join(' ');
 const nr=jetzt,m=p&&nr>=0?p.mitten_mm[nr]:0;let st='',kn='',kl='';
 if(!p){st='Diese Seite geht so nicht.'}
 else if(nr>=0){const vor=zeigt!==null&&nr>0?m-p.mitten_mm[nr-1]:0;
  st=s.fotos[nr]?`${ic('kamera')}<b>${cm(m)} cm</b>`:nr===0||!s.fotos[nr-1]||zeigt!==nr-1?`${ic('kopf')}<b>${cm(m)} cm</b><small>Bildmitte ab Anfang</small>`:`${ic('schieben')}<b>${cm(vor)} cm</b><small>Bildmitte ${cm(m)} cm ab Anfang</small>`;
  kn=ic('kamera')+(laeuft?' …':` ${nr+1}/${p.mitten_mm.length}`);kl=s.fotos[nr]?'Foto wiederholen':`Foto ${nr+1} von ${p.mitten_mm.length} auslösen`}
 else{const n=naechste();const g=n?(+n-+seite+4)%4:0;st=n?`${quer(b,seite)}${ic('rollen')}<b>${g*90}°</b>${quer(b,n)}`:`${ic('ja')}<b>${b.id}</b>`;kn=ic(n?'schieben':'plus')+(n?quer(b,n):'');kl=n?`Balken um ${g*90} Grad gerollt, weiter mit ${sname(b,n)}`:'Neuer Balken'}
 $('#schritt').innerHTML=st;$('#los span').innerHTML=kn;$('#los').title=kl;$('#los').setAttribute('aria-label',kl);$('#los').hidden=!kn;$('#los').disabled=laeuft;
 $('#abschnitte').innerHTML=p?p.mitten_mm.map((x,i)=>{const f=s.fotos[i];return `<button data-i="${i}" aria-pressed="${i===zeigt}" class="${i===nr?'jetzt':''}" aria-label="Abschnitt ${i+1}${f?'':', noch kein Foto'}">${f?`<canvas data-src="${bildHtml(f)}"></canvas>`:S.app&&i===nr?'<canvas class="lk"></canvas>':''}<span>${cm(x,0)}</span></button>`}).join(''):'';
 const z=$('#abschnitte [aria-pressed=true]')||$('#abschnitte .jetzt');if(z)z.scrollIntoView({block:'nearest',inline:'nearest'});
 bildMalen(s);handyMalen();appMalen();$$('#abschnitte canvas[data-src]').forEach(c=>hole(c.dataset.src,i=>{if(i)zeichne(c,i,p.zuschnitt,300)}))}
function naechste(){for(let i=1;i<4;i++){const k=String((+seite-1+i)%4+1);if(!fertig(B().seiten[k])&&B().seiten[k].plan)return k}return null}
function lageMalen(b,p){if(!p){$('#lage').innerHTML='';return}
 const H=Math.max(p.kamera_rolle_mm,100),k=125/H,h=p.hoch_mm*k,w=p.flaeche_mm*k,y0=150,q=p.quer_mm*k/2;
 $('#lage').innerHTML=`<svg viewBox="0 0 288 170" role="img" aria-label="Seite ${seite} oben, Abstand zur Kamera ${cm(p.abstand_mm)} cm"><path d="M144 25L${144-q} ${y0-h}H${144+q}Z" fill="#fff" opacity=".09"/><rect x="132" y="13" width="24" height="10" rx="2" fill="#a3a3a9"/><circle cx="144" cy="24" r="3" fill="#fff"/><rect x="${144-w/2}" y="${y0-h}" width="${w}" height="${h}" fill="#8a6543"/><path d="M${144-w/2} ${y0-h}h${w}" stroke="#fff" stroke-width="3"/><path d="M40 ${y0+4}H248" stroke="#77777d" stroke-width="3"/><path d="M262 25V${y0-h}M257 25h10M257 ${y0-h}h10" stroke="#a3a3a9"/><text x="256" y="${(25+y0-h)/2+4}" text-anchor="end">${cm(p.abstand_mm)} cm</text></svg>`}
let winkel=0,schneide=null;const BILDER=new Map();
function hole(src,dann){let i=BILDER.get(src);if(!i){if(BILDER.size>60)BILDER.delete(BILDER.keys().next().value);i=new Image();i.src=src;BILDER.set(src,i)}if(i.complete){dann(i.naturalWidth?i:null);return}i.addEventListener('load',()=>dann(i),{once:true});i.addEventListener('error',()=>dann(null),{once:true})}
/* Zeichnet mit langer Seite waagerecht, auf den Zuschnitt begrenzt */
function zeichne(c,img,z,max){const W=img.naturalWidth,H=img.naturalHeight,hoch=H>W,L=hoch?H:W,K=hoch?W:H,[x,y,b,h]=z||[0,0,1,1],f=Math.min(1,max/(L*b));c.width=Math.max(1,Math.round(L*b*f));c.height=Math.max(1,Math.round(K*h*f));const g=c.getContext('2d',{willReadFrequently:true});g.setTransform(f,0,0,f,-x*L*f,-y*K*f);if(hoch){g.translate(L,0);g.rotate(Math.PI/2)}g.drawImage(img,0,0)}
const ausschnitt=()=>schneide?null:SE().plan&&SE().plan.zuschnitt;
function leinwand(){const el=$('#bild');let c=el.querySelector('canvas');if(!c){el.innerHTML='<canvas role="img"></canvas>';c=el.querySelector('canvas')}c.style.transform=`rotate(${winkel}deg)`;return c}
function bildMalen(s){const f=zeigt!==null&&s.fotos[zeigt],el=$('#bild'),inf=$('#bildinfo');winkel=dreh.w||0;el.classList.toggle('mess',!!(mess||schneide));
 if(schneide){inf.innerHTML=`<span>Rahmen um den Boxboden ziehen</span><span class="re">${schneide.r?ik('zuok','ja','Zuschnitt übernehmen'):''}${S.einstellungen.zuschnitt?ik('zuganz','ganz','Ganzes Bild'):''}${ik('zuab','nein','Abbrechen')}</span>`}
 const sch=ik('zuschnitt','zuschnitt','Aufnahmebereich begrenzen');
 if(!f){el.dataset.src='';const u=geloescht&&geloescht.balken===bid&&geloescht.seite===seite&&geloescht.nr===zeigt?ik('zurueck','zurueck','Löschen rückgängig'):'';
  if(S.app){leinwand().setAttribute('aria-label','Live-Bild');live()}else el.innerHTML='<span>Noch kein Foto</span>';
  if(!schneide)inf.innerHTML=`<span class="re">${u}${!u&&fotos0()?ik('massaend','stift','Maße ändern'):''}${S.app?ik('drehen','drehen','Bild drehen')+sch:''}</span>`;return}
 const src=bildHtml(f),k=src+JSON.stringify(ausschnitt());if(el.dataset.src!==k||!el.querySelector('canvas')){el.dataset.src=k;hole(src,i=>{if(el.dataset.src!==k)return;if(!i){el.innerHTML='<span>Foto gespeichert, Vorschau nicht möglich</span>';return}const c=leinwand();c.setAttribute('aria-label',`${bid}, Seite ${seite}, Abschnitt ${zeigt+1}`);zeichne(c,i,ausschnitt(),2400);ueber()})}else leinwand();
 if(!schneide)inf.innerHTML=mess?`<span>${mess.p.length<2?'Zwei Punkte mit bekanntem Abstand anklicken':'Abstand eingeben'}</span><span class="re">${mess.p.length<2?'':`<label>Abstand<span><input id="strecke" inputmode="decimal" autocomplete="off">cm</span></label>${ik('messok','ja','Übernehmen')}`}${ik('messab','nein','Abbrechen')}</span>`
 :`<b>Abschnitt ${zeigt+1}</b><span>${f.breite_px?`${f.breite_px} × ${f.hoehe_px} px · `:''}${f.px_je_mm?f.px_je_mm.toLocaleString('de-DE')+' px/mm · ':''}${f.mb.toLocaleString('de-DE')} MB${f.kamera&&f.kamera.dauer?' · '+belicht(f.kamera):''}</span><span class="re">${ik('drehen','drehen','Bild drehen')}${sch}${ik('messen','mass','Maßstab messen')}${ik('nochmal','kamera','Foto wiederholen')}${ik('weg','weg','Foto löschen')}</span>`;
 ueber();const st=$('#strecke');if(st)st.focus()}
function ueber(){messMalen();pruefe()}
addEventListener('resize',()=>{if(bid&&!formular)ueber()});
function rahmen(){const c=$('#bild canvas'),el=$('#bild'),a=c.width/c.height,w=el.clientWidth,h=el.clientHeight,b=Math.min(w,h*a);return{b,h:b/a,x:(w-b)/2,y:(h-b/a)/2}}
function messMalen(){$('#bild svg')?.remove();const c=$('#bild canvas');if(!c||!(mess||schneide))return;const r=rahmen();let in_='';
 if(mess){const p=mess.p.map(q=>[r.x+q[0]*r.b,r.y+q[1]*r.b]);in_=(p.length>1?`<path d="M${p[0]}L${p[1]}" stroke="#000" stroke-width="4"/><path d="M${p[0]}L${p[1]}" stroke="#00e0ea" stroke-width="2"/>`:'')+p.map(q=>`<circle cx="${q[0]}" cy="${q[1]}" r="6" fill="none" stroke="#00e0ea" stroke-width="2"/>`).join('')}
 else if(schneide.r){const[x,y,b,h]=schneide.r;in_=`<path fill="#000b" fill-rule="evenodd" d="M0 0h9999v9999H0zM${r.x+x*r.b} ${r.y+y*r.h}h${b*r.b}v${h*r.h}h${-b*r.b}z"/><rect x="${r.x+x*r.b}" y="${r.y+y*r.h}" width="${b*r.b}" height="${h*r.h}" fill="none" stroke="#00e0ea" stroke-width="2"/>`}
 $('#bild').insertAdjacentHTML('beforeend',`<svg>${in_}</svg>`)}
const punkt=e=>{const k=$('#bild').getBoundingClientRect(),r=rahmen();return[Math.min(1,Math.max(0,(e.clientX-k.left-r.x)/r.b)),Math.min(1,Math.max(0,(e.clientY-k.top-r.y)/r.h))]};
$('#bild').onclick=e=>{if(!mess||mess.p.length>1||!$('#bild canvas'))return;const k=$('#bild').getBoundingClientRect(),r=rahmen();mess.p.push([(e.clientX-k.left-r.x)/r.b,(e.clientY-k.top-r.y)/r.b]);mal()};
$('#bild').onpointerdown=e=>{if(!schneide||!$('#bild canvas'))return;e.preventDefault();$('#bild').setPointerCapture(e.pointerId);schneide.a=punkt(e)};
$('#bild').onpointermove=e=>{if(!schneide||!schneide.a)return;const p=punkt(e),a=schneide.a;schneide.r=[Math.min(a[0],p[0]),Math.min(a[1],p[1]),Math.abs(a[0]-p[0]),Math.abs(a[1]-p[1])];messMalen()};
$('#bild').onpointerup=$('#bild').onpointercancel=()=>{if(schneide&&schneide.a){schneide.a=null;mal()}};
async function schnitt(r){if(r&&winkel)r=[1-r[0]-r[2],1-r[1]-r[3],r[2],r[3]].map(v=>Math.max(0,v));try{S=await ruf('/api/zuschnitt',{zuschnitt:r});schneide=null;$('#afehler').textContent=fotos(SE())?'Gilt für Seiten ohne Fotos. Diese Seite hat schon welche.':'';jetzt=offen();mal()}catch(x){$('#afehler').textContent=x.message}}
async function messOk(){const[a,b]=mess.p,z=ausschnitt();try{S=await ruf('/api/massstab',{balken:bid,seite,anteil:Math.hypot(a[0]-b[0],a[1]-b[1])*(z?z[2]:1),strecke_mm:lies($('#strecke').value)});mess=null;$('#afehler').textContent='';mal()}catch(x){$('#afehler').textContent=x.message}}
$('#bildinfo').onclick=e=>{const id=e.target.closest('button')?.id;if(!id||laeuft)return;if(id==='drehen'){dreh.w=(winkel+180)%360;try{localStorage.setItem('aufnahme-dreh',JSON.stringify(dreh))}catch(x){}mal()}
 if(id==='messen'){mess={p:[]};mal()}if(id==='messab'){mess=null;$('#afehler').textContent='';mal()}if(id==='messok')messOk();
 if(id==='zuschnitt'){schneide={r:null};mess=null;$('#bild').dataset.src='';mal()}if(id==='zuab'){schneide=null;mal()}if(id==='zuok')schnitt(schneide.r);if(id==='zuganz')schnitt(null);
 if(id==='nochmal'){jetzt=zeigt;document.activeElement.blur();mal()}if(id==='weg')loesche();if(id==='zurueck')zurueck();if(id==='massaend')maleForm(B())};
$('#bildinfo').onkeydown=e=>{if(e.key==='Enter'&&e.target.id==='strecke')messOk()};
const belicht=k=>`${k.dauer<.5?'1/'+Math.round(1/k.dauer):k.dauer.toFixed(1)} s · ISO ${Math.round(k.iso)}`;
let lz=0;function live(){const n=++lz,i=new Image();i.onload=()=>{if(n!==lz||formular||!S.app)return;const k=$('#abschnitte .jetzt .lk');if(k)zeichne(k,i,SE().plan&&SE().plan.zuschnitt,300);const c=$('#bild canvas');if(c&&!(zeigt!==null&&SE().fotos[zeigt])){zeichne(c,i,ausschnitt(),2400);ueber()}};i.src='/live.jpg?'+Date.now()}
setInterval(()=>{if(S.app&&!formular&&!document.hidden)live()},500);
/* Anteil ausgebrannter Pixel unter den nicht dunklen (das Holz) */
function ausgebrannt(q){const c=document.createElement('canvas');c.width=300;c.height=225;const x=c.getContext('2d',{willReadFrequently:true});x.drawImage(q,0,0,300,225);const d=x.getImageData(0,0,300,225).data;let n=0,w=0;for(let i=0;i<d.length;i+=4){const m=Math.max(d[i],d[i+1],d[i+2]);if(m<110)continue;n++;if(m>=253)w++}return n?w/n:0}
function pruefe(){$('#brand')?.remove();const c=$('#bild canvas');if(!c||mess||schneide)return;const a=ausgebrannt(c);if(a>.01)$('#bildinfo').insertAdjacentHTML('afterbegin',`<span id="brand" class="warn">${Math.round(a*100)} % überbelichtet</span>`)}
function appMalen(){const a=S.app;$('#kam').hidden=!a;if(!a)return;$('#kam output').textContent=a.dauer?belicht(a):'–';$$('#kam [data-m]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.m===a.modus))}
$('#kam').onclick=async e=>{const b=e.target.closest('button');if(!b)return;b.blur();try{await ruf('/api/kamera',b.dataset.m?{art:'modus',wert:b.dataset.m}:b.dataset.ev?{art:'ev',wert:+b.dataset.ev}:{art:'einmessen'});$('#afehler').textContent=''}catch(x){$('#afehler').textContent=x.message}};
const fotos0=()=>!Object.values(B().seiten).some(x=>fotos(x));
async function los(){if(laeuft||formular||mess||schneide)return;const s=SE();if(!s.plan)return;
 if(jetzt<0){const n=naechste();if(n){seite=n;seiteAuf()}else maleForm();return}
 await nimm(()=>ruf('/api/ausloesen',{balken:bid,seite,nr:jetzt}))}
async function loesche(){if(laeuft||formular||mess||schneide||zeigt===null||!SE().fotos[zeigt])return;const z={balken:bid,seite,nr:zeigt};document.activeElement.blur();await nimm(()=>ruf('/api/loeschen',z),true);if(!SE().fotos[z.nr]){geloescht=z;jetzt=z.nr;zeigt=z.nr;mal()}}
async function zurueck(){if(laeuft||!geloescht)return;const z=geloescht;document.activeElement.blur();laeuft=true;try{const r=await ruf('/api/zurueck',z);ersetze(r.balken);geloescht=null;jetzt=offen();zeigt=z.nr;$('#afehler').textContent=''}catch(x){$('#afehler').textContent=x.message}laeuft=false;mal()}
async function nimm(tu,loescht){const ziel=[bid,seite,jetzt];laeuft=true;$('#afehler').textContent='';if(!loescht){geloescht=null;mal()}
 try{const r=await tu();ersetze(r.balken);if(bid===ziel[0]&&seite===ziel[1]){zeigt=ziel[2];jetzt=offen()}}catch(x){$('#afehler').textContent=x.message}
 laeuft=false;mal()}
$('#los').onclick=()=>{$('#los').blur();los()};
addEventListener('keydown',e=>{if(e.code!=='Space'||e.repeat||$('#dlg').open||formular||/^(INPUT|SELECT|BUTTON)$/.test(e.target.tagName))return;e.preventDefault();los()});
addEventListener('keydown',e=>{if($('#dlg').open||/^(INPUT|SELECT)$/.test(e.target.tagName)||formular)return;if((e.key==='Delete'||e.key==='Backspace')&&!e.repeat){e.preventDefault();loesche()}if(e.key==='z'&&(e.metaKey||e.ctrlKey)&&geloescht&&geloescht.balken===bid&&geloescht.seite===seite){e.preventDefault();zurueck()}});
$('#seiten').onclick=e=>{const k=e.target.closest('button');if(!k||laeuft)return;seite=k.dataset.s;seiteAuf()};
$('#abschnitte').onclick=e=>{const k=e.target.closest('button');if(!k||laeuft)return;const i=+k.dataset.i;if(SE().fotos[i]){zeigt=i;jetzt=offen()}else{jetzt=i;zeigt=null}mess=schneide=null;mal()};
$('#vorschub input').onchange=async e=>{const i=e.target;try{ersetze(await ruf('/api/vorschub',{balken:bid,seite,mm:i.value.trim()?lies(i.value):0}));i.blur();$('#afehler').textContent='';seiteAuf()}catch(x){$('#afehler').textContent=x.message}};
$('#wahl').onchange=e=>{if(laeuft||!e.target.value)return mal();oeffne(e.target.value);e.target.blur()};$('#neu').onclick=()=>{if(!laeuft)maleForm()};
function handyMalen(){const h=$('#handy');h.className=S.handy?'da':'';const n=S.handy?'iPhone verbunden':'iPhone nicht verbunden';h.title=n;h.setAttribute('aria-label',n)}
function dlg(){const a=S.adressen,m=S.einstellungen;$('#abstand').kr.value=cm(m.kamera_rolle_mm);$('#abstand .fehler').textContent='';
 $('#winkel').textContent=m.faktor_gemessen?'Gemessen.':'Angenommen (24 mm). Nach dem ersten Foto mit dem Lineal unter dem Bild messen.';
 $('#appadr').innerHTML=a.map(esc).join('<br>');const u=t=>a.map(x=>`<code>${esc(x+t)}</code>`).join(a.length>1?'<span class="leise">geht die erste nicht:</span>':'');
 $('#kurz').innerHTML=`<li>Wiederholen: 500 Mal</li><li>Inhalte von URL abrufen (GET)${u('/warten')}</li><li>Foto aufnehmen: 1 Foto, Rückkamera, Kameravorschau aus</li><li>Inhalte von URL abrufen: Methode POST, Anfragetext „Datei“, Datei = Foto${u('/foto')}</li><li>Aktionen 2 bis 4 liegen im „Wiederholen“. Starten, Zugriffe erlauben.</li>`;
 if(!$('#dlg').open)$('#dlg').showModal()}
$('#einst').onclick=$('#handy').onclick=dlg;$('.zu').onclick=()=>$('#dlg').close();$('#dlg').onclose=()=>document.activeElement.blur();
$('#abstand').onsubmit=async e=>{e.preventDefault();try{S=await ruf('/api/einstellungen',{kamera_rolle_mm:lies(e.target.kr.value)});$('#dlg').close();if(bid&&!formular)seiteAuf()}catch(x){$('#abstand .fehler').textContent=x.message}};
$('#datei').onchange=async e=>{const d=e.target.files[0];e.target.value='';if(!d||!bid||formular)return;$('#dlg').close();if(jetzt<0){$('#afehler').textContent='Erst einen Abschnitt wählen.';return}await nimm(()=>ruf(`/api/datei?balken=${bid}&seite=${seite}&nr=${jetzt}`,d))};
async function puls(){if(!laeuft)try{const n=await ruf('/api/stand');if(!laeuft){const vor=!!S.app;S.handy=n.handy;S.app=n.app;if(vor!==!!S.app&&!formular&&bid&&!(zeigt!==null&&SE().fotos[zeigt]))mal();appMalen();S.adressen=n.adressen;handyMalen();if(n.hinweis&&n.hinweis!==S.hinweis)$('#afehler').textContent=n.hinweis;S.hinweis=n.hinweis}}catch(e){S.handy=false;handyMalen();$('#handy').title='Programm beendet';$('#afehler').textContent='Das Programm auf dem Mac antwortet nicht.'}setTimeout(puls,1500)}
ruf('/api/stand').then(n=>{S=n;S.balken.length?oeffne(S.balken.at(-1).id):maleForm();handyMalen();puls()}).catch(e=>{document.body.append(e.message)});
