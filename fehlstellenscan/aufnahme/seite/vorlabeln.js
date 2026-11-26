/* Vorlabeln per Modell (Jan 26.11.2026, docs/plan-vorlabeln.md), gemeinsam für Labeln und Galerie. Gerechnet wird auf
   Jans Mac; auf neurolign.meldro.de reicht der Server durch den Tunnel weiter. Knöpfe nur als Symbol, Fortschritt je
   Balken als Zeichnung. Ist der Mac nicht da, sperrt das durchgestrichene Notebook den Knopf (wie Training).
   Modell ohne Schalter (der Mac wählt), ein anderes und Prüfbalken nur bewusst über ···. */
'use strict';
const VL=(()=>{
 const S='fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"';
 const svg=(d,k='')=>`<svg class="vli ${k}" viewBox="0 0 24 24" aria-hidden="true" ${S}>${d}</svg>`;
 const STAB=svg('<path d="M4 20l10-10M12.5 8.5l3 3"/><path d="M17 2.8v3.4M15.3 4.5h3.4M20.5 9v2.4M19.3 10.2h2.4M9.5 3.5v2M8.5 4.5h2"/>');
 const STABGUT=svg('<path d="M4 20l10-10M12.5 8.5l3 3"/><path d="M17 2.8v3.4M15.3 4.5h3.4M9.5 3.5v2M8.5 4.5h2"/><path class="zg" d="M14.5 18l2.3 2.3 4.7-5"/>');
 const STABWARN=svg('<path d="M4 20l10-10M12.5 8.5l3 3"/><path d="M17 2.8v3.4M15.3 4.5h3.4M9.5 3.5v2M8.5 4.5h2"/><path class="zw" d="M18 14v3.5M18 20.5v.01"/>');
 const AUS=svg('<path d="M5 6h14v9H5zM3 18h18M4 3l16 16"/>','aus');
 const SCHLOSS=svg('<rect x="5" y="11" width="14" height="10" rx="1"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>');
 const OFFEN=svg('<rect x="5" y="11" width="14" height="10" rx="1"/><path d="M8 11V8a4 4 0 0 1 7.6-1.8"/>');
 const PUNKTE='<svg class="vli" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><circle cx="5" cy="12" r="1.8"/><circle cx="12" cy="12" r="1.8"/><circle cx="19" cy="12" r="1.8"/></svg>';
 const HAKEN=svg('<path d="M5 12.5l4.5 4.5L19 7.5"/>','gut');
 const WARN=svg('<path d="M12 3l10 18H2zM12 10v5M12 18v.01"/>','warn');
 const MAC=['localhost','127.0.0.1'].includes(location.hostname);
 const esc=t=>String(t).replace(/[&<>"]/g,c=>'&#'+c.charCodeAt(0)+';');
 let stand=null,aus='',wahl=null,pruef=false,uhr=null,fertigGemeldet=new Set,beiFertig=()=>{},beiStand=()=>{};
 const lauf=()=>stand&&stand.lauf,laeuft=()=>!!lauf()&&['holen','rechnen'].includes(lauf().status);
 const modell=()=>wahl||(stand&&stand.modell)||'';
 async function ruf(weg,daten){let a;try{a=await fetch(weg,daten===undefined?{}:{method:'POST',headers:{'X-Aufnahme':'1'},body:JSON.stringify(daten)})}
  catch(e){throw Object.assign(Error(MAC?'Das Programm auf dem Mac antwortet nicht.':'Keine Verbindung zu Neurolign.'),{mac:false})}
  let j={};try{j=await a.json()}catch(e){}if(!a.ok)throw Object.assign(Error(j.fehler||`Fehler ${a.status}`),{mac:j.mac});return j}
 function neu(j){stand=j;aus='';const l=lauf();
  if(l)for(const[b,e]of Object.entries(l.balken)){const k=l.id+b;if(e.status=='fertig'&&!fertigGemeldet.has(k)){fertigGemeldet.add(k);beiFertig(b,e)}}
  beiStand();takt()}
 function takt(){clearTimeout(uhr);uhr=setTimeout(laden,laeuft()?2500:aus?30000:60000)}
 async function laden(){if(document.hidden){takt();return}try{neu(await ruf('/api/vorlabeln'))}catch(e){aus=e.mac===false?e.message:'';if(!aus)console.warn(e.message);stand=stand&&e.mac===false?null:stand;beiStand();takt()}}
 /* balken: Liste IDs; fotos: Namen (leer = alle) */
 async function start(balken,fotos){if(aus||laeuft())return;
  const d={balken,fotos:fotos||[]};if(wahl)d.modell=wahl;if(pruef)d.pruefung=true;
  try{const j=await ruf('/api/vorlabeln',d);pruef=false;for(const b of balken)fertigGemeldet.delete((j.lauf||{}).id+b);neu(j);return true}
  catch(e){if(e.mac===false){aus=e.message;beiStand()}throw e}}
 function teil(b){return stand&&stand.teile?stand.teile[b]:undefined}
 const gesperrt=b=>!pruef&&teil(b)!==undefined&&teil(b)!='train';
 /* Zustand eines Balkens: [Text, Zeichnung] */
 function zustand(b){const l=lauf(),e=l&&l.balken[b];
  if(e&&(e.status=='wartet'||e.status=='rechnen'&&!e.m)&&laeuft())return['wartet',`<svg class="vli ring warte" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="3 3.7"/></svg>`];
  if(e&&e.status=='rechnen'){const a=e.n/e.m,w=a*2*Math.PI,x=12+8.5*Math.sin(w),y=12-8.5*Math.cos(w);
   return[`${e.n} von ${e.m} Kacheln`,`<svg class="vli ring" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" stroke-opacity=".3" stroke-width="2"/>${a>=1?'<circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" stroke-width="2"/>':`<path d="M12 3.5A8.5 8.5 0 ${a>.5?1:0} 1 ${x.toFixed(2)} ${y.toFixed(2)}" fill="none" stroke="currentColor" stroke-width="2"/>`}</svg>`]}
  if(e&&e.status=='fertig')return[`fertig, ${e.neu??0} neu`,STABGUT];
  if(e&&e.status=='fehler')return[e.fehler||'Fehler',STABWARN];
  if(e&&e.status=='gesperrt'||gesperrt(b))return['Prüfung oder Nur Test: nicht vorlabeln',SCHLOSS];
  return['',STAB]}
 /* Knopf für einen Balken oder ein Foto. attr: data-Attribute */
 function knopf(b,attr,titel){const[t,z]=zustand(b),l=lauf(),e=l&&l.balken[b],arbeit=laeuft()&&e&&['wartet','rechnen'].includes(e.status);
  const sperr=!!aus||laeuft()||gesperrt(b)||!stand,txt=aus?aus:arbeit||gesperrt(b)||e&&e.status=='fehler'?t:`${titel}${modell()?' mit '+modell():''}${e&&e.status=='fertig'?` (zuletzt ${t})`:''}`;
  return`<button class="ib vlk${arbeit?' arbeit':''}" ${attr} aria-label="${esc(txt)}" title="${esc(txt)}" ${sperr?'aria-disabled="true"':''}>${aus?AUS:e&&e.status=='fertig'?STAB:z}</button>`}
 /* Etikett mit Modellname und ···: anderes Modell, Prüfbalken einmal mit einbeziehen */
 function etikett(){if(aus||!stand)return'';
  return`<span class="vle"><span class="vlm" title="Modell fürs Vorlabeln">${esc(modell()||'kein Modell')}</span><button class="ib vlmehr" aria-haspopup="true" aria-expanded="false" aria-label="Modell und Prüfbalken" title="Modell und Prüfbalken">${PUNKTE}</button></span>`}
 function menue(knopf){let m=document.getElementById('vlmenue');if(m){m.remove();knopf.setAttribute('aria-expanded','false');return}
  m=document.createElement('div');m.id='vlmenue';m.className='vlmenue';m.setAttribute('role','menu');
  const ms=(stand&&stand.modelle)||[];
  m.innerHTML=ms.map(n=>`<button role="menuitemradio" aria-checked="${n==modell()}" data-m="${esc(n)}">${n==modell()?HAKEN:'<i></i>'}<span>${esc(n)}</span>${n==stand.modell?'<small>★</small>':''}</button>`).join('')+
   `<hr><button role="menuitemcheckbox" aria-checked="${pruef}" data-p="1" title="Einmal auch Prüf- und Testbalken vorlabeln">${pruef?OFFEN:SCHLOSS}<span>Prüf- und Testbalken</span></button>`;
  document.body.append(m);const r=knopf.getBoundingClientRect(),w=m.offsetWidth,h=m.offsetHeight;
  m.style.left=Math.max(8,Math.min(r.right-w,innerWidth-w-8))+'px';m.style.top=(r.bottom+h+4>innerHeight?Math.max(8,r.top-h-4):r.bottom+4)+'px';knopf.setAttribute('aria-expanded','true');
  m.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.m)wahl=b.dataset.m==stand.modell?null:b.dataset.m;if(b.dataset.p)pruef=!pruef;m.remove();knopf.setAttribute('aria-expanded','false');beiStand();knopf.isConnected&&knopf.focus()});
  m.addEventListener('keydown',e=>{const k=[...m.querySelectorAll('button')],i=k.indexOf(document.activeElement);if(e.key=='Escape'){m.remove();knopf.focus()}
   if(e.key=='ArrowDown'){e.preventDefault();k[(i+1)%k.length].focus()}if(e.key=='ArrowUp'){e.preventDefault();k[(i+k.length-1)%k.length].focus()}});
  m.querySelector('button').focus()}
 addEventListener('pointerdown',e=>{const m=document.getElementById('vlmenue');if(m&&!e.target.closest('#vlmenue,.vlmehr'))m.remove()});
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)laden()});
 return{laden,start,knopf,etikett,menue,zustand,laeuft,gesperrt,get aus(){return aus},get stand(){return stand},
  set beiFertig(f){beiFertig=f},set beiStand(f){beiStand=f}};
})();
