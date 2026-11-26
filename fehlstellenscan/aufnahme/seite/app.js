'use strict';
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const cm=(mm,n=1)=>(mm/10).toLocaleString('de-DE',{maximumFractionDigits:n,useGrouping:false}),lies=t=>/^\s*\d+([.,]\d+)?\s*$/.test(t)?Math.round(parseFloat(t.replace(',','.'))*100)/10:null;
const PF={kamera:'M4 8h3l2-3h6l2 3h3v11H4zM12 10a3.5 3.5 0 1 0 0 7a3.5 3.5 0 0 0 0-7z',drehen:'M4 12a8 8 0 0 1 14-5.3L20 9M20 4v5h-5M20 12a8 8 0 0 1-14 5.3L4 15M4 20v-5h5',mass:'M3 9h18v7H3zM7 9v3M11 9v4M15 9v3',stift:'M4 20l1-5L16 4l4 4L9 19zM13.5 6.5l4 4',weg:'M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v5M14 11v5',zurueck:'M9 5L4 10l5 5M4 10h10a5 5 0 0 1 0 10h-3',ziel:'M12 3v4M12 17v4M3 12h4M17 12h4M12 8a4 4 0 1 0 0 8a4 4 0 0 0 0-8z',ganz:'M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5',zuschnitt:'M7 2v15h15M2 7h15v15',ja:'M4 13l5 5L20 6',nein:'M6 6l12 12M18 6L6 18',schieben:'M3 12h17M14 6l6 6-6 6',rollen:'M5 13a7 7 0 1 0 3-6L5 9M5 4v5h5',plus:'M12 5v14M5 12h14',etikett:'M3 3h8l10 10-8 8L3 11zM7.5 7.5h.01',skala:'M5 19L19 5M13 5h6v6M5 13v6h6',kopf:'M5 4v16M9 12h11M15 7l5 5-5 5'};
const ic=n=>`<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="${PF[n]}"/></svg>`,ik=(id,n,name)=>`<button id="${id}" class="sy" title="${name}" aria-label="${name}">${ic(n)}</button>`;
const kw=(id,n,name,kl='')=>`<button id="${id}" class="sy ${kl}" title="${name}" aria-label="${name}">${ic(n)}</button>`;
const sname=(b,k)=>{const p=b.seiten[k].plan;return `Seite ${k}${p?', '+p.art:''}`};
/* Balken im Schrägbild, Länge in die Tiefe. Seite k schraffiert: 1 oben, 2 rechts, 3 unten, 4 links; verdeckte Kanten gestrichelt */
function balken3d(b,k){const l=Math.max(b.breite_mm,b.hoehe_mm),s=Math.min(b.breite_mm,b.hoehe_mm),w=16,h=Math.max(7,16*s/l),dx=30,dy=-15,x=6,y=4-dy,P=q=>q.map(z=>z.toFixed(1)).join(' ');
 const v=[[x,y],[x+w,y],[x+w,y+h],[x,y+h]],r=v.map(([a,c])=>[a+dx,c+dy]),f={1:[v[0],v[1],r[1],r[0]],2:[v[1],r[1],r[2],v[2]],3:[v[3],v[2],r[2],r[3]],4:[v[0],r[0],r[3],v[3]]}[k];
 return `<svg class="b3" viewBox="0 0 ${x+w+dx+6} ${(y+h+6).toFixed(1)}" aria-hidden="true"><path d="M${f.map(P).join('L')}Z" class="flaeche${+k>2?' hinten':''}"/><path d="M${P(v[3])}L${P(r[3])}L${P(r[2])}M${P(r[0])}L${P(r[3])}" class="verdeckt"/><path d="M${P(v[0])}H${x+w}V${(y+h).toFixed(1)}H${x}ZM${P(v[0])}L${P(r[0])}L${P(r[1])}L${P(r[2])}L${P(v[2])}M${P(v[1])}L${P(r[1])}" class="kanten"/></svg>`}
/* Längen unter 10 cm in mm, sonst in cm; Eingabe in derselben Einheit */
const einheit=mm=>mm<100?'mm':'cm',laenge=mm=>mm<100?`${mm.toLocaleString('de-DE',{maximumFractionDigits:1})} mm`:`${cm(mm)} cm`;
const prozent=x=>(x>0?'+':x<0?'−':'±')+Math.abs(x).toLocaleString('de-DE',{minimumFractionDigits:1,maximumFractionDigits:1})+' %';
let S={balken:[],einstellungen:{},adressen:[]},bid=null,bweg=null,seite='1',jetzt=0,zeigt=null,laeuft=false,geloescht=null,mess=null,formular=false,aendern=null,geprueft=null;
let dreh={};try{dreh=JSON.parse(localStorage.getItem('aufnahme-dreh'))||{}}catch(e){}
async function ruf(weg,daten){let a;try{a=await fetch(weg,daten===undefined?{}:{method:'POST',headers:{'X-Aufnahme':'1'},body:daten instanceof Blob?daten:JSON.stringify(daten)})}catch(e){throw Error('Das Programm auf dem Mac antwortet nicht. Im Terminal neu starten.')}
 const j=await a.json();if(!a.ok)throw Error(j.fehler);return j}
const B=()=>S.balken.find(b=>b.id===bid),SE=()=>B().seiten[seite],fotos=s=>Object.keys(s.fotos).length,fertig=s=>s.plan&&fotos(s)>=s.plan.mitten_mm.length;
const offen=()=>{const p=SE().plan;return p?p.mitten_mm.findIndex((_,i)=>!SE().fotos[i]):-1};
const ersetze=b=>{const i=S.balken.findIndex(x=>x.id===b.id);i<0?S.balken.push(b):S.balken[i]=b};
function oeffne(id,s){if($('#werte .medit'))masseSpeichern();bid=id;formular=false;seite=s||['1','2','3','4'].find(s=>!fertig(B().seiten[s]))||'1';seiteAuf()}
function seiteAuf(){jetzt=offen();const n=Object.keys(SE().fotos).map(Number).sort((a,b)=>a-b);zeigt=n.length?n.at(-1):null;mess=schneide=geprueft=null;$('#afehler').textContent='';mal()}
/* Anlegen und Ändern im selben Formular. Ändern geht auch mit Fotos: die bleiben, der Server passt Abstand und Maßstab an */
const bname=b=>b.name?`${b.id} ${b.name}`:b.id;
function maleForm(b,feld='laenge'){menueZu();formular=true;aendern=b||null;$('#ftitel').textContent=b?bname(b):'Neuer Balken';const h=$('#form .haupt'),n=b?'Speichern':'Balken anlegen';h.innerHTML=ic(b?'ja':'plus');h.title=n;h.setAttribute('aria-label',n);
 const ab=$('#formab'),rueck=!S.balken.length&&bweg,an=rueck?`${bweg} zurückholen`:'Abbrechen';ab.hidden=!S.balken.length&&!bweg;ab.innerHTML=ic(rueck?'zurueck':'nein');ab.title=an;ab.setAttribute('aria-label',an);const f=$('#form form');for(const k of['laenge','breite','hoehe'])f[k].value=b?cm(b[k+'_mm']):'';f.holzart.value=b?b.holzart:'';f.name.value=b?b.name||'':'';$('#form .fehler').textContent='';mal();f[feld].focus();if(feld==='name')f.name.select()}
