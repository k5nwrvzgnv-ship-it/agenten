'use strict';
const $=i=>document.getElementById(i),esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const KL=['Ast lebend','Ast tot','Astloch','Ast mit Riss','Riss','Quartzity','Harz','Mark','Bläue','Überwallung','Bohrloch','Metall','Nagelloch','Farbe','Fäule','Insektenfraß','Verbindung','Fuge'];
const dez=w=>w==null?'–':w.toLocaleString('de-DE',{minimumFractionDigits:3,maximumFractionDigits:3});
function dauer(s){if(s==null)return'–';const m=Math.round(s/60),h=Math.floor(m/60);return h?`${h} h ${m%60} min`:`${m} min`}
function ergebnis(e){if(!e)return'';const a=e.altholz||e,g=a.gesamt,m=g.maske,b=g.box,ge=e.gesamt.maske,satz={altholz:'Altholz',kodytek:'Kodytek-Auswahl'};
 const zahlen=[['mAP50',m.map50],['mAP50-95',m.map],['Precision',m.p],['Recall',m.r]];
 const neben=[['Beste Epoche',e.beste==null?'–':`${e.beste} von ${e.gelaufen}${e.epochen&&e.gelaufen<e.epochen?` (geplant ${e.epochen})`:''}`],['Dauer',dauer(e.sekunden)],
  ['Bilder',e.train==null?'–':`${zahl(e.train)} Training, ${zahl(e.val)} Prüfung`],['Datensätze',e.saetze.length?e.saetze.map(x=>satz[x]||x).join(', '):'–'],
  ['Startmodell',e.modell||'–'],['Bildgröße, Batch',`${e.imgsz||'–'} px, ${e.batch||'–'}`]];
 return `<h3 id="tergk">Ergebnis ${esc(e.name)}</h3>${e.probe?'<p class="warn">Alter Lauf, geprüft auf denselben Fotos wie trainiert. Die Zahlen sagen nichts über die Erkennung.</p>':PRUEF[e.pruefung]?`<p class="leise">${PRUEF[e.pruefung]}</p>`:''}
 <p class="leise">Masken, geprüft mit dem besten Stand auf ${e.altholz?'Altholz, ':''}${zahl(g.bilder)} Bildern mit ${zahl(g.objekte)} Objekten</p>
 <dl class="kenn">${zahlen.map(([n,w])=>`<div><dt>${n}</dt><dd>${dez(w)}</dd></div>`).join('')}</dl>
 <p class="leise boxen">Boxen: mAP50 ${dez(b.map50)}, mAP50-95 ${dez(b.map)}, Precision ${dez(b.p)}, Recall ${dez(b.r)}</p>${e.altholz?`
 <p class="leise boxen">Alle Sätze zusammen (${zahl(e.gesamt.bilder)} Bilder): mAP50 ${dez(ge.map50)}, mAP50-95 ${dez(ge.map)}, Precision ${dez(ge.p)}, Recall ${dez(ge.r)}</p>`:''}
 <div class="breit" tabindex="0" role="region" aria-label="Masken je Klasse"><table class="zahlen"><caption class="nurvor">Masken je Klasse</caption><thead><tr><th>Klasse</th><th>Objekte</th><th>mAP50</th><th>mAP50-95</th><th>Precision</th><th>Recall</th></tr></thead>
 <tbody>${a.klassen.map(k=>`<tr><td>${esc(k.k==null?k.klasse:KL[k.k])}</td><td>${zahl(k.objekte)}</td><td>${dez(k.maske.map50)}</td><td>${dez(k.maske.map)}</td><td>${dez(k.maske.p)}</td><td>${dez(k.maske.r)}</td></tr>`).join('')}</tbody></table></div>
 <dl class="lauf">${neben.map(([n,w])=>`<div><dt>${n}</dt><dd>${esc(w)}</dd></div>`).join('')}</dl>
 <p class="leise pfad">${esc(e.gewichte)}</p>`}
const TEIL={train:'Training',val:'Prüfung',test:'Nur Test'};
const PRUEF={seite:'Altholz geprüft auf einer zurückgehaltenen Seite, ohne eigenen Prüfbalken.',fotos:'Altholz geprüft auf den letzten Fotos derselben Seite, Nachbarfotos überlappen.'};let S=null,ERG='';const WAHL=new Set(['altholz']),zahl=n=>n.toLocaleString('de-DE');
const MAC=['localhost','127.0.0.1'].includes(location.hostname);
/* Auf neurolign.meldro.de rechnet Jans Mac über den Tunnel; ist er nicht da, antwortet der Server mit mac:false */
async function ruf(weg,daten){let a;try{a=await fetch(weg,daten===undefined?{}:{method:'POST',headers:{'X-Aufnahme':'1'},body:JSON.stringify(daten)})}catch(e){throw Error(MAC?'Das Programm auf dem Mac antwortet nicht. Im Terminal neu starten.':'Keine Verbindung zu Neurolign.')}
 let j={};try{j=await a.json()}catch(e){}if(!a.ok)throw Object.assign(Error(j.fehler||`Fehler ${a.status}`),{mac:j.mac});return j}
