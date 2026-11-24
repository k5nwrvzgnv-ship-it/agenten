/* Looks und Bedienfeld. Je Look ein Satz Startwerte, Jans Änderungen liegen darüber (localStorage, je Look). */
const LOOKS={
neurolign:{n:'Neurolign',schrift:'Outfit',fs:15,modus:'dunkel',dichte:1,ecken:28,strich:1.1,regler:'dreh',zahl:'an',vorschau:'rund',getrennt:1,
 dunkel:{flaeche:'#0e0d0c',akzent:'#d19a3f',buehne:'#000000'},hell:{flaeche:'#f4f2ee',akzent:'#8a5a10',buehne:'#dcd8d0'}},
ruhig:{n:'Neurolign ruhig',schrift:'Outfit',fs:15,modus:'dunkel',dichte:1,ecken:22,strich:1,regler:'schieber',zahl:'aus',vorschau:'rund',
 dunkel:{flaeche:'#12110f',akzent:'#e0a94b',buehne:'#000000'},hell:{flaeche:'#f1efeb',akzent:'#7d5312',buehne:'#d8d4cc'}},
nacht:{n:'Nachtschicht',schrift:'JetBrains Mono',fs:13,modus:'dunkel',dichte:.85,ecken:0,strich:.7,regler:'schieber',zahl:'aus',vorschau:'eckig',getrennt:1,
 dunkel:{flaeche:'#0b1016',akzent:'#6ff7e8',buehne:'#05080b'},hell:{flaeche:'#e9eef2',akzent:'#00616b',buehne:'#b4bec6'}},
mess:{n:'Messblatt',schrift:'Source Serif 4',fs:16,modus:'hell',dichte:1,ecken:2,strich:.9,regler:'schieber',zahl:'aus',vorschau:'eckig',
 hell:{flaeche:'#ffffff',akzent:'#b3261e',buehne:'#e6e6e6'},dunkel:{flaeche:'#161616',akzent:'#ff8a7a',buehne:'#000000'}},
farbe:{n:'Farbfeld',schrift:'Bricolage Grotesque',fs:16,modus:'hell',dichte:1,ecken:20,strich:1.7,regler:'schieber',zahl:'an',vorschau:'eckig',getrennt:1,
 hell:{flaeche:'#e4e3ee',akzent:'#1d1a3a',buehne:'#1d1a3a'},dunkel:{flaeche:'#1a1830',akzent:'#f0eefc',buehne:'#0b0a18'}},
wald:{n:'Waldkante',schrift:'Schibsted Grotesk',fs:15,modus:'hell',dichte:1,ecken:8,strich:1.1,regler:'schieber',zahl:'aus',vorschau:'eckig',
 hell:{flaeche:'#f3f7f4',akzent:'#17603f',buehne:'#b9c4bd'},dunkel:{flaeche:'#10201a',akzent:'#7fdca8',buehne:'#07110d'}}};