$('#formab').onclick=()=>{if(!S.balken.length&&bweg)balkenZurueck();else if(aendern)oeffne(aendern.id,seite);else if(bid&&B())oeffne(bid);else if(S.balken.length)oeffne(S.balken.at(-1).id)};
$('#form').onkeydown=e=>{if(e.key==='Escape'&&S.balken.length){e.preventDefault();$('#formab').click()}};
$('#form form').onsubmit=async e=>{e.preventDefault();const f=e.target,d={holzart:f.holzart.value,name:f.name.value};$('#form .fehler').textContent='';
 for(const k of['laenge','breite','hoehe'])d[k+'_mm']=lies(f[k].value);if(aendern)d.id=aendern.id;
 try{const b=await ruf('/api/balken',d),s=aendern?seite:null;ersetze(b);oeffne(b.id,s);document.activeElement.blur()}catch(x){$('#form .fehler').textContent=x.message}};
function bildHtml(f){const src=`/foto/${bid}/${f.vorschau}`;return src}
function mal(){
 $('#wahl').innerHTML=(formular&&!aendern?'<option value="">Neuer Balken</option>':'')+S.balken.map(b=>{const n=Object.values(b.seiten).filter(fertig).length;return `<option value="${b.id}" ${b.id===bid&&!(formular&&!aendern)?'selected':''}>${esc(bname(b))}${n?` · ${n}/4`:''}</option>`}).join('');
 $('#form').hidden=!formular;const bz=$('#bzurueck');bz.hidden=!bweg;if(bweg){bz.querySelector('span').textContent=bweg;bz.title=`${bweg} zurückholen`;bz.setAttribute('aria-label',bz.title)}$('#aufnahme').hidden=formular;if(formular)return;
 const b=B(),s=SE(),p=s.plan;
 $('#seiten').innerHTML=['1','2','3','4'].map(k=>{const x=b.seiten[k];return `<button data-s="${k}" aria-pressed="${k===seite}" title="${sname(b,k)}" aria-label="${sname(b,k)}">${balken3d(b,k)}<small>${x.plan?fertig(x)?ic('ja'):fotos(x)+'/'+x.plan.mitten_mm.length:'–'}</small></button>`}).join('');
 lageMalen(b,p);
 const hat=fotos(s)>0;$('#vorschub').hidden=!p||p.mitten_mm.length<2;const vi=$('#vorschub input');if(p&&document.activeElement!==vi)vi.value=cm(p.schritt_mm);vi.disabled=hat;
 const me=$('#werte .medit');if(!me||me.dataset.id!==bid)$('#werte').innerHTML=`<dt>L × B × H</dt><dd><button id="masse" title="Maße ändern">${cm(b.laenge_mm)} × ${cm(b.breite_mm)} × ${cm(b.hoehe_mm)} cm</button></dd>`+(p?`<dt>Bildfeld</dt><dd>${cm(p.laengs_mm,0)} × ${cm(p.quer_mm,0)} cm</dd>${b.pruefung?`<dt>Maßprüfung</dt><dd title="${b.pruefung.anzahl} Messungen, ${prozent(b.pruefung.min)} bis ${prozent(b.pruefung.max)}">${prozent(b.pruefung.mittel)} · ${b.pruefung.anzahl}×</dd>`:''}`:'');
 const w=[];if(s.fehler)w.push(s.fehler);if(p){if(p.luecke)w.push('Vorschub größer als das Bildfeld, es bleibt eine Lücke.');if(p.zu_breit)w.push('Fläche breiter als das Bildfeld.');if(!p.abstand_gemessen&&!S.einstellungen.abstand_gemessen)w.push('Abstand Linse bis Rolle noch nicht gemessen (···).')}$('#warnung').textContent=w.join(' ');
 const nr=jetzt,m=p&&nr>=0?p.mitten_mm[nr]:0;let st='',kn='',kl='';
 if(!p){st='Diese Seite geht so nicht.'}
 else if(nr>=0){const vor=zeigt!==null&&nr>0?m-p.mitten_mm[nr-1]:0;
  st=s.fotos[nr]?`${ic('kamera')}<b>${cm(m)} cm</b>`:nr===0&&!fotos(s)?`${balken3d(b,seite)}${ic('kopf')}<b>${cm(m)} cm</b>`:nr===0||!s.fotos[nr-1]||zeigt!==nr-1?`${ic('kopf')}<b>${cm(m)} cm</b>`:`${ic('schieben')}<b>${cm(vor)} cm</b><small>${ic('kopf')}${cm(m)} cm</small>`;
  kn=ic('kamera');kl=s.fotos[nr]?'Foto wiederholen':`Foto ${nr+1} von ${p.mitten_mm.length} auslösen`}
 else if(!naechste()&&Object.values(B().seiten).every(fertig)){st=`${ic('ja')}<b>${b.id}</b>`;kn=ic('etikett');kl='Fotos dieses Balkens labeln'}
 else{const n=naechste();const g=n?(+n-+seite+4)%4:0;st=n?`${balken3d(b,seite)}${ic('rollen')}<b>${g*90}°</b>${balken3d(b,n)}`:`${ic('ja')}<b>${b.id}</b>`;kn=n?ic('kamera'):ic('plus');kl=n?`Weiter mit ${sname(b,n)}`:'Neuer Balken'}
 $('#schritt').innerHTML=st;$('#los span').innerHTML=kn;$('#los').title=kl;$('#los').setAttribute('aria-label',kl);$('#los').hidden=!kn;$('#los').disabled=laeuft;
 $('#abschnitte').innerHTML=p?p.mitten_mm.map((x,i)=>{const f=s.fotos[i];return `<button data-i="${i}" aria-pressed="${i===zeigt}" class="${i===nr?'jetzt':''}" aria-label="Abschnitt ${i+1}${f?'':', noch kein Foto'}">${f?`<canvas data-src="${bildHtml(f)}"></canvas>`:S.app&&i===nr?'<canvas class="lk"></canvas>':''}<span>${cm(x,0)} cm</span></button>`}).join(''):'';
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
 if(schneide){inf.innerHTML=`<span>Rahmen um den Boxboden ziehen</span><span class="re">${schneide.r?kw('zuok','ja','Übernehmen','prim'):''}${S.einstellungen.zuschnitt?kw('zuganz','ganz','Ganzes Bild'):''}${kw('zuab','nein','Abbrechen')}</span>`}
 const sch=kw('zuschnitt','zuschnitt','Zuschnitt');
 if(!f){el.dataset.src='';const u=geloescht&&geloescht.balken===bid&&geloescht.seite===seite&&geloescht.nr===zeigt?kw('zurueck','zurueck','Löschen rückgängig'):'';
  if(S.app){leinwand().setAttribute('aria-label','Live-Bild');live()}else el.innerHTML='<span>Noch kein Foto</span>';
  if(!schneide)inf.innerHTML=`<span class="re">${u}${S.app?kw('drehen','drehen','Drehen')+sch:''}</span>`;return}
 const src=bildHtml(f),k=src+JSON.stringify(ausschnitt());if(el.dataset.src!==k||!el.querySelector('canvas')){el.dataset.src=k;hole(src,i=>{if(el.dataset.src!==k)return;if(!i){el.innerHTML='<span>Foto gespeichert, Vorschau nicht möglich</span>';return}const c=leinwand();c.setAttribute('aria-label',`${bid}, Seite ${seite}, Abschnitt ${zeigt+1}`);zeichne(c,i,ausschnitt(),2400);ueber()})}else leinwand();
 if(!schneide)inf.innerHTML=mess?messLeiste():`${geprueft?`<span class="gepr">${ic('ja')}${laenge(geprueft.foto_mm)}${ic('mass')}${laenge(geprueft.zollstock_mm)}<b>${prozent(geprueft.abweichung)}</b></span>${kw('pruefweg','zurueck','Rückgängig')}`:`<b>Abschnitt ${zeigt+1}</b><span>${f.breite_px?`${f.breite_px} × ${f.hoehe_px} px · `:''}${f.px_je_mm?f.px_je_mm.toLocaleString('de-DE')+' px/mm · ':''}${f.mb.toLocaleString('de-DE')} MB${f.kamera&&f.kamera.dauer?' · '+belicht(f.kamera):''}</span>`}<span class="re">${kw('drehen','drehen','Drehen')}${sch}${kw('messen','mass','Messen')}${kw('nochmal','kamera','Nochmal')}${kw('weg','weg','Löschen')}</span>`;
 ueber();const st=$('#strecke');if(st){st.value=mess.wert||'';abweichung();st.focus()}}
