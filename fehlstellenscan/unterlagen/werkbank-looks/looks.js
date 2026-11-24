/* Looks und Bedienfeld. Je Look ein Satz Startwerte, Jans Änderungen liegen darüber (localStorage, je Look). */
const LOOKS={
neurolign:{n:'Neurolign',schrift:'Outfit',fs:15,modus:'dunkel',dichte:1,ecken:28,strich:1.1,regler:'dreh',zahl:'an',vorschau:'rund',getrennt:1,
 dunkel:{flaeche:'#0e0d0c',akzent:'#d19a3f',buehne:'#000000'},hell:{flaeche:'#f4f2ee',akzent:'#8a5a10',buehne:'#dcd8d0'}},
ruhig:{n:'Neurolign ruhig',schrift:'Outfit',fs:15,modus:'dunkel',dichte:1,ecken:22,strich:1,regler:'schieber',zahl:'aus',vorschau:'rund',
 dunkel:{flaeche:'#12110f',akzent:'#e0a94b',buehne:'#000000'},hell:{flaeche:'#f1efeb',akzent:'#7d5312',buehne:'#d8d4cc'}},
/* Jans Wahl vom 24.11.2026; nur die Schrift ist ein Vorschlag */
nacht:{n:'Nachtschicht',schrift:'Red Hat Text',fs:13.5,modus:'dunkel',dichte:1.15,ecken:9,strich:.4,regler:'dreh',zahl:'aus',vorschau:'eckig',getrennt:1,
 dunkel:{flaeche:'#000000',akzent:'#000000',buehne:'#05080b'},hell:{flaeche:'#e9eef2',akzent:'#00616b',buehne:'#b4bec6'}},
mess:{n:'Messblatt',schrift:'Source Serif 4',fs:16,modus:'hell',dichte:1,ecken:2,strich:.9,regler:'schieber',zahl:'aus',vorschau:'eckig',
 hell:{flaeche:'#ffffff',akzent:'#b3261e',buehne:'#e6e6e6'},dunkel:{flaeche:'#161616',akzent:'#ff8a7a',buehne:'#000000'}},
farbe:{n:'Farbfeld',schrift:'Bricolage Grotesque',fs:16,modus:'hell',dichte:1,ecken:20,strich:1.7,regler:'schieber',zahl:'an',vorschau:'eckig',getrennt:1,
 hell:{flaeche:'#e4e3ee',akzent:'#1d1a3a',buehne:'#1d1a3a'},dunkel:{flaeche:'#1a1830',akzent:'#f0eefc',buehne:'#0b0a18'}},
wald:{n:'Waldkante',schrift:'Schibsted Grotesk',fs:15,modus:'hell',dichte:1,ecken:8,strich:1.1,regler:'schieber',zahl:'aus',vorschau:'eckig',
 hell:{flaeche:'#f3f7f4',akzent:'#17603f',buehne:'#b9c4bd'},dunkel:{flaeche:'#10201a',akzent:'#7fdca8',buehne:'#07110d'}}};
