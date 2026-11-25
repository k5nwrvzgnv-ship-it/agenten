'use strict';
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const cm=(mm,n=1)=>(mm/10).toLocaleString('de-DE',{maximumFractionDigits:n,useGrouping:false}),lies=t=>/^\s*\d+([.,]\d+)?\s*$/.test(t)?Math.round(parseFloat(t.replace(',','.'))*100)/10:null;
let S={balken:[],einstellungen:{},adressen:[]},bid=null,seite='1',jetzt=0,zeigt=null,laeuft=false,mess=null,formular=false,aendern=null;
let dreh={};try{dreh=JSON.parse(localStorage.getItem('aufnahme-dreh'))||{}}catch(e){}
async function ruf(weg,daten){let a;try{a=await fetch(weg,daten===undefined?{}:{method:'POST',headers:{'X-Aufnahme':'1'},body:daten instanceof Blob?daten:JSON.stringify(daten)})}catch(e){throw Error('Das Programm auf dem Mac antwortet nicht. Im Terminal neu starten.')}
 const j=await a.json();if(!a.ok)throw Error(j.fehler);return j}
const B=()=>S.balken.find(b=>b.id===bid),SE=()=>B().seiten[seite],fotos=s=>Object.keys(s.fotos).length,fertig=s=>s.plan&&fotos(s)>=s.plan.mitten_mm.length;
const offen=()=>{const p=SE().plan;return p?p.mitten_mm.findIndex((_,i)=>!SE().fotos[i]):-1};
const ersetze=b=>{const i=S.balken.findIndex(x=>x.id===b.id);i<0?S.balken.push(b):S.balken[i]=b};
function oeffne(id){bid=id;formular=false;seite=['1','2','3','4'].find(s=>!fertig(B().seiten[s]))||'1';seiteAuf()}
function seiteAuf(){jetzt=offen();const n=Object.keys(SE().fotos).map(Number).sort((a,b)=>a-b);zeigt=n.length?n.at(-1):null;mess=null;$('#afehler').textContent='';mal()}
function maleForm(b){formular=true;aendern=b||null;$('#ftitel').textContent=b?b.id+' ändern':'Neuer Balken';$('#form .haupt').textContent=b?'Maße speichern':'Balken anlegen';const f=$('#form form');for(const k of['laenge','breite','hoehe'])f[k].value=b?cm(b[k+'_mm']):'';f.holzart.value=b?b.holzart:'';$('#form .fehler').textContent='';mal();f.laenge.focus()}
$('#form form').onsubmit=async e=>{e.preventDefault();const f=e.target,d={holzart:f.holzart.value};$('#form .fehler').textContent='';
 for(const k of['laenge','breite','hoehe'])d[k+'_mm']=lies(f[k].value);if(aendern)d.id=aendern.id;
 try{const b=await ruf('/api/balken',d);ersetze(b);oeffne(b.id);document.activeElement.blur()}catch(x){$('#form .fehler').textContent=x.message}};