/* Messen: zwei Punkte, die Länge steht sofort da. Mit dem Zollstockmaß wird daraus eine Prüfung (Maßstab bleibt)
   oder, solange der Bildwinkel nur angenommen ist, der neue Maßstab */
const messAnteil=(a,b)=>{const z=ausschnitt();return Math.hypot(a[0]-b[0],a[1]-b[1])*(z?z[2]:1)};
const messMm=(a,b)=>{const p=SE().plan;return messAnteil(a,b)*(p.voll_mm||p.laengs_mm)};
const zollstock=()=>{const v=lies($('#strecke')?.value||'');return v===null?null:einheit(messMm(...mess.p))==='mm'?v/10:v};
function messLeiste(){if(mess.p.length<2)return `<span class="re">${kw('messab','nein','Abbrechen')}</span>`;
 const mm=messMm(...mess.p),gem=S.einstellungen.faktor_gemessen;
 return `<b title="Im Foto">${gem?'':'≈ '}${laenge(mm)}</b><label class="zoll" title="Zollstock">${ic('mass')}<span><input id="strecke" aria-label="Zollstock" inputmode="decimal" autocomplete="off" aria-describedby="abw">${einheit(mm)}</span></label><output id="abw"></output><span class="re">${gem?kw('pruefok','ja','Prüfung speichern','prim')+kw('messok','skala','Als Maßstab übernehmen'):kw('messok','skala','Als Maßstab übernehmen','prim')}${kw('messab','nein','Abbrechen')}</span>`}
function abweichung(){const o=$('#abw'),z=zollstock();if(!o)return;if(mess)mess.wert=$('#strecke').value;const a=z?(messMm(...mess.p)/z-1)*100:0;o.textContent=z?prozent(a):''}
async function pruefOk(){const z=zollstock();if(!z){$('#afehler').textContent='Maß vom Zollstock eingeben.';return}
 try{const b=await ruf('/api/kontrolle',{balken:bid,seite,nr:zeigt,anteil:messAnteil(...mess.p),zollstock_mm:z});ersetze(b);geprueft=b.kontrollen.at(-1);mess=null;$('#afehler').textContent='';mal()}catch(x){$('#afehler').textContent=x.message}}