const GRUPPEN={Ruhig:['Red Hat Text','Hanken Grotesk','Manrope','Figtree'],Geometrisch:['Urbanist','Red Hat Display','Sora','Afacad Flux'],Technisch:['Saira','Chakra Petch','Oxanium','Exo 2'],Eigenwillig:['Space Grotesk','Familjen Grotesk','Syne','Zalando Sans Expanded'],Schmal:['Smooch Sans','Big Shoulders'],Schreibmaschine:['Sometype Mono','Geist Mono'],Serifen:['Newsreader','Fraunces'],Bisherige:['Outfit','Geist','Host Grotesk','Instrument Sans','Schibsted Grotesk','Archivo','IBM Plex Sans','Bricolage Grotesque','Barlow Semi Condensed','Source Serif 4','JetBrains Mono','Systemschrift']};
let wahl={look:'nacht',je:{}};try{const w=JSON.parse(localStorage.getItem('werkbank-looks-wahl2')||'null');if(w&&LOOKS[w.look])wahl={look:w.look,je:w.je||{},google:w.google||[]}}catch(e){}
const hash=location.hash.slice(1);if(LOOKS[hash])wahl.look=hash;
const W=()=>{const grund={gewicht:400,lauf:0};const l=LOOKS[wahl.look],j=wahl.je[wahl.look]||{},m=j.modus||l.modus;return{look:wahl.look,...grund,...l,...l[m],...j,modus:m}};
const STRICH=()=>W().strich,INL=()=>!W().getrennt||matchMedia('(max-width:860px)').matches;
/* Farbrechnung: aus Fläche und Akzent entstehen alle Töne, Schrift bleibt lesbar, egal was gewählt ist */
const rgb=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16)),hex=a=>'#'+a.map(x=>Math.round(x).toString(16).padStart(2,'0')).join('');
const mi=(a,b,t)=>{const x=rgb(a),y=rgb(b);return hex(x.map((v,i)=>v+(y[i]-v)*t))};
const lum=h=>rgb(h).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
const kon=(a,b)=>{const[x,y]=[lum(a),lum(b)].sort((p,q)=>q-p);return(x+.05)/(y+.05)};
const auf=h=>kon('#ffffff',h)>kon('#111111',h)?'#ffffff':'#111111';
const lesbar=(f,ziel,gr,k)=>{for(let t=0;t<=1;t+=.05){const x=mi(f,ziel,t);if(gr.every(g=>kon(x,g)>=k))return x}return ziel};
function farben(w){const F=w.flaeche,A=w.akzent,T=kon('#f4f4f4',F)>kon('#141414',F)?'#f4f4f4':'#141414',wa=kon(mi(F,A,.15),F)<1.08?mi(F,T,.16):mi(F,A,.15),f2=mi(F,T,.07),schw=mi(F,T,.1),G=[F,wa,f2,schw];
 const schiene=lum(F)<.2?mi(A,'#000000',.8):mi(A,'#000000',.35);
 return{flaeche:F,feld2:f2,akz:A,aufakz:auf(A),akzh:mi(A,auf(A)=='#ffffff'&&lum(A)>.02?'#000000':'#ffffff',.18),akzr:kon(A,F)<1.6?T:A,akzt:kon(A,F)<1.6?T:lesbar(A,T,G,4.6),fok:kon(A,F)<1.6?T:lesbar(A,T,G,4.6),text:T,leise:lesbar(mi(F,T,.6),T,G,4.7),linie:mi(F,T,.17),stark:mi(F,T,.5),aus:mi(F,T,.4),wahl:wa,wahlt:kon(A,F)<1.6?T:lesbar(A,T,[wa],4.6),schw,buehne:w.buehne,warn:lesbar('#e08a1e',T,G,4.6),ok:lesbar('#2fa866',T,G,4.6),rot:lesbar('#e0453c',T,G,4.6),schiene,schienet:auf(schiene),cs:T=='#f4f4f4'?'dark':'light'}}
function gestalte(){const w=W(),a=document.getElementById('app'),h=document.documentElement.style;a.dataset.look=w.look;a.dataset.vorschau=w.vorschau;
 for(const[k,v]of Object.entries(farben(w)))a.style.setProperty('--'+k,v);
 a.style.setProperty('--f',w.schrift=='Systemschrift'?'system-ui,-apple-system,"Segoe UI",sans-serif':`"${w.schrift}",system-ui,sans-serif`);
 a.style.fontVariantNumeric=w.schrift=='Schibsted Grotesk'?'normal':'';a.style.fontWeight=w.gewicht||400;a.style.letterSpacing=(w.lauf||0)+'em';a.style.setProperty('--d',w.dichte);a.style.setProperty('--r',w.ecken+'px');h.setProperty('--fs',w.fs+'px');h.background='#1d1f22';
 document.getElementById('looks').innerHTML=Object.entries(LOOKS).map(([k,l])=>`<button data-l="${k}" aria-pressed="${k==w.look}">${l.n}${wahl.je[k]?' *':''}</button>`).join('');
 const ab=document.querySelector(`[data-l="${w.look}"]`),lo=document.getElementById('looks');lo.scrollLeft=ab.offsetLeft-lo.offsetLeft-8;
 const f=document.getElementById('feld');if(!f.hidden&&!f.contains(document.activeElement))feldZ();else if(!f.hidden)werteZ();
 try{localStorage.setItem('werkbank-looks-wahl2',JSON.stringify(wahl))}catch(e){}}