function bildHtml(f){const src=`/foto/${bid}/${f.vorschau}`;return src}
function mal(){
 $('#wahl').innerHTML=(formular&&!aendern?'<option value="">Neuer Balken</option>':'')+S.balken.map(b=>{const n=Object.values(b.seiten).filter(fertig).length;return `<option value="${b.id}" ${b.id===bid&&!(formular&&!aendern)?'selected':''}>${b.id}${n?` · ${n}/4 Seiten`:''}</option>`}).join('');
 $('#wahl').hidden=!S.balken.length;$('#form').hidden=!formular;$('#aufnahme').hidden=formular;if(formular)return;
 const b=B(),s=SE(),p=s.plan;
 $('#seiten').innerHTML=['1','2','3','4'].map(k=>{const x=b.seiten[k];return `<button data-s="${k}" aria-pressed="${k===seite}">Seite ${k}<small>${x.plan?fotos(x)+'/'+x.plan.mitten_mm.length:'–'}</small></button>`}).join('');
 lageMalen(b,p);
 const hat=fotos(s)>0;$('#vorschub').hidden=!p||p.mitten_mm.length<2;const vi=$('#vorschub input');if(p&&document.activeElement!==vi)vi.value=cm(p.schritt_mm);vi.disabled=hat;
 $('#werte').innerHTML=p?`<dt>Maße L × B × H</dt><dd>${cm(b.laenge_mm)} × ${cm(b.breite_mm)} × ${cm(b.hoehe_mm)}</dd><dt>${p.art} oben</dt><dd>${cm(p.flaeche_mm)} cm</dd><dt>Bildfeld</dt><dd>${cm(p.laengs_mm,0)} × ${cm(p.quer_mm,0)} cm</dd>`:'';
 const w=[];if(s.fehler)w.push(s.fehler);if(p){if(p.luecke)w.push('Vorschub größer als das Bildfeld, es bleibt eine Lücke.');if(p.zu_breit)w.push('Fläche breiter als das Bildfeld.');if(!p.abstand_gemessen&&!S.einstellungen.abstand_gemessen)w.push('Abstand Linse bis Rolle noch nicht gemessen (···).')}$('#warnung').textContent=w.join(' ');
 const nr=jetzt,m=p&&nr>=0?p.mitten_mm[nr]:0;let st='',kn='';
 if(!p){st='Diese Seite geht so nicht.'}
 else if(nr>=0){const vor=zeigt!==null&&nr>0?m-p.mitten_mm[nr-1]:0;
  st=s.fotos[nr]?`Abschnitt ${nr+1} wiederholen<small>Kameramitte bei ${cm(m)} cm</small>`:nr===0?`Balkenanfang unter die Kamera<small>Kameramitte bei ${cm(m)} cm ab Anfang</small>`:`${cm(vor)} cm weiterschieben<small>Kameramitte bei ${cm(m)} cm ab Anfang</small>`;
  kn=laeuft?'Foto wird gemacht …':s.fotos[nr]?'Foto wiederholen':`Foto ${nr+1} von ${p.mitten_mm.length}`}
 else{const n=naechste();st=n?`Seite ${seite} fertig<small>${(+n-+seite+4)%4===2?'Balken auf die Gegenseite rollen':'Balken um 90° rollen'}, Anfang bleibt vorn</small>`:`${b.id} fertig`;kn=n?`Weiter mit Seite ${n}`:'Neuer Balken'}
 $('#schritt').innerHTML=st;$('#los span').textContent=kn;$('#los').hidden=!kn;$('#los').disabled=laeuft;
 $('#abschnitte').innerHTML=p?p.mitten_mm.map((x,i)=>{const f=s.fotos[i];return `<button data-i="${i}" aria-pressed="${i===zeigt}" class="${i===nr?'jetzt':''}" aria-label="Abschnitt ${i+1}${f?'':', noch kein Foto'}">${f?`<img alt="" src="${bildHtml(f)}">`:''}<span>${cm(x,0)}</span></button>`}).join(''):'';
 const z=$('#abschnitte [aria-pressed=true]')||$('#abschnitte .jetzt');if(z)z.scrollIntoView({block:'nearest',inline:'nearest'});
 bildMalen(s);handyMalen()}
function naechste(){for(let i=1;i<4;i++){const k=String((+seite-1+i)%4+1);if(!fertig(B().seiten[k])&&B().seiten[k].plan)return k}return null}
function lageMalen(b,p){if(!p){$('#lage').innerHTML='';return}
 const H=Math.max(p.kamera_rolle_mm,100),k=125/H,h=p.hoch_mm*k,w=p.flaeche_mm*k,y0=150,q=p.quer_mm*k/2;
 $('#lage').innerHTML=`<svg viewBox="0 0 288 170" role="img" aria-label="Seite ${seite} oben, Abstand zur Kamera ${cm(p.abstand_mm)} cm"><path d="M144 25L${144-q} ${y0-h}H${144+q}Z" fill="#fff" opacity=".09"/><rect x="132" y="13" width="24" height="10" rx="2" fill="#a3a3a9"/><circle cx="144" cy="24" r="3" fill="#fff"/><rect x="${144-w/2}" y="${y0-h}" width="${w}" height="${h}" fill="#8a6543"/><path d="M${144-w/2} ${y0-h}h${w}" stroke="#fff" stroke-width="3"/><path d="M40 ${y0+4}H248" stroke="#77777d" stroke-width="3"/><path d="M262 25V${y0-h}M257 25h10M257 ${y0-h}h10" stroke="#a3a3a9"/><text x="256" y="${(25+y0-h)/2+4}" text-anchor="end">${cm(p.abstand_mm)} cm</text><text x="${144-w/2-8}" y="${y0-h+4}" text-anchor="end">Seite ${seite}</text></svg>`}
