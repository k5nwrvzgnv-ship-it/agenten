'use strict';
// Galerie: alle Balken, neueste zuerst, in den drei Teilen der Aufteilung (kette.teile). Ziehen ordnet zu,
// Pfeil links/rechts auf einer Karte auch. Balken, mit denen schon trainiert wurde, bleiben (gesperrt).
const $=s=>document.querySelector(s),esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const TEILE=['train','val','test'],NAME={train:'Training',val:'Prüfung',test:'Nur Test'};
const SCHLOSS='<svg class="ic" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="5" y="11" width="14" height="10" rx="1"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>';
const BALKEN='<svg viewBox="0 0 48 48" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 20l12-8h24l-12 8zM6 20v14h24V20M30 34l12-8V12"/></svg>';
let G=[],zug=null;
const cm=mm=>(mm/10).toLocaleString('de-DE',{maximumFractionDigits:1});

async function ruf(weg,daten){let a;try{a=await fetch(weg,daten===undefined?{}:{method:'POST',headers:{'X-Aufnahme':'1'},body:JSON.stringify(daten)})}
 catch(e){throw Error('Das Programm auf dem Mac antwortet nicht. Im Terminal neu starten.')}
 let j={};try{j=await a.json()}catch(e){}if(!a.ok)throw Error(j.fehler||`Fehler ${a.status}`);return j}

function karte(b){
 // Seitenstriche nur, wenn etwas fehlt: ein vollständiger Balken bleibt ruhig
 const gut=n=>b.seiten[n]&&!b.weg?.includes(n),voll=['1','2','3','4'].every(gut);
 const seiten=voll?'':`<span class="vier">${['1','2','3','4'].map(n=>`<i class="${gut(n)?'ja':b.weg?.includes(n)?'weg':''}"></i>`).join('')}</span>`;
 // Vorschau: abgewickelter Mantel (unten Seite 1, darüber die nächste, wie beim Rollen), sonst ein Zuschnitt
 const bild=b.koerper?`<div class="mantel">${['4','3','2','1'].map(n=>`<i${b.seiten[n]&&!b.weg?.includes(n)?` style="background-image:url('/koerper/${encodeURIComponent(b.id)}/S${n}_k.jpg?v=${b.koerper}')"`:` class="fehlt${b.weg?.includes(n)?' weg':''}"`}></i>`).join('')}</div>`
  :b.bild?`<img src="/zuschnitt/${encodeURIComponent(b.bild)}_k.jpg" alt="" loading="lazy" draggable="false">`:`<div class="ohne">${BALKEN}</div>`;
 const titel=[`${b.id}: ${cm(b.laenge_mm)} × ${cm(b.breite_mm)} × ${cm(b.hoehe_mm)} cm`,b.holzart,
  `${Object.values(b.seiten).filter(Boolean).length} von 4 Seiten, ${b.fertig} von ${b.fotos} Fotos gelabelt`,
  ...(b.weg||[]).map(n=>`Seite ${n}: ${b.gruende?.[n]||'unbrauchbar'}`),
  b.abweichung>2?`Maß weicht bis ${b.abweichung.toLocaleString('de-DE')} % ab`:'',b.fest?'Schon trainiert, Teil bleibt':''].filter(Boolean).join('\n');
 return `<a class="karte${b.fest?' fest':''}${b.id===rechnet?' rechnet':''}" href="/koerper?id=${encodeURIComponent(b.id)}" data-b="${esc(b.id)}" draggable="${!b.fest}" title="${esc(titel)}"
  aria-label="${esc(b.id)}, ${esc(NAME[b.teil])}${b.fest?', gesperrt':''}" aria-keyshortcuts="ArrowLeft ArrowRight">${bild}
  <span><b>${esc(b.id)}</b>${b.abweichung>2?'<i class="ab"></i>':''}${b.fest?SCHLOSS:''}${seiten}</span>
  <small>${cm(b.laenge_mm)} × ${cm(b.breite_mm)} × ${cm(b.hoehe_mm)}</small>
  ${b.fotos?`<i class="lbl" style="--a:${Math.round(100*b.fertig/b.fotos)}%"></i>`:''}</a>`}