const SCHRIFTEN=['Outfit','Geist','Host Grotesk','Instrument Sans','Schibsted Grotesk','Archivo','IBM Plex Sans','Bricolage Grotesque','Barlow Semi Condensed','Source Serif 4','JetBrains Mono','Systemschrift'];
let wahl={look:'neurolign',je:{}};try{const w=JSON.parse(localStorage.getItem('werkbank-looks-wahl')||'null');if(w&&LOOKS[w.look])wahl={look:w.look,je:w.je||{}}}catch(e){}
const hash=location.hash.slice(1);if(LOOKS[hash])wahl.look=hash;
const W=()=>{const l=LOOKS[wahl.look],j=wahl.je[wahl.look]||{},m=j.modus||l.modus;return{look:wahl.look,...l,...l[m],...j,modus:m}};
const STRICH=()=>W().strich,INL=()=>!W().getrennt||matchMedia('(max-width:860px)').matches;
/* Farbrechnung: aus Fläche und Akzent entstehen alle Töne, Schrift bleibt lesbar, egal was gewählt ist */
const rgb=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16)),hex=a=>'#'+a.map(x=>Math.round(x).toString(16).padStart(2,'0')).join('');
const mi=(a,b,t)=>{const x=rgb(a),y=rgb(b);return hex(x.map((v,i)=>v+(y[i]-v)*t))};
const lum=h=>rgb(h).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
const kon=(a,b)=>{const[x,y]=[lum(a),lum(b)].sort((p,q)=>q-p);return(x+.05)/(y+.05)};
const auf=h=>kon('#ffffff',h)>kon('#111111',h)?'#ffffff':'#111111';
const lesbar=(f,ziel,gr,k)=>{for(let t=0;t<=1;t+=.05){const x=mi(f,ziel,t);if(gr.every(g=>kon(x,g)>=k))return x}return ziel};
function farben(w){const F=w.flaeche,A=w.akzent,T=kon('#f4f4f4',F)>kon('#141414',F)?'#f4f4f4':'#141414',wa=mi(F,A,.15),f2=mi(F,T,.07),schw=mi(F,T,.1),G=[F,wa,f2,schw];
 const schiene=lum(F)<.2?mi(A,'#000000',.8):mi(A,'#000000',.35);
 return{flaeche:F,feld2:f2,akz:A,aufakz:auf(A),akzh:mi(A,auf(A)=='#ffffff'?'#000000':'#ffffff',.15),akzt:lesbar(A,T,G,4.6),fok:lesbar(A,T,G,4.6),text:T,leise:lesbar(mi(F,T,.6),T,G,4.7),linie:mi(F,T,.17),stark:mi(F,T,.5),aus:mi(F,T,.4),wahl:wa,wahlt:lesbar(A,T,[wa],4.6),schw,buehne:w.buehne,warn:lesbar('#e08a1e',T,G,4.6),ok:lesbar('#2fa866',T,G,4.6),rot:lesbar('#e0453c',T,G,4.6),schiene,schienet:auf(schiene),cs:T=='#f4f4f4'?'dark':'light'}}
function gestalte(){const w=W(),a=document.getElementById('app'),h=document.documentElement.style;a.dataset.look=w.look;a.dataset.vorschau=w.vorschau;
 for(const[k,v]of Object.entries(farben(w)))a.style.setProperty('--'+k,v);
 a.style.setProperty('--f',w.schrift=='Systemschrift'?'system-ui,-apple-system,"Segoe UI",sans-serif':`"${w.schrift}",system-ui,sans-serif`);
 a.style.fontVariantNumeric=w.schrift=='Schibsted Grotesk'?'normal':'';a.style.setProperty('--d',w.dichte);a.style.setProperty('--r',w.ecken+'px');h.setProperty('--fs',w.fs+'px');h.background='#1d1f22';
 document.getElementById('looks').innerHTML=Object.entries(LOOKS).map(([k,l])=>`<button data-l="${k}" aria-pressed="${k==w.look}">${l.n}${wahl.je[k]?' *':''}</button>`).join('');
 const ab=document.querySelector(`[data-l="${w.look}"]`),lo=document.getElementById('looks');lo.scrollLeft=ab.offsetLeft-lo.offsetLeft-8;
 const f=document.getElementById('feld');if(!f.hidden&&!f.contains(document.activeElement))feldZ();else if(!f.hidden)werteZ();
 try{localStorage.setItem('werkbank-looks-wahl',JSON.stringify(wahl))}catch(e){}}