async function pruefWeg(){try{ersetze(await ruf('/api/kontrolle',{balken:bid,weg:true}));geprueft=null;$('#afehler').textContent='';mal()}catch(x){$('#afehler').textContent=x.message}}
function ueber(){messMalen();pruefe();rasterText()}
function rasterText(){$('#rw')?.remove();const R=$('#bild canvas')&&rasterAn&&(mess||schneide||liveZeigt())?rasterWeite():null;if(R)$('#bildinfo').insertAdjacentHTML('afterbegin',`<span id="rw">Raster ${S.einstellungen.faktor_gemessen?"":"etwa "}${cm(R.w)} cm</span>`)}
addEventListener('resize',()=>{if(bid&&!formular)ueber()});
function rahmen(){const c=$('#bild canvas'),el=$('#bild'),a=c.width/c.height,w=el.clientWidth,h=el.clientHeight,b=Math.min(w,h*a);return{b,h:b/a,x:(w-b)/2,y:(h-b/a)/2}}
/* Raster zum Ausrichten: im Live-Bild, beim Messen und beim Zuschnitt, an der Bildmitte verankert. Weite in cm, wenn der Plan sie hergibt */
const liveZeigt=()=>!!S.app&&!(zeigt!==null&&SE().fotos[zeigt]);
function rasterWeite(){const p=SE().plan;if(!p)return null;const mm=schneide?p.voll_mm:p.laengs_mm;return{mm,w:rWeite||[10,20,50,100].find(w=>mm/w<=16)||200}}
function raster(r,nurGitter){const R=rasterWeite(),s=R?R.w/R.mm*r.b:r.b/12,mx=r.x+r.b/2,my=r.y+r.h/2,e=16,x2=r.x+r.b,y2=r.y+r.h;let d='';
 if(rasterAn&&(R||!nurGitter))for(let i=-Math.floor(r.b/2/s);i*s<r.b/2;i++)for(let j=-Math.floor(r.h/2/s);j*s<r.h/2;j++)if(i||j)d+=`M${mx+i*s-3} ${my+j*s}h6M${mx+i*s} ${my+j*s-3}v6`;
 const achse=`M${mx} ${r.y}v${r.h}M${r.x} ${my}h${r.b}`,ecken=`M${r.x+6} ${r.y+6+e}v${-e}h${e}M${x2-6-e} ${r.y+6}h${e}v${e}M${x2-6} ${y2-6-e}v${e}h${-e}M${r.x+6+e} ${y2-6}h${-e}v${-e}`,ziel=`M${mx-14} ${my}h9M${mx+5} ${my}h9M${mx} ${my-14}v9M${mx} ${my+5}v9`;
 if(nurGitter)return `<g fill="none"><path d="${d}" stroke="#000" stroke-opacity=".35" stroke-width="3"/><path d="${d}" stroke="#00e0ea" stroke-opacity=".6"/></g>`;
 return `<g fill="none"><path d="${d}" stroke="#000" stroke-opacity=".35" stroke-width="3"/><path d="${d}" stroke="#00e0ea" stroke-opacity=".6"/><path d="${achse}" stroke="#00e0ea" stroke-opacity=".55" stroke-dasharray="2 6"/><g style="filter:drop-shadow(0 0 3px #ff2bd6)"><path d="${ecken}" stroke="#ff2bd6" stroke-opacity=".8" stroke-width="1.5"/><path d="${ziel}" stroke="#ff2bd6" stroke-width="1.5"/></g></g>`}
/* Die Messlinie rastet bis 6 Grad an der Waagerechten oder Senkrechten ein, schräg messen bleibt möglich */
const einrasten=(a,q)=>{const x=Math.abs(q[0]-a[0]),y=Math.abs(q[1]-a[1]),t=Math.tan(6*Math.PI/180);return y<=x*t?[q[0],a[1]]:x<=y*t?[a[0],q[1]]:q};
const messPunkt=e=>{const k=$('#bild').getBoundingClientRect(),r=rahmen(),q=[Math.min(1,Math.max(0,(e.clientX-k.left-r.x)/r.b)),Math.min(r.h/r.b,Math.max(0,(e.clientY-k.top-r.y)/r.b))];return mess.p.length?einrasten(mess.p[0],q):q};
function messMalen(){$('#bild svg')?.remove();zollLeiste();const c=$('#bild canvas'),aus=mess||schneide||liveZeigt();if(!c||!(aus||rasterAn||zoll.an))return;const r=rahmen();let in_='';
 if(mess){const alle=mess.p.length===1&&mess.m?[mess.p[0],mess.m]:mess.p,p=alle.map(q=>[r.x+q[0]*r.b,r.y+q[1]*r.b]);in_=(p.length>1?`<path d="M${p[0]}L${p[1]}" stroke="#000" stroke-width="4"/><path d="M${p[0]}L${p[1]}" stroke="#00e0ea" stroke-width="2"/>`:'')+p.map(q=>`<circle cx="${q[0]}" cy="${q[1]}" r="6" fill="none" stroke="#00e0ea" stroke-width="2"/>`).join('');
  if(p.length>1&&Math.hypot(p[1][0]-p[0][0],p[1][1]-p[0][1])>12){const rechts=Math.max(p[0][0],p[1][0]),eng=rechts+90>r.x+r.b,y=Math.min(p[0][1],p[1][1])-10;in_+=`<text x="${eng?rechts-12:rechts+12}" y="${y}" text-anchor="${eng?'end':'start'}" class="mlang">${S.einstellungen.faktor_gemessen?'':'≈ '}${laenge(messMm(...alle))}</text>`}
  if(mess.m&&mess.p.length<2){const x=r.x+mess.m[0]*r.b,y=r.y+mess.m[1]*r.b;in_+=`<path d="M${x} ${r.y}v${r.h}M${r.x} ${y}h${r.b}" stroke="#00e0ea" stroke-opacity=".7" stroke-dasharray="4 4"/>`}}
 else if(schneide&&schneide.r){const[x,y,b,h]=schneide.r;in_=`<path fill="#000b" fill-rule="evenodd" d="M0 0h9999v9999H0zM${r.x+x*r.b} ${r.y+y*r.h}h${b*r.b}v${h*r.h}h${-b*r.b}z"/><rect x="${r.x+x*r.b}" y="${r.y+y*r.h}" width="${b*r.b}" height="${h*r.h}" fill="none" stroke="#00e0ea" stroke-width="2"/>`}
 $('#bild').insertAdjacentHTML('beforeend',`<svg>${raster(r,!aus)}${in_}${mess||schneide?'':zollSvg(r)}</svg>`)}