const AUS='<svg class="ic macaus" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 6h14v9H5zM3 18h18M4 3l16 16"/></svg>';
function fehler(e){const aus=e.mac===false;$('tfehler').innerHTML=aus?`<span role="img" title="${esc(e.message)}" aria-label="${esc(e.message)}">${AUS}</span>`:esc(e.message);
 $('training').classList.toggle('ohnemac',aus);if(aus)$('tlos').disabled=true}
const aktiv=()=>S.lauf&&['bauen','training','pruefen'].includes(S.lauf.status);
function mal(){const d=document.activeElement&&document.activeElement.dataset.b;
 $('tbal').innerHTML=S.balken.map(b=>`<tr><td>${esc(b.id)}</td><td>${b.fertig} von ${b.fotos}</td><td>${b.objekte}</td><td>${b.fest?TEIL[b.teil]:`<select data-b="${esc(b.id)}" aria-label="Teil von ${esc(b.id)}">${Object.entries(TEIL).map(([k,n])=>`<option value="${k}" ${k===b.teil?'selected':''}>${n}</option>`).join('')}</select>`}</td></tr>`).join('');
 $('talt').hidden=!S.balken.length;
 if(d)document.querySelector(`[data-b="${d}"]`)?.focus();
 const A=S.altholz;
 const R=[{id:'altholz',name:'Altholz',train:A.train,val:A.val},...S.saetze],fk=document.activeElement&&document.activeElement.dataset.s;
 $('tsatz').innerHTML='<legend>Datensätze</legend>'+R.map(x=>`<label><input type="checkbox" data-s="${esc(x.id)}" ${WAHL.has(x.id)?'checked':''} ${aktiv()?'disabled':''}><span>${esc(x.name)}</span><small>${zahl(x.train+x.val)} Bilder${x.fertig!=null?`, ${zahl(x.fertig)} korrigiert`:''}</small></label>`).join('');
 if(fk)document.querySelector(`[data-s="${fk}"]`)?.focus();
 const W=R.filter(x=>WAHL.has(x.id)),sum=t=>W.reduce((n,x)=>n+x[t],0),nurAlt=W.length===1&&W[0].id==='altholz',g=W.length&&(nurAlt?A.val>0:sum('train')&&sum('val')&&!(WAHL.has('altholz')&&!A.val));
 const ganz=W.some(x=>x.fertig==null&&x.id!=='altholz');
 $('tsumme').textContent=!W.length?'Mindestens einen Datensatz wählen.':WAHL.has('altholz')&&!A.fertig?'Altholz hat noch kein fertig gelabeltes Foto.':WAHL.has('altholz')&&!A.val?'Für die Prüfung fehlt ein zweites fertig gelabeltes Foto.':`Training ${zahl(sum('train'))}, Prüfung ${zahl(sum('val'))} Bilder${W.some(x=>x.id==='kodytek')&&ganz?' (doppelte zählen einmal)':''}. Start vom Modell ${S.modell}.`;
 $('tprobe').textContent=!g?'':WAHL.has('altholz')&&PRUEF[A.art]?PRUEF[A.art]:ganz?'Der ganze Satz rechnet auf dem Mac viele Stunden.':'';
 $('tlos').disabled=!aktiv()&&!g;$('tlos').textContent=aktiv()?'Training abbrechen':'Training starten';
 const eh=ergebnis(S.ergebnis);if(eh!==ERG){$('terg').innerHTML=ERG=eh}$('terg').hidden=!eh;
 const l=S.lauf;if(!l){$('tlauf').innerHTML='';return}
 const w=l.werte.at(-1),t={bauen:'Datensatz wird gebaut',training:`Epoche ${l.epoche} von ${l.epochen}`,pruefen:'Prüfung nur auf Altholz',fertig:'Fertig',fehler:'Fehlgeschlagen',abgebrochen:'Abgebrochen'}[l.status];
 $('tlauf').innerHTML=`<p role="status"><b>${esc(l.name)}</b> ${t}</p><progress max="${l.epochen}" value="${l.epoche}" aria-label="Epochen"></progress>${w&&w.map!==undefined?`<p class="leise">Masken-mAP50 ${w.map.toLocaleString('de-DE',{maximumFractionDigits:3})}</p>`:''}${l.fehler?`<p class="fehler">${esc(l.fehler)}</p>`:''}`}
async function tu(weg,daten){try{S=await ruf(weg,daten);fehler({});$('tfehler').textContent='';mal()}catch(e){fehler(e)}}
$('tlos').onclick=()=>aktiv()?tu('/api/abbrechen',{}):tu('/api/training',{saetze:[...WAHL]});
$('tsatz').onchange=e=>{const s=e.target.dataset.s;e.target.checked?WAHL.add(s):WAHL.delete(s);mal()};
$('tbal').onchange=e=>tu('/api/teil',{balken:e.target.dataset.b,teil:e.target.value});
async function puls(){if(document.activeElement.tagName!=='SELECT')try{S=await ruf('/api/training');if($('training').classList.contains('ohnemac')){fehler({});$('tfehler').textContent=''}mal()}catch(e){fehler(e)};setTimeout(puls,3000)}
puls();