function mal(fokus){
 for(const sp of document.querySelectorAll('.spalte')){const t=sp.dataset.teil,da=G.filter(b=>b.teil===t);
  sp.querySelector('h2 small').textContent=da.length||'';
  sp.querySelector('.karten').innerHTML=da.map(karte).join('')||'<div class="leerspalte"></div>'}
 if(fokus)document.querySelector(`.karte[data-b="${fokus}"]`)?.focus()}

async function setzen(id,teil){const b=G.find(x=>x.id===id);if(!b||b.fest||b.teil===teil)return;
 const alt=b.teil;b.teil=teil;mal(document.activeElement?.dataset?.b===id?id:null);$('#gfehler').textContent='';
 try{await ruf('/api/teil',{balken:id,teil});$('#gmeldung').textContent=`${id}: ${NAME[teil]}`}
 catch(e){b.teil=alt;mal();$('#gfehler').textContent=e.message}}

async function laden(){try{G=await ruf('/api/galerie');mal(document.activeElement?.dataset?.b);$('#gfehler').textContent='';nachrechnen()}
 catch(e){$('#gfehler').textContent=e.message}}

// Fehlende oder veraltete Körper nacheinander rechnen, neueste zuerst; was nicht geht, behält den Zuschnitt
const versucht=new Set();let rechnet=null;
async function nachrechnen(){if(rechnet)return;
 for(;;){const b=G.find(x=>x.fotos&&(!x.koerper||x.koerper_alt)&&!versucht.has(x.id));if(!b)break;
  versucht.add(b.id);rechnet=b.id;mal(document.activeElement?.dataset?.b);
  try{const k=await ruf('/api/koerper?id='+encodeURIComponent(b.id));const x=G.find(y=>y.id===b.id);
   if(x){x.koerper=k.stand;x.koerper_alt=false;x.weg=Object.keys(k.seiten).filter(n=>k.seiten[n].grund);x.gruende=Object.fromEntries(x.weg.map(n=>[n,k.seiten[n].grund]));const w=Object.values(k.seiten).filter(s=>!s.grund).flatMap(s=>Object.values(s.abweichung_prozent)).filter(v=>v!=null).map(Math.abs);x.abweichung=w.length?Math.max(...w):null}}
  catch(e){console.warn(b.id,e.message)}}
 rechnet=null;mal(document.activeElement?.dataset?.b)}

const galerie=$('#galerie');
galerie.addEventListener('dragstart',e=>{const k=e.target.closest?.('.karte');if(!k||k.classList.contains('fest'))return e.preventDefault();
 zug=k.dataset.b;e.dataTransfer.setData('text/plain',zug);e.dataTransfer.effectAllowed='move';k.classList.add('zieht')});
galerie.addEventListener('dragend',()=>{zug=null;document.querySelectorAll('.zieht,.ziel').forEach(x=>x.classList.remove('zieht','ziel'))});
galerie.addEventListener('dragover',e=>{const sp=e.target.closest('.spalte');if(!sp||!zug)return;e.preventDefault();e.dataTransfer.dropEffect='move';
 document.querySelectorAll('.ziel').forEach(x=>x!==sp&&x.classList.remove('ziel'));sp.classList.add('ziel')});
galerie.addEventListener('dragleave',e=>{const sp=e.target.closest('.spalte');if(sp&&!sp.contains(e.relatedTarget))sp.classList.remove('ziel')});
galerie.addEventListener('drop',e=>{const sp=e.target.closest('.spalte');if(!sp||!zug)return;e.preventDefault();sp.classList.remove('ziel');setzen(zug,sp.dataset.teil)});
galerie.addEventListener('keydown',e=>{const k=e.target.closest?.('.karte');if(!k||!['ArrowLeft','ArrowRight'].includes(e.key))return;
 const b=G.find(x=>x.id===k.dataset.b),i=TEILE.indexOf(b.teil)+(e.key==='ArrowRight'?1:-1);e.preventDefault();
 if(i>=0&&i<TEILE.length)setzen(b.id,TEILE[i])});
galerie.addEventListener('error',e=>{if(e.target.tagName==='IMG'){const d=document.createElement('div');d.className='ohne';d.innerHTML=BALKEN;e.target.replaceWith(d)}},true);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)laden()});
laden();