let winkel=0;
function bildMalen(s){const f=zeigt!==null&&s.fotos[zeigt],el=$('#bild'),inf=$('#bildinfo');el.classList.toggle('mess',!!mess);
 if(!f){el.innerHTML='<span>Noch kein Foto</span>';inf.innerHTML=fotos0()?'<span class="re"><button id="massaend">Maße ändern</button></span>':'';return}
 winkel=dreh.w||0;const src=bildHtml(f);
 if(el.dataset.src!==src||!el.querySelector('img')){el.innerHTML=`<img alt="${bid}, Seite ${seite}, Abschnitt ${zeigt+1}" src="${src}">`;el.dataset.src=src;el.querySelector('img').onload=stelle;el.querySelector('img').onerror=()=>{el.innerHTML='<span>Foto gespeichert, Vorschau nicht möglich</span>'}}
 stelle();
 inf.innerHTML=mess?`<span>${mess.p.length<2?'Zwei Punkte mit bekanntem Abstand anklicken':'Abstand eingeben'}</span><span class="re">${mess.p.length<2?'':`<label>Abstand<span><input id="strecke" inputmode="decimal" autocomplete="off">cm</span></label><button id="messok">Übernehmen</button>`}<button id="messab">Abbrechen</button></span>`
 :`<b>Abschnitt ${zeigt+1}</b><span>${f.breite_px?`${f.breite_px} × ${f.hoehe_px} px · `:''}${f.px_je_mm?f.px_je_mm.toLocaleString('de-DE')+' px/mm · ':''}${f.mb.toLocaleString('de-DE')} MB</span><span class="re"><button id="drehen">Drehen</button><button id="messen">Maßstab messen</button><button id="nochmal">Wiederholen</button></span>`;
 const st=$('#strecke');if(st)st.focus()}
const fotos0=()=>!Object.values(B().seiten).some(x=>fotos(x));
/* Lage des Bildes: lange Seite waagerecht, dazu die gemerkte Drehung um 0 oder 180 Grad */
function stelle(){const img=$('#bild img');if(!img||!img.naturalWidth)return;const el=$('#bild'),hoch=img.naturalHeight>img.naturalWidth,w=(hoch?90:0)+winkel,c=el.clientWidth,h=el.clientHeight;
 img.style.transform='';if(hoch){img.style.inset='50% auto auto 50%';img.style.width=h+'px';img.style.height=c+'px';img.style.transform=`translate(-50%,-50%) rotate(${w}deg)`}else{img.style.inset='0';img.style.width='100%';img.style.height='100%';img.style.transform=`rotate(${w}deg)`}
 if(mess)messMalen()}
addEventListener('resize',()=>{if(bid&&!formular)stelle()});
function rahmen(){const img=$('#bild img'),el=$('#bild'),a=Math.max(img.naturalWidth,img.naturalHeight)/Math.min(img.naturalWidth,img.naturalHeight),c=el.clientWidth,h=el.clientHeight,b=Math.min(c,h*a);return{b,x:(c-b)/2,y:(h-b/a)/2,h:b/a}}
function messMalen(){let v=$('#bild svg');if(v)v.remove();if(!mess)return;const r=rahmen(),p=mess.p.map(q=>[r.x+q[0]*r.b,r.y+q[1]*r.b]);
 $('#bild').insertAdjacentHTML('beforeend',`<svg>${p.length>1?`<path d="M${p[0]}L${p[1]}" stroke="#000" stroke-width="4"/><path d="M${p[0]}L${p[1]}" stroke="#00e0ea" stroke-width="2"/>`:''}${p.map(q=>`<circle cx="${q[0]}" cy="${q[1]}" r="6" fill="none" stroke="#00e0ea" stroke-width="2"/>`).join('')}</svg>`)}
$('#bild').onclick=e=>{if(!mess||mess.p.length>1||!$('#bild img'))return;const k=$('#bild').getBoundingClientRect(),r=rahmen();mess.p.push([(e.clientX-k.left-r.x)/r.b,(e.clientY-k.top-r.y)/r.b]);mal();messMalen()};
async function messOk(){const[a,b]=mess.p;try{S=await ruf('/api/massstab',{balken:bid,seite,anteil:Math.hypot(a[0]-b[0],a[1]-b[1]),strecke_mm:lies($('#strecke').value)});mess=null;$('#bild svg')?.remove();$('#afehler').textContent='';mal()}catch(x){$('#afehler').textContent=x.message}}
$('#bildinfo').onclick=e=>{const id=e.target.id;if(id==='drehen'){dreh.w=(winkel+180)%360;try{localStorage.setItem('aufnahme-dreh',JSON.stringify(dreh))}catch(x){}mal()}
 if(id==='messen'){mess={p:[]};mal()}if(id==='messab'){mess=null;$('#bild svg')?.remove();$('#afehler').textContent='';mal()}if(id==='messok')messOk();
 if(id==='nochmal'){jetzt=zeigt;e.target.blur();mal()}if(id==='massaend')maleForm(B())};