const REG=[['schrift','Schriftart'],['fs','Schriftgröße',12,20,.5,' px'],['gewicht','Schriftstärke',[[300,'Leicht'],[400,'Normal'],[500,'Kräftig']]],['lauf','Laufweite',-.03,.08,.01,' em'],['modus','Helligkeit',[['dunkel','Dunkel'],['hell','Hell']]],['akzent','Akzentfarbe'],['flaeche','Flächenfarbe'],['buehne','Um das Bild'],['dichte','Dichte',[[.8,'Eng'],[.85,'Dicht'],[1,'Normal'],[1.15,'Luftig']]],['ecken','Ecken',0,32,1,' px'],['strich','Umrisse',.1,2.6,.1,'×'],['regler','Regler',[['dreh','Drehregler'],['schieber','Schieber']]],['zahl','Große Zahl',[['an','An'],['aus','Aus']]],['vorschau','Vorschau',[['rund','Rund'],['eckig','Eckig']]]];
const komma=x=>(''+x).replace('.',',');
const anzeige=(r,v)=>Array.isArray(r[2])?(r[2].find(o=>o[0]==v)||['',v])[1]:r.length>3?komma(v)+r[5]:v;
const text=()=>{const w=W(),j=wahl.je[w.look]||{};return`Look ${w.n}: `+REG.map(r=>`${r[1]} ${anzeige(r,w[r[0]])}`).join(', ')+'. Geändert: '+(REG.filter(r=>j[r[0]]!==undefined).map(r=>r[1]).join(', ')||'nichts')+'.'};
const fam=s=>s=='Systemschrift'?'system-ui,sans-serif':`'${s}',sans-serif`,esc=s=>s.replace(/[&<>"']/g,c=>'&#'+c.charCodeAt(0)+';');
let eigen=null;
function schriftZ(v){const g={...(eigen||(wahl.google||[]).length?{Eigene:[...(eigen?[eigen]:[]),...(wahl.google||[])]}:{}),...GRUPPEN};
 return`<fieldset class="sw"><legend>Schriftart</legend><div class="sl">${Object.entries(g).map(([n,l])=>`<p>${n}</p>`+l.map(s=>`<label><input type="radio" name="schrift" value="${esc(s)}" ${s==v?'checked':''}><span style="font-family:${esc(fam(s))}">${esc(s)} <i>19,2 mm</i></span></label>`).join('')).join('')}</div></fieldset>
<form id="gf"><label for="gn">Weitere von Google Fonts, Name</label><div><input type="text" id="gn" autocomplete="off"><button>Laden</button></div></form><button id="sdk" class="sd">Eigene Schriftdatei öffnen</button><input type="file" id="sdat" accept=".ttf,.otf,.woff,.woff2" hidden><p id="sm" role="status"></p>`}
const gUrl=n=>'https://fonts.googleapis.com/css2?family='+encodeURIComponent(n).replace(/%20/g,'+')+':wght@400;500;600&display=swap';
function gLink(url){return new Promise((ja,nein)=>{const l=document.createElement('link');l.rel='stylesheet';l.href=url;l.onload=ja;l.onerror=()=>{l.remove();nein()};document.head.append(l)})}
const gLad=n=>gLink(gUrl(n)).catch(()=>gLink(gUrl(n).replace(':wght@400;500;600','')));
for(const n of wahl.google||[])gLad(n).catch(()=>{});
const setzS=s=>{(wahl.je[wahl.look]??={}).schrift=s;gestalte();feldZ();mal()};
document.getElementById('feld').addEventListener('submit',async e=>{e.preventDefault();const n=document.getElementById('gn').value.trim().replace(/['"\\<>;]/g,'');if(!n)return;const m=document.getElementById('sm');m.textContent='Lädt …';try{await gLad(n);await document.fonts.load(`16px '${n}'`);wahl.google=[...new Set([...(wahl.google||[]),n])];setzS(n);document.getElementById('sm').textContent=n+' geladen.'}catch(x){m.textContent=`„${n}“ nicht gefunden oder kein Netz. Schreibweise wie auf fonts.google.com.`}});
async function eigeneSchrift(n,f){const x=new FontFace(n,await f.arrayBuffer());await x.load();document.fonts.add(x);eigen=n}
document.getElementById('feld').addEventListener('change',async e=>{if(e.target.id!='sdat'||!e.target.files[0])return;const f=e.target.files[0],n=f.name.replace(/\.[^.]+$/,'').replace(/['"\\<>;,]/g,' ');try{await eigeneSchrift(n,f);let t=n+' geladen.';try{await db(s=>s.put({i:'schrift',n,f}))}catch(x){t+=' Gilt nur bis zum Neuladen.'}setzS(n);document.getElementById('sm').textContent=t}catch(x){document.getElementById('sm').textContent='Diese Datei lässt sich nicht als Schrift laden.'}});
function feldZ(){const w=W();document.getElementById('feld').innerHTML=`<h2>${w.n} anpassen</h2>`+REG.map(r=>{const i='s-'+r[0],v=w[r[0]];if(r[0]=='schrift')return schriftZ(v);return`<div class="z"><label for="${i}">${r[1]}</label>${Array.isArray(r[2])?`<select id="${i}">${r[2].map(o=>`<option value="${o[0]}" ${o[0]==v?'selected':''}>${o[1]}</option>`).join('')}</select>`:r.length>3?`<div class="s"><input id="${i}" type="range" min="${r[2]}" max="${r[3]}" step="${r[4]}" value="${v}"><output>${anzeige(r,v)}</output></div>`:`<input id="${i}" type="color" value="${v}">`}</div>`}).join('')+`<div class="kn"><button class="kop" id="kop">Wahl als Text kopieren</button><button id="zur">Diesen Look zurücksetzen</button><button id="allz">Alle Looks zurücksetzen</button></div><textarea id="wtext" readonly aria-label="Wahl als Text">${text()}</textarea>`}
function werteZ(){if(!document.getElementById('wtext'))return;const w=W();for(const r of REG){if(r[0]=='schrift')continue;const e=document.getElementById('s-'+r[0]);if(!e)return;e.value=w[r[0]];if(r.length>3)e.nextElementSibling.textContent=anzeige(r,w[r[0]])}document.getElementById('wtext').value=text()}
document.getElementById('looks').onclick=e=>{const b=e.target.closest('button');if(!b)return;wahl.look=b.dataset.l;gestalte();if(!document.getElementById('feld').hidden)feldZ();document.querySelector(`[data-l="${wahl.look}"]`).focus({preventScroll:true});mal()};
document.getElementById('anp').onclick=e=>{const f=document.getElementById('feld');f.hidden=!f.hidden;e.target.setAttribute('aria-expanded',!f.hidden);e.target.textContent=f.hidden?'Anpassen':'Schließen';if(!f.hidden){feldZ();const c=f.querySelector('.sl :checked');if(c){const l=f.querySelector('.sl');l.scrollTop=c.parentNode.offsetTop-l.offsetTop-60}}};
document.getElementById('feld').addEventListener('input',e=>{if(e.target.name=='schrift'){(wahl.je[wahl.look]??={}).schrift=e.target.value;gestalte();mal();return}const k=e.target.id.slice(2),r=REG.find(r=>r[0]==k);if(!r)return;const j=wahl.je[wahl.look]??={};
 if(k=='modus'){delete j.akzent;delete j.flaeche;delete j.buehne}j[k]=['fs','dichte','ecken','strich','gewicht','lauf'].includes(k)?+e.target.value:e.target.value;gestalte();mal()});
document.getElementById('feld').addEventListener('click',async e=>{const i=e.target.id;if(i=='sdk')document.getElementById('sdat').click();if(i=='zur'){delete wahl.je[wahl.look];gestalte();feldZ();mal()}if(i=='allz'){wahl.je={};gestalte();feldZ();mal()}
 if(i=='kop'){const t=document.getElementById('wtext');try{await navigator.clipboard.writeText(t.value);e.target.textContent='Kopiert'}catch(x){t.focus();t.select();e.target.textContent=document.execCommand('copy')?'Kopiert':'Text unten markiert: Strg C'}setTimeout(()=>{const k=document.getElementById('kop');if(k)k.textContent='Wahl als Text kopieren'},2500)}});