const REG=[['schrift','Schriftart',SCHRIFTEN.map(s=>[s,s])],['fs','Schriftgröße',12,20,.5,' px'],['modus','Helligkeit',[['dunkel','Dunkel'],['hell','Hell']]],['akzent','Akzentfarbe'],['flaeche','Flächenfarbe'],['buehne','Um das Bild'],['dichte','Dichte',[[.8,'Eng'],[.85,'Dicht'],[1,'Normal'],[1.15,'Luftig']]],['ecken','Ecken',0,32,1,' px'],['strich','Umrisse',.4,2.6,.1,'×'],['regler','Regler',[['dreh','Drehregler'],['schieber','Schieber']]],['zahl','Große Zahl',[['an','An'],['aus','Aus']]],['vorschau','Vorschau',[['rund','Rund'],['eckig','Eckig']]]];
const komma=x=>(''+x).replace('.',',');
const anzeige=(r,v)=>Array.isArray(r[2])?(r[2].find(o=>o[0]==v)||['',v])[1]:r.length>3?komma(v)+r[5]:v;
const text=()=>{const w=W(),j=wahl.je[w.look]||{};return`Look ${w.n}: `+REG.map(r=>`${r[1]} ${anzeige(r,w[r[0]])}`).join(', ')+'. Geändert: '+(REG.filter(r=>j[r[0]]!==undefined).map(r=>r[1]).join(', ')||'nichts')+'.'};
function feldZ(){const w=W();document.getElementById('feld').innerHTML=`<h2>${w.n} anpassen</h2>`+REG.map(r=>{const i='s-'+r[0],v=w[r[0]];return`<div class="z"><label for="${i}">${r[1]}</label>${Array.isArray(r[2])?`<select id="${i}">${r[2].map(o=>`<option value="${o[0]}" ${o[0]==v?'selected':''}>${o[1]}</option>`).join('')}</select>`:r.length>3?`<div class="s"><input id="${i}" type="range" min="${r[2]}" max="${r[3]}" step="${r[4]}" value="${v}"><output>${anzeige(r,v)}</output></div>`:`<input id="${i}" type="color" value="${v}">`}</div>`}).join('')+`<div class="kn"><button class="kop" id="kop">Wahl als Text kopieren</button><button id="zur">Diesen Look zurücksetzen</button><button id="allz">Alle Looks zurücksetzen</button></div><textarea id="wtext" readonly aria-label="Wahl als Text">${text()}</textarea>`}
function werteZ(){const w=W();for(const r of REG){const e=document.getElementById('s-'+r[0]);if(!e)return;e.value=w[r[0]];if(r.length>3)e.nextElementSibling.textContent=anzeige(r,w[r[0]])}document.getElementById('wtext').value=text()}
document.getElementById('looks').onclick=e=>{const b=e.target.closest('button');if(!b)return;wahl.look=b.dataset.l;gestalte();if(!document.getElementById('feld').hidden)feldZ();document.querySelector(`[data-l="${wahl.look}"]`).focus({preventScroll:true});mal()};
document.getElementById('anp').onclick=e=>{const f=document.getElementById('feld');f.hidden=!f.hidden;e.target.setAttribute('aria-expanded',!f.hidden);e.target.textContent=f.hidden?'Anpassen':'Schließen';if(!f.hidden)feldZ()};
document.getElementById('feld').addEventListener('input',e=>{const k=e.target.id.slice(2),r=REG.find(r=>r[0]==k);if(!r)return;const j=wahl.je[wahl.look]??={};
 if(k=='modus'){delete j.akzent;delete j.flaeche;delete j.buehne}j[k]=['fs','dichte','ecken','strich'].includes(k)?+e.target.value:e.target.value;gestalte();mal()});
document.getElementById('feld').addEventListener('click',async e=>{const i=e.target.id;if(i=='zur'){delete wahl.je[wahl.look];gestalte();feldZ();mal()}if(i=='allz'){wahl.je={};gestalte();feldZ();mal()}
 if(i=='kop'){const t=document.getElementById('wtext');try{await navigator.clipboard.writeText(t.value);e.target.textContent='Kopiert'}catch(x){t.focus();t.select();e.target.textContent=document.execCommand('copy')?'Kopiert':'Text unten markiert: Strg C'}setTimeout(()=>{const k=document.getElementById('kop');if(k)k.textContent='Wahl als Text kopieren'},2500)}});