$('#bildinfo').onkeydown=e=>{if(e.key==='Enter'&&e.target.id==='strecke')messOk()};
async function los(){if(laeuft||formular||mess)return;const s=SE();if(!s.plan)return;
 if(jetzt<0){const n=naechste();if(n){seite=n;seiteAuf()}else maleForm();return}
 await nimm(()=>ruf('/api/ausloesen',{balken:bid,seite,nr:jetzt}))}
async function nimm(tu){const ziel=[bid,seite,jetzt];laeuft=true;$('#afehler').textContent='';mal();
 try{const r=await tu();ersetze(r.balken);if(bid===ziel[0]&&seite===ziel[1]){zeigt=ziel[2];jetzt=offen()}}catch(x){$('#afehler').textContent=x.message}
 laeuft=false;mal()}
$('#los').onclick=()=>{$('#los').blur();los()};
addEventListener('keydown',e=>{if(e.code!=='Space'||e.repeat||$('#dlg').open||formular||/^(INPUT|SELECT|BUTTON)$/.test(e.target.tagName))return;e.preventDefault();los()});
$('#seiten').onclick=e=>{const k=e.target.closest('button');if(!k||laeuft)return;seite=k.dataset.s;seiteAuf()};
$('#abschnitte').onclick=e=>{const k=e.target.closest('button');if(!k||laeuft)return;const i=+k.dataset.i;if(SE().fotos[i]){zeigt=i;jetzt=offen()}else jetzt=i;mess=null;mal()};
$('#vorschub input').onchange=async e=>{const i=e.target;try{ersetze(await ruf('/api/vorschub',{balken:bid,seite,mm:i.value.trim()?lies(i.value):0}));i.blur();$('#afehler').textContent='';seiteAuf()}catch(x){$('#afehler').textContent=x.message}};
$('#wahl').onchange=e=>{if(laeuft||!e.target.value)return mal();oeffne(e.target.value);e.target.blur()};$('#neu').onclick=()=>{if(!laeuft)maleForm()};
function handyMalen(){const h=$('#handy');h.className=S.handy?'da':'';h.querySelector('span').textContent=S.handy?'iPhone verbunden':'iPhone nicht verbunden'}
function dlg(){const a=S.adressen,m=S.einstellungen;$('#abstand').kr.value=cm(m.kamera_rolle_mm);$('#abstand .fehler').textContent='';
 $('#winkel').textContent=m.faktor_gemessen?'Gemessen.':'Angenommen (24 mm). Nach dem ersten Foto „Maßstab messen“.';
 const u=t=>a.map(x=>`<code>${esc(x+t)}</code>`).join(a.length>1?'<span class="leise">geht die erste nicht:</span>':'');
 $('#kurz').innerHTML=`<li>Wiederholen: 500 Mal</li><li>Inhalte von URL abrufen (GET)${u('/warten')}</li><li>Foto aufnehmen: 1 Foto, Rückkamera, Kameravorschau aus</li><li>Inhalte von URL abrufen: Methode POST, Anfragetext „Datei“, Datei = Foto${u('/foto')}</li><li>Aktionen 2 bis 4 liegen im „Wiederholen“. Starten, Zugriffe erlauben.</li>`;
 if(!$('#dlg').open)$('#dlg').showModal()}
$('#einst').onclick=$('#handy').onclick=dlg;$('.zu').onclick=()=>$('#dlg').close();$('#dlg').onclose=()=>document.activeElement.blur();
$('#abstand').onsubmit=async e=>{e.preventDefault();try{S=await ruf('/api/einstellungen',{kamera_rolle_mm:lies(e.target.kr.value)});$('#dlg').close();if(bid&&!formular)seiteAuf()}catch(x){$('#abstand .fehler').textContent=x.message}};
$('#datei').onchange=async e=>{const d=e.target.files[0];e.target.value='';if(!d||!bid||formular)return;$('#dlg').close();if(jetzt<0){$('#afehler').textContent='Erst einen Abschnitt wählen.';return}await nimm(()=>ruf(`/api/datei?balken=${bid}&seite=${seite}&nr=${jetzt}`,d))};
async function puls(){if(!laeuft)try{const n=await ruf('/api/stand');if(!laeuft){S.handy=n.handy;S.adressen=n.adressen;handyMalen();if(n.hinweis&&n.hinweis!==S.hinweis)$('#afehler').textContent=n.hinweis;S.hinweis=n.hinweis}}catch(e){S.handy=false;handyMalen();$('#handy span').textContent='Programm beendet'}setTimeout(puls,1500)}
ruf('/api/stand').then(n=>{S=n;S.balken.length?oeffne(S.balken.at(-1).id):maleForm();handyMalen();puls()}).catch(e=>{document.body.append(e.message)});