const punkt=e=>{const k=$('#bild').getBoundingClientRect(),r=rahmen();return[Math.min(1,Math.max(0,(e.clientX-k.left-r.x)/r.b)),Math.min(1,Math.max(0,(e.clientY-k.top-r.y)/r.h))]};
$('#bild').onclick=e=>{if(!mess||mess.p.length>1||!$('#bild canvas'))return;mess.p.push(messPunkt(e));mess.m=null;mal()};
$('#bild').onpointerdown=e=>{if(!schneide||!$('#bild canvas'))return;e.preventDefault();$('#bild').setPointerCapture(e.pointerId);schneide.a=punkt(e)};
$('#bild').onpointermove=e=>{if(mess){if(mess.p.length<2&&$('#bild canvas')){mess.m=messPunkt(e);messMalen()}return}if(!schneide||!schneide.a)return;const p=punkt(e),a=schneide.a;schneide.r=[Math.min(a[0],p[0]),Math.min(a[1],p[1]),Math.abs(a[0]-p[0]),Math.abs(a[1]-p[1])];messMalen()};
$('#bild').onpointerup=$('#bild').onpointercancel=()=>{if(schneide&&schneide.a){schneide.a=null;mal()}};
async function schnitt(r){if(r&&winkel)r=[1-r[0]-r[2],1-r[1]-r[3],r[2],r[3]].map(v=>Math.max(0,v));try{S=await ruf('/api/zuschnitt',{zuschnitt:r});schneide=null;$('#afehler').textContent=fotos(SE())?'Gilt für Seiten ohne Fotos. Diese Seite hat schon welche.':'';jetzt=offen();mal()}catch(x){$('#afehler').textContent=x.message}}
async function messOk(){const z=zollstock();if(!z){$('#afehler').textContent='Maß vom Zollstock eingeben.';return}try{S=await ruf('/api/massstab',{balken:bid,seite,anteil:messAnteil(...mess.p),strecke_mm:z});mess=null;$('#afehler').textContent='';mal()}catch(x){$('#afehler').textContent=x.message}}
$('#bildinfo').onclick=e=>{const id=e.target.closest('button')?.id;if(!id||laeuft)return;if(id==='drehen'){dreh.w=(winkel+180)%360;try{localStorage.setItem('aufnahme-dreh',JSON.stringify(dreh))}catch(x){}mal()}
 if(id==='messen'){mess={p:[]};geprueft=null;mal()}if(id==='pruefok')pruefOk();if(id==='pruefweg')pruefWeg();if(id==='messab'){mess=null;$('#afehler').textContent='';mal()}if(id==='messok')messOk();
 if(id==='zuschnitt'){schneide={r:null};mess=null;$('#bild').dataset.src='';mal()}if(id==='zuab'){schneide=null;mal()}if(id==='zuok')schnitt(schneide.r);if(id==='zuganz')schnitt(null);
 if(id==='nochmal'){jetzt=zeigt;document.activeElement.blur();mal()}if(id==='weg')loesche();if(id==='zurueck')zurueck()};
$('#bildinfo').onkeydown=e=>{if(e.key==='Enter'&&e.target.id==='strecke')S.einstellungen.faktor_gemessen?pruefOk():messOk();if(e.key==='Escape'&&mess){mess=null;mal()}};
$('#bildinfo').oninput=e=>{if(e.target.id==='strecke')abweichung()};
const belicht=k=>`${k.dauer<.5?'1/'+Math.round(1/k.dauer):k.dauer.toFixed(1)} s · ISO ${Math.round(k.iso)}`;
let lz=0;function live(){const n=++lz,i=new Image();i.onload=()=>{if(n!==lz||formular||!S.app)return;const k=$('#abschnitte .jetzt .lk');if(k)zeichne(k,i,SE().plan&&SE().plan.zuschnitt,300);const c=$('#bild canvas');if(c&&!(zeigt!==null&&SE().fotos[zeigt])){zeichne(c,i,ausschnitt(),2400);ueber()}};i.src='/live.jpg?'+Date.now()+rasterFuersHandy()}
/* Das Raster der iPhone-App folgt dem am Mac: gleiche Weite, bezogen aufs ganze Bild (die App zeigt keinen Zuschnitt) */
function rasterFuersHandy(){const R=rasterAn&&bid&&B()&&SE()&&rasterWeite(),p=R&&SE().plan;return R?`&r=${(R.w/(p.voll_mm||p.laengs_mm)).toFixed(5)}&w=${R.w}&g=${S.einstellungen.faktor_gemessen?1:0}`:''}
setInterval(()=>{if(S.app&&!formular&&!document.hidden)live()},500);
/* Anteil ausgebrannter Pixel unter den nicht dunklen (das Holz) */
function ausgebrannt(q){const c=document.createElement('canvas');c.width=300;c.height=225;const x=c.getContext('2d',{willReadFrequently:true});x.drawImage(q,0,0,300,225);const d=x.getImageData(0,0,300,225).data;let n=0,w=0;for(let i=0;i<d.length;i+=4){const m=Math.max(d[i],d[i+1],d[i+2]);if(m<110)continue;n++;if(m>=253)w++}return n?w/n:0}
function pruefe(){$('#brand')?.remove();const c=$('#bild canvas');if(!c||mess||schneide)return;const a=ausgebrannt(c);if(a>.01)$('#bildinfo').insertAdjacentHTML('afterbegin',`<span id="brand" class="warn">${Math.round(a*100)} % überbelichtet</span>`)}
function appMalen(){const a=S.app;$('#kam').hidden=!a;if(!a)return;$('#kam output').textContent=a.dauer?belicht(a):'–';$$('#kam [data-m]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.m===a.modus))}
$('#kam').onclick=async e=>{const b=e.target.closest('button');if(!b)return;b.blur();try{await ruf('/api/kamera',b.dataset.m?{art:'modus',wert:b.dataset.m}:b.dataset.ev?{art:'ev',wert:+b.dataset.ev}:{art:'einmessen'});$('#afehler').textContent=''}catch(x){$('#afehler').textContent=x.message}};
async function los(){if(laeuft||formular||mess||schneide)return;const s=SE();if(!s.plan)return;
 if(jetzt<0){const n=naechste();if(!n&&Object.values(B().seiten).every(fertig)){location.href='/labeln?balken='+bid;return}if(n){seite=n;seiteAuf()}else maleForm();return}
 await nimm(()=>ruf('/api/ausloesen',{balken:bid,seite,nr:jetzt}))}
async function loesche(){if(laeuft||formular||mess||schneide||zeigt===null||!SE().fotos[zeigt])return;const z={balken:bid,seite,nr:zeigt};document.activeElement.blur();await nimm(()=>ruf('/api/loeschen',z),true);if(!SE().fotos[z.nr]){geloescht=z;jetzt=z.nr;zeigt=z.nr;mal()}}
async function zurueck(){if(laeuft||!geloescht)return;const z=geloescht;document.activeElement.blur();laeuft=true;try{const r=await ruf('/api/zurueck',z);ersetze(r.balken);geloescht=null;jetzt=offen();zeigt=z.nr;$('#afehler').textContent=''}catch(x){$('#afehler').textContent=x.message}laeuft=false;mal()}
async function nimm(tu,loescht){const ziel=[bid,seite,jetzt];laeuft=true;$('#afehler').textContent='';if(!loescht){geloescht=null;mal()}
 try{const r=await tu();ersetze(r.balken);if(bid===ziel[0]&&seite===ziel[1]){zeigt=ziel[2];jetzt=offen()}}catch(x){$('#afehler').textContent=x.message}
 laeuft=false;mal()}
$('#los').onclick=()=>{$('#los').blur();los()};
addEventListener('keydown',e=>{if(e.code!=='Space'||e.repeat||$('#dlg').open||formular||/^(INPUT|SELECT|BUTTON)$/.test(e.target.tagName))return;e.preventDefault();los()});
addEventListener('keydown',e=>{if($('#dlg').open||/^(INPUT|SELECT)$/.test(e.target.tagName)||formular)return;if((e.key==='Delete'||e.key==='Backspace')&&!e.repeat){e.preventDefault();loesche()}if(e.key==='z'&&(e.metaKey||e.ctrlKey)){if(geloescht&&geloescht.balken===bid&&geloescht.seite===seite){e.preventDefault();zurueck()}else if(bweg){e.preventDefault();balkenZurueck()}}});
$('#seiten').onclick=e=>{const k=e.target.closest('button');if(!k||laeuft)return;seite=k.dataset.s;seiteAuf()};
$('#abschnitte').onclick=e=>{const k=e.target.closest('button');if(!k||laeuft)return;const i=+k.dataset.i;if(SE().fotos[i]){zeigt=i;jetzt=offen()}else{jetzt=i;zeigt=null}mess=schneide=geprueft=null;mal()};
$('#vorschub input').onchange=async e=>{const i=e.target;try{ersetze(await ruf('/api/vorschub',{balken:bid,seite,mm:i.value.trim()?lies(i.value):0}));i.blur();$('#afehler').textContent='';seiteAuf()}catch(x){$('#afehler').textContent=x.message}};
/* Maße direkt rechts ändern: Klick auf L × B × H macht drei Felder daraus. Enter oder Wegklicken speichert, Esc bricht ab */
const MF=['laenge','breite','hoehe'];
function masseAuf(k){if(laeuft||!B())return;const b=B(),dd=$('#masse').parentElement;dd.className='medit';dd.dataset.id=b.id;
 dd.innerHTML=MF.map(f=>`<input name="${f}" value="${cm(b[f+'_mm'])}" inputmode="decimal" autocomplete="off" aria-label="${{laenge:'Länge',breite:'Breite',hoehe:'Höhe'}[f]} in cm">`).join('<span>×</span>')+'<span>cm</span>';
 const e=dd.querySelector(`[name=${k||'laenge'}]`);e.focus();e.select()}
function masseZu(){const dd=$('#werte .medit');if(dd){dd.className='';dd.innerHTML='';}mal()}
async function masseSpeichern(){const dd=$('#werte .medit');if(!dd||dd.dataset.l)return;const b=S.balken.find(x=>x.id===dd.dataset.id);if(!b)return;const d={id:b.id,holzart:b.holzart||'',name:b.name||''};
 for(const f of MF)d[f+'_mm']=lies(dd.querySelector(`[name=${f}]`).value);if(MF.every(f=>d[f+'_mm']===b[f+'_mm'])){masseZu();return}
 dd.dataset.l='1';try{ersetze(await ruf('/api/balken',d));$('#afehler').textContent='';dd.className='';seiteAuf()}catch(x){$('#afehler').textContent=x.message;delete dd.dataset.l;const f=MF.find(f=>x.message.startsWith({laenge:'Länge',breite:'Breite',hoehe:'Höhe'}[f]))||'laenge',e=dd.querySelector(`[name=${f}]`);e.focus();e.select()}}
$('#werte').onclick=e=>{const k=e.target.closest('#masse');if(!k)return;const r=k.getBoundingClientRect(),x=(e.clientX-r.left)/r.width;masseAuf(e.detail?MF[Math.min(2,Math.floor(x*3))]:'laenge')};
$('#werte').onkeydown=e=>{if(!e.target.closest('.medit'))return;if(e.key==='Enter'){e.preventDefault();masseSpeichern()}if(e.key==='Escape'){e.preventDefault();masseZu();$('#masse')?.focus()}};
$('#werte').addEventListener('focusout',e=>{const dd=$('#werte .medit');if(dd&&!dd.contains(e.relatedTarget))setTimeout(()=>{if(!dd.contains(document.activeElement))masseSpeichern()},0)});
$('#wahl').onchange=e=>{if(laeuft||!e.target.value)return mal();oeffne(e.target.value);e.target.blur()};$('#neu').onclick=()=>{if(!laeuft)maleForm()};
/* ··· am Balken: Seltenes (Maße, Name, Löschen). Löschen legt in den Papierkorb, Rückgängig daneben statt Nachfrage */
function menueZu(){$('#bmenue').hidden=true;$('#bmehr').setAttribute('aria-expanded','false')}
$('#bmehr').onclick=()=>{const m=$('#bmenue'),auf=m.hidden;m.hidden=!auf;$('#bmehr').setAttribute('aria-expanded',String(auf));if(auf)m.querySelector('button').focus()};
$('#bmenue').onclick=e=>{const t=e.target.closest('button')?.dataset.tu;if(!t||laeuft)return;menueZu();if(t==='bearbeiten')maleForm(B());if(t==='weg')balkenWeg()};
$('#bmenue').onkeydown=e=>{const k=[...$$('#bmenue button')],i=k.indexOf(document.activeElement);if(e.key==='Escape'){menueZu();$('#bmehr').focus()}
 if(e.key==='ArrowRight'||e.key==='ArrowDown'){e.preventDefault();k[(i+1)%k.length].focus()}if(e.key==='ArrowLeft'||e.key==='ArrowUp'){e.preventDefault();k[(i+k.length-1)%k.length].focus()}};
addEventListener('pointerdown',e=>{if(!e.target.closest('#bwahl'))menueZu()});
async function balkenWeg(){if(laeuft||!B())return;const id=bid,i=S.balken.findIndex(b=>b.id===id);$('#afehler').textContent='';
 try{await ruf('/api/balken-weg',{balken:id});S.balken.splice(i,1);bweg=id;geloescht=null;const n=S.balken[Math.max(0,i-1)];n?oeffne(n.id):maleForm();if(n)$('#bzurueck').focus()}catch(x){$('#afehler').textContent=x.message}}
async function balkenZurueck(){if(laeuft||!bweg)return;const id=bweg;try{const b=await ruf('/api/balken-zurueck',{balken:id});bweg=null;ersetze(b);S.balken.sort((a,c)=>a.id.localeCompare(c.id));oeffne(id);$('#afehler').textContent=''}catch(x){$('#afehler').textContent=x.message;if(formular)$('#form .fehler').textContent=x.message}}
$('#bzurueck').onclick=balkenZurueck;
function handyMalen(){const h=$('#handy');h.className=S.handy?'da':'';const n=S.handy?'iPhone verbunden':'iPhone nicht verbunden';h.title=n;h.setAttribute('aria-label',n)}
function dlg(){const a=S.adressen,m=S.einstellungen;$('#abstand').kr.value=cm(m.kamera_rolle_mm);$('#abstand .fehler').textContent='';
 $('#winkel').textContent=m.faktor_gemessen?'Gemessen':'Angenommen (24 mm)';
 $('#appadr').innerHTML=a.map(x=>`<code>${esc(x)}</code>`).join(a.length>1?'<span class="leise">geht die erste nicht:</span>':'');const u=t=>a.map(x=>`<code>${esc(x+t)}</code>`).join(a.length>1?'<span class="leise">geht die erste nicht:</span>':'');

 if(!$('#dlg').open)$('#dlg').showModal()}
$('#einst').onclick=$('#handy').onclick=dlg;$('.zu').onclick=()=>$('#dlg').close();$('#dlg').onclose=()=>document.activeElement.blur();
$('#abstand').onsubmit=async e=>{e.preventDefault();try{S=await ruf('/api/einstellungen',{kamera_rolle_mm:lies(e.target.kr.value)});$('#dlg').close();if(bid&&!formular)seiteAuf()}catch(x){$('#abstand .fehler').textContent=x.message}};
$('#datei').onchange=async e=>{const d=e.target.files[0];e.target.value='';if(!d||!bid||formular)return;$('#dlg').close();if(jetzt<0){$('#afehler').textContent='Erst einen Abschnitt wählen.';return}await nimm(()=>ruf(`/api/datei?balken=${bid}&seite=${seite}&nr=${jetzt}`,d))};
async function puls(){if(!laeuft)try{const n=await ruf('/api/stand');if(!laeuft){const vor=!!S.app;S.handy=n.handy;S.app=n.app;if(vor!==!!S.app&&!formular&&bid&&!(zeigt!==null&&SE().fotos[zeigt]))mal();appMalen();S.adressen=n.adressen;handyMalen();if(n.hinweis&&n.hinweis!==S.hinweis)$('#afehler').textContent=n.hinweis;S.hinweis=n.hinweis}}catch(e){S.handy=false;handyMalen();$('#handy').title='Programm beendet';$('#afehler').textContent='Das Programm auf dem Mac antwortet nicht.'}setTimeout(puls,1500)}
ruf('/api/stand').then(n=>{S=n;const w=new URLSearchParams(location.search).get('balken'),b=S.balken.find(x=>x.id===w)||S.balken.at(-1);b?oeffne(b.id):maleForm();handyMalen();puls()}).catch(e=>{document.body.append(e.message)});

/* Raster und Zollstock (Jan 26.11.2026: „überall die Möglichkeit, ein Raster einzuschalten, mit verschiedener Größe,
   das betrifft auch den Zollstock“). Raster an/aus und Weite merkt sich der Browser; ohne gewählte Weite gilt die
   automatische. Zollstock: zwei Klicks setzen, Enden ziehen dreht und verlängert, Band ziehen verschiebt. Teilung
   aus dem Plan der Seite (≈ solange der Bildwinkel nur angenommen ist). Auf einem Foto: echte Länge eintippen, Haken
   übernimmt sie als Maßstab (wie Messen). Punkte in Anteilen der Bildbreite wie beim Messen. */
let rasterAn=true,rWeite=null;const zoll={an:false,a:null,b:null,setzen:null,maus:null,zug:null};
try{const x=localStorage.getItem('aufnahme-raster');if(x)rasterAn=x==='1';const w=+localStorage.getItem('aufnahme-weite');if([10,20,50,100].includes(w))rWeite=w}catch(e){}
const rasterMerken=()=>{try{localStorage.setItem('aufnahme-raster',rasterAn?'1':'0');if(rWeite)localStorage.setItem('aufnahme-weite',String(rWeite))}catch(e){}};
const fotoZeigt=()=>!!(bid&&B()&&SE()&&zeigt!==null&&SE().fotos[zeigt]);
function zollSvg(r){if(!zoll.an)return'';const P=q=>[r.x+q[0]*r.b,r.y+q[1]*r.b],G='#f2c230',D='#111';
 if(zoll.setzen){if(!zoll.setzen.length)return'';const a=P(zoll.setzen[0]),m=zoll.maus?P(zoll.maus):a;return`<path d="M${a}L${m}" stroke="${D}" stroke-width="4"/><path d="M${a}L${m}" stroke="${G}" stroke-width="2"/><circle cx="${a[0]}" cy="${a[1]}" r="5" fill="${G}" stroke="${D}" stroke-width="1.5"/>`}
 if(!zoll.a)return'';const A=P(zoll.a),E=P(zoll.b),n=Math.hypot(E[0]-A[0],E[1]-A[1])||1e-9,u=[(E[0]-A[0])/n,(E[1]-A[1])/n],v=[u[1],-u[0]],Q=(t,h)=>[A[0]+u[0]*t+v[0]*h,A[1]+u[1]*t+v[1]*h];
 const R=rasterWeite(),mmPx=R?R.mm/r.b:null,ang=Math.atan2(u[1],u[0])*180/Math.PI,dreh=ang>90||ang<-90?ang+180:ang,ung=S.einstellungen.faktor_gemessen?'':'≈ ';let g='';
 if(mmPx){const pm=1/mmPx,mmL=n*mmPx;g+=`<path d="M${[Q(0,0),Q(n,0),Q(n,26),Q(0,26)].join('L')}Z" fill="${G}" fill-opacity=".5" stroke="${D}"/>`;
  const st=pm>=4?1:pm*5>=5?5:10,zi=[1,2,5,10,20,50].find(k=>k*10*pm>=26)||100;let t='',z='';
  for(let mm=0;mm<=mmL+1e-6;mm+=st){const k=Math.round(mm),l=k%10==0?13:k%5==0?9:5;t+=`M${Q(mm*pm,0)}L${Q(mm*pm,l)}`;if(k%10==0&&k>0&&(k/10)%zi==0&&(mmL-mm)*pm>20){const q=Q(mm*pm,20);z+=`<text x="${q[0]}" y="${q[1]}" transform="rotate(${ang} ${q[0]} ${q[1]})" class="zz">${k/10}</text>`}}
  g+=`<path d="${t}" stroke="#1b1b1b" fill="none"/>${z}`;{const f=$('#zl');if(f&&document.activeElement!==f)f.placeholder=cm(mmL)}const q=Q(n/2,-14);g+=`<text x="${q[0]}" y="${q[1]}" transform="rotate(${dreh} ${q[0]} ${q[1]})" class="zl">${ung}${laenge(mmL)}</text>`}
 else g+=`<path d="M${A}L${E}" stroke="${D}" stroke-width="4"/><path d="M${A}L${E}" stroke="${G}" stroke-width="2"/>`;
 for(const q of[A,E])g+=`<circle cx="${q[0]}" cy="${q[1]}" r="5" fill="${G}" stroke="${D}" stroke-width="1.5"/>`;return g}
function zollLeiste(){const k=$('#rasterk');if(!k)return;k.setAttribute('aria-pressed',rasterAn);const R=bid&&B()&&SE()&&rasterWeite();$('#weiten').hidden=!rasterAn||!R;
 for(const b of $$('#weiten button'))b.setAttribute('aria-pressed',!!R&&+b.dataset.w===R.w);$('#zollk').setAttribute('aria-pressed',zoll.an);
 $('#einm').hidden=!zoll.an||!zoll.a||!!zoll.setzen||!fotoZeigt()||!SE().plan;$('#bild').classList.toggle('zollsetzen',!!(zoll.an&&zoll.setzen));$('#bild').classList.toggle('zollan',zoll.an)}
function zollAn(an){zoll.an=an;zoll.setzen=an&&!zoll.a?[]:null;zoll.maus=zoll.zug=null;ueber()}
$('#rasterk').onclick=()=>{rasterAn=!rasterAn;rasterMerken();ueber()};
$('#weiten').onclick=e=>{const b=e.target.closest('button');if(!b)return;const l=$$('#weiten button'),eng=matchMedia('(max-width:700px)').matches&&b.getAttribute('aria-pressed')==='true';rWeite=+(eng?l[(l.indexOf(b)+1)%l.length]:b).dataset.w;rasterMerken();ueber();if(eng)$('#weiten [aria-pressed=true]').focus()};
$('#zollk').onclick=()=>zollAn(!zoll.an);
const zpunkt=e=>{const k=$('#bild').getBoundingClientRect(),r=rahmen();return[Math.min(1,Math.max(0,(e.clientX-k.left-r.x)/r.b)),Math.min(r.h/r.b,Math.max(0,(e.clientY-k.top-r.y)/r.b))]};
$('#bild').addEventListener('pointerdown',e=>{if(!zoll.an||mess||schneide||!$('#bild canvas')||e.button)return;const q=zpunkt(e),r=rahmen();
 if(zoll.setzen){zoll.setzen.push(q);if(zoll.setzen.length===2){[zoll.a,zoll.b]=zoll.setzen;zoll.setzen=null;zoll.maus=null;ueber();if(!$('#einm').hidden)$('#zl').focus()}else messMalen();return}
 if(!zoll.a)return;const ab=(p,o)=>Math.hypot((p[0]-o[0])*r.b,(p[1]-o[1])*r.b),fang=matchMedia('(pointer:coarse)').matches?24:14;
 const ende=ab(q,zoll.a)<=fang?'a':ab(q,zoll.b)<=fang?'b':null,L=ab(zoll.a,zoll.b)||1,u=[(zoll.b[0]-zoll.a[0])*r.b/L,(zoll.b[1]-zoll.a[1])*r.b/L],w=[(q[0]-zoll.a[0])*r.b,(q[1]-zoll.a[1])*r.b],t=w[0]*u[0]+w[1]*u[1],h=w[0]*u[1]-w[1]*u[0];
 if(!ende&&!(t>=0&&t<=L&&h>=-8&&h<=30))return;e.preventDefault();$('#bild').setPointerCapture(e.pointerId);zoll.zug={e:ende||'ab',a:q,s:[[...zoll.a],[...zoll.b]]}});
$('#bild').addEventListener('pointermove',e=>{if(!zoll.an||mess||schneide)return;if(zoll.setzen){zoll.maus=zpunkt(e);if(zoll.setzen.length)messMalen();return}if(!zoll.zug)return;
 const q=zpunkt(e),z=zoll.zug,dx=q[0]-z.a[0],dy=q[1]-z.a[1];if(z.e==='ab'){zoll.a=[z.s[0][0]+dx,z.s[0][1]+dy];zoll.b=[z.s[1][0]+dx,z.s[1][1]+dy]}else if(z.e==='a')zoll.a=[z.s[0][0]+dx,z.s[0][1]+dy];else zoll.b=[z.s[1][0]+dx,z.s[1][1]+dy];messMalen()});
for(const t of['pointerup','pointercancel'])$('#bild').addEventListener(t,()=>{zoll.zug=null});
async function zollOk(){const mm=lies($("#zl").value);if(!mm||!zoll.a){$("#zl").focus();return}
 try{S=await ruf('/api/massstab',{balken:bid,seite,anteil:messAnteil(zoll.a,zoll.b),strecke_mm:mm});$('#zl').blur();$('#afehler').textContent='';mal()}catch(x){$('#afehler').textContent=x.message}}
$('#zlok').onclick=zollOk;$('#zl').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();zollOk()}if(e.key==='Escape'){e.target.value='';e.target.blur()}};
addEventListener('keydown',e=>{if($('#dlg').open||formular||e.metaKey||e.ctrlKey||e.altKey||/^(INPUT|SELECT)$/.test(e.target.tagName))return;const k=e.key.toLowerCase();
 if(k==='r'){rasterAn=!rasterAn;rasterMerken();ueber()}else if(k==='l')zollAn(!zoll.an);else if(e.key==='Escape'&&zoll.setzen)zollAn(false)});
