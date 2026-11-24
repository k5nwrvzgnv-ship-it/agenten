/* Bedienung, für alle Looks gleich. Grundlage: werkbank-startansicht/index.html */
const $=i=>document.getElementById(i),B=DATEN.bilder,IDS=['153200004','153200015','153200022'];
const K={0:['Ast lebend','#00e0ea'],1:['Ast tot','#ff3fa4'],2:['Astloch','#a48dff'],3:['Ast mit Riss','#ff9a3d'],4:['Riss','#5c9dff'],6:['Harz','#6bea7f']},KL=Object.keys(K);
for(const i of IDS)B[i].src=i+'.jpg';
const KNOTEN=()=>W().look=='neurolign'||W().look=='ruhig',fix=x=>x.toFixed(1).replace('.',',').replace('-','−'),kl=(x,a,b)=>Math.max(a,Math.min(b,x));
const flae=p=>p.reduce((s,a,i)=>{const b=p[(i+1)%p.length];return s+a[0]*b[1]-b[0]*a[1]},0);
function ber(p,n){const L=[0];p.forEach((a,i)=>{const b=p[(i+1)%p.length];L.push(L[i]+Math.hypot(b[0]-a[0],b[1]-a[1]))});const o=[];let j=0;for(let k=0;k<n;k++){const t=L[p.length]*k/n;while(L[j+1]<t)j++;const a=p[j],b=p[(j+1)%p.length],f=(t-L[j])/((L[j+1]-L[j])||1);o.push([a[0]+f*(b[0]-a[0]),a[1]+f*(b[1]-a[1])])}return o}
const obj=(k,c,p)=>({k,c,b:ber(flae(p)<0?[...p].reverse():p,28),r:0,g:0,ok:false});
const st={};let halt={};try{halt=JSON.parse(localStorage.getItem('werkbank-looks')||'{}')}catch(e){}
function lade(i){const h=halt[i];st[i]=h?{o:h.o,zeit:h.zeit,dreck:false,h:[]}:{o:B[i].modell.map(o=>obj(o.k,o.c,o.p)),zeit:null,dreck:false,h:[]}}
IDS.forEach(lade);
let id=IDS[0],sel=-1,zeich=null,maus=null,zieh=null,pan=null,nur=false,V=null,uhr;
const name=i=>(B[i].name||i).replace(/[&<>"]/g,c=>'&#'+c.charCodeAt(0)+';');const S=()=>st[id],akt=()=>S().o[sel],ein=()=>B[id].px?'px':'mm',fak=()=>B[id].px||1;
function form(o){let p=o.b;for(let t=0;t<o.g;t++)p=p.map((a,j)=>{const n=p.length,v=p[(j+n-1)%n],w=p[(j+1)%n];return[a[0]*.5+(v[0]+w[0])*.25,a[1]*.5+(v[1]+w[1])*.25]});
 return p.map((a,j)=>{const n=p.length,v=p[(j+n-1)%n],w=p[(j+1)%n],x=w[0]-v[0],y=w[1]-v[1],l=Math.hypot(x,y)||1;return[kl(a[0]+o.r*y/l,0,B[id].lmm),kl(a[1]-o.r*x/l,0,B[id].qmm)]})}
const pfad=p=>{const n=p.length;return p.reduce((d,a,i)=>{const z=p[(i+n-1)%n],b=p[(i+1)%n],c=p[(i+2)%n];return d+`C${a[0]+(b[0]-z[0])/6} ${a[1]+(b[1]-z[1])/6} ${b[0]-(c[0]-a[0])/6} ${b[1]-(c[1]-a[1])/6} ${b[0]} ${b[1]}`},`M${p[0]}`)+'Z'};
function mass(p){let m={w:1e9},x=0;for(let g=0;g<180;g+=2){const u=[Math.cos(g*Math.PI/180),Math.sin(g*Math.PI/180)],q=p.map(a=>a[0]*u[0]+a[1]*u[1]),lo=Math.min(...q),hi=Math.max(...q);if(hi-lo<m.w)m={w:hi-lo,u,lo,hi};x=Math.max(x,hi-lo)}m.x=x;m.v=[-m.u[1],m.u[0]];const q=p.map(a=>a[0]*m.v[0]+a[1]*m.v[1]);m.m=(Math.min(...q)+Math.max(...q))/2;return m}
const angs=p=>p.some(a=>a[0]<.8||a[1]<.8||a[0]>B[id].lmm-.8||a[1]>B[id].qmm-.8);
const gr=p=>angs(p)?'am Rand':(mass(p).w*fak()).toFixed(ein()=='px'?0:1).replace('.',',')+' '+ein();
const folge=()=>S().o.map((o,i)=>i).sort((a,b)=>(S().o[a].c??2)-(S().o[b].c??2));
const bu_=i=>String.fromCharCode(65+folge().indexOf(i)),mitte=p=>[p.reduce((s,a)=>s+a[0],0)/p.length,p.reduce((s,a)=>s+a[1],0)/p.length];
const doppelt=i=>{const p=form(S().o[i]),m=mitte(p),w=mass(p).w;return S().o.findIndex((o,j)=>{if(j==i)return false;const q=form(o),n=mitte(q);return Math.hypot(m[0]-n[0],m[1]-n[1])<Math.min(w,mass(q).w)*.4})};
function merk(){const s=S();s.h.push(JSON.stringify([s.o,sel]));if(s.h.length>80)s.h.shift();s.dreck=true}
function sag(t,k,f){const h=$('hin');h.hidden=false;h.textContent=t;if(k){const b=document.createElement('button');b.textContent=k;b.onclick=()=>{h.hidden=true;f()};h.append(b)}clearTimeout(uhr);uhr=setTimeout(()=>h.hidden=true,5000)}
/* Bild */
function ganz(){V=[0,0,B[id].lmm,B[id].qmm]}
function zoom(f,x,y){x??=V[0]+V[2]/2;y??=V[1]+V[3]/2;const w=kl(V[2]*f,12,B[id].lmm),q=w/V[2];V=[kl(x-(x-V[0])*q,0,B[id].lmm-w),kl(y-(y-V[1])*q,0,B[id].qmm-V[3]*q),w,V[3]*q];bildZ()}
function bildZ(){const sv=$('bild');sv.setAttribute('viewBox',V.join(' '));const r=sv.getBoundingClientRect(),z=Math.max(V[2]/r.width,V[3]/r.height)||.1;let s=`<image href="${B[id].src}" width="${B[id].lmm}" height="${B[id].qmm}" preserveAspectRatio="none"/>`;
 if(!nur){S().o.forEach((o,i)=>{const a=i==sel,p=form(o),f=K[o.k][1];s+=`<path class="o" data-o="${i}" d="${pfad(p)}" fill="${f}" fill-opacity="${a?.06:.16}" stroke="#000a" stroke-width="${((a?2.5:1.8)*STRICH()+2)*z}"/><path d="${pfad(p)}" fill="none" stroke="${f}" stroke-width="${(a?2.500:1.800)*z*STRICH()}" pointer-events="none"/>`;
 if(a&&!zeich){if(!angs(p)){const m=mass(p),P=x=>[m.u[0]*x+m.v[0]*m.m,m.u[1]*x+m.v[1]*m.m],A=P(m.lo),E=P(m.hi);s+=`<path d="M${A}L${E}" stroke="#000a" stroke-width="${3.500*z}" pointer-events="none"/><path d="M${A}L${E}" stroke="#fff" stroke-width="${1.500*z}" pointer-events="none"/>`}
 p.forEach((q,j)=>{if(j%2==0)s+=`<rect x="${q[0]-3.8*z}" y="${q[1]-3.8*z}" width="${7.6*z}" height="${7.6*z}" rx="${KNOTEN()?3.8*z:0}" fill="#fff" stroke="#000" stroke-width="${z}" pointer-events="none"/><circle class="pk" data-p="${j}" cx="${q[0]}" cy="${q[1]}" r="${10*z}" fill="transparent"/>`});
 const ob=Math.min(...p.map(q=>q[1])),re=Math.max(...p.map(q=>q[0])),li=Math.min(...p.map(q=>q[0])),t=`${bu_(i)} ${K[o.k][0]}, ${gr(p)}`,rx=re+12*z+t.length*8.500*z<V[0]+V[2]?re+12*z:li-12*z,anc=rx>li?'start':'end';s+=`<text x="${rx}" y="${ob+14*z}" text-anchor="${anc}" font-size="${15*z}" stroke-width="${4*z}">${t}</text>`}});
 if(!zeich){S().o.forEach((o,i)=>{if(i==sel)return;const p=form(o),l=Math.min(...p.map(q=>q[0])),re=Math.max(...p.map(q=>q[0])),u=Math.max(...p.map(q=>q[1])),d=doppelt(i);const x=(l+re)/2,y=d>=0?(u+20*z):(Math.min(...p.map(q=>q[1]))+u)/2+5*z;s+=`<text x="${x}" y="${y}" text-anchor="middle" font-size="${15*z}" stroke-width="${4*z}">${bu_(i)}</text>`})}
 if(zeich&&zeich.length){s+=`<polyline points="${[...zeich,maus||zeich.at(-1)].join(' ')}" fill="none" stroke="#000" stroke-width="${4*z}"/><polyline points="${[...zeich,maus||zeich.at(-1)].join(' ')}" fill="none" stroke="#fff" stroke-width="${2*z}"/>`;zeich.forEach((q,i)=>s+=`<circle cx="${q[0]}" cy="${q[1]}" r="${(i?4:7)*z}" fill="#fff" stroke="#000" stroke-width="${z}"/>`)}}
 sv.innerHTML=s;sv.classList.toggle('zeichnen',!!zeich);$('fit').disabled=V[2]>=B[id].lmm-.01}
/* Liste */
const mx=p=>ein()=='px'?Math.round(mass(p).x*fak())+' px':fix(mass(p).x)+' mm';
const warnung=dp=>dp>=0?`<p class="dp">Liegt auf ${bu_(dp)}. Eins von beiden löschen.</p>`:'';
function detail(){const d=$('detail');d.hidden=INL();if(INL()){d.innerHTML='';return}const o=akt();d.classList.toggle('voll',!!o);if(!o){d.innerHTML=`<p class="leer">${S().o.length?(S().o.every(o=>o.ok)?'Alle Objekte geprüft.':'Objekt im Bild oder in der Liste wählen.'):'Kein Objekt im Bild.'}</p>`;return}const p=form(o);d.style.setProperty('--kf',K[o.k][1]);d.innerHTML=`<p class="dk"><b>${bu_(sel)}</b><span class="fb" style="background:${K[o.k][1]}"></span>${K[o.k][0]}</p>`+warnung(doppelt(sel))+ed(o,p)}
function zeile(i){const o=S().o[i],p=form(o),a=i==sel,dp=doppelt(i),s=o.ok?['geprüft','ok']:o.c===null?['neu','']:[`KI ${Math.round(o.c*100)} %`,o.c<.7?'un':''];
 return`<li class="${a?'an':''}" style="--kf:${K[o.k][1]}"><button class="zl" data-i="${i}" aria-expanded="${a}"><b>${bu_(i)}</b><span class="fb" style="background:${K[o.k][1]}"></span><span class="nm">${K[o.k][0]}</span><span class="gr">${gr(p)}</span><span class="mx">${angs(p)?'':'max '+mx(p)}</span><span class="st ${s[1]}">${s[0]}</span></button>${a&&INL()?warnung(dp)+ed(o,p):''}</li>`}
const zahl=p=>angs(p)?'<div class="zahl wort">am Rand</div>':`<div class="zahl">${gr(p).replace(/ (..)$/,'<small>$1</small>')}</div>`;
const neben=(o,p)=>`${angs(p)?'<span>angeschnitten</span>':`<span>max <b>${mx(p)}</b></span>`}${o.c===null?'':`<span>KI <b>${Math.round(o.c*100)} %</b></span>`}`;
function rad(v,lo,hi,txt){const w=x=>(-225+270*(x-lo)/(hi-lo))*Math.PI/180,pt=x=>[60+Math.cos(w(x))*46,60+Math.sin(w(x))*46],bo=(a,b,c)=>`<path d="M${pt(a)}A46 46 0 ${270*(b-a)/(hi-lo)>180?1:0} 1 ${pt(b)}" fill="none" stroke="${c}" stroke-width="6" stroke-linecap="round"/>`,n=Math.max(lo,0),k=pt(v);return bo(lo,hi,'var(--linie)')+(v!=n?bo(Math.min(v,n),Math.max(v,n),'var(--akzt)'):'')+`<circle cx="${k[0]}" cy="${k[1]}" r="10" fill="var(--text)"/><text x="60" y="67" text-anchor="middle" font-size="22">${txt}</text>`}
const radR=o=>rad(o.r,-4,4,wr(o).replace(/ ..$/,'')),radG=o=>rad(o.g,0,8,o.g);
function ed(o,p){const m=mass(p),e=ein()=='px'?x=>Math.round(x*fak())+' px':x=>fix(x)+' mm',w=W(),D=w.regler=='dreh';return`<div class="ed">${w.zahl=='an'?`<div class="gz">${zahl(p)}</div><div class="neben">${neben(o,p)}</div>`:''}
${D?`<div class="raeder"><div class="rad"><svg data-r="r" viewBox="0 0 120 112" aria-hidden="true">${radR(o)}</svg><input id="r" type="range" min="-4" max="4" step="0.1" value="${o.r}" aria-label="Größe"><span>Größe</span></div><div class="rad"><svg data-r="g" viewBox="0 0 120 112" aria-hidden="true">${radG(o)}</svg><input id="g" type="range" min="0" max="8" step="1" value="${o.g}" aria-label="Glätten"><span>Glätten</span></div></div>`:''}
<fieldset class="kl" aria-label="Klasse">${KL.map((k,n)=>`<label><input type="radio" name="kl" value="${k}" ${k==o.k?'checked':''}><span class="fb" style="background:${K[k][1]}"></span>${K[k][0]}<kbd>${n+1}</kbd></label>`).join('')}</fieldset>
${D?'':`<div class="rg"><label for="r">Größe</label><input id="r" type="range" min="-4" max="4" step="0.1" value="${o.r}"><output id="rv">${wr(o)}</output></div>
<details ${window.mehr?'open':''}><summary>Glätten und Maße</summary><div class="rg"><label for="g">Glätten</label><input id="g" type="range" min="0" max="8" step="1" value="${o.g}"><output id="gv">${o.g}</output></div><dl><dt>Kleinster Durchmesser</dt><dd>${angs(p)?'angeschnitten':e(m.w)}</dd><dt>Größter Durchmesser</dt><dd>${angs(p)?'angeschnitten':e(m.x)}</dd></dl></details>`}
<div class="akt"><button class="k gut" id="gut">${o.ok?'Nächstes Objekt':'Stimmt'}<kbd class="nurbreit">Enter</kbd></button><button class="lo" id="lo" aria-label="Objekt löschen"><svg class="i" viewBox="0 0 24 24"><path d="M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13"/></svg></button></div></div>`}
const wr=o=>(o.r>0?'+':'')+(B[id].px?Math.round(o.r*fak())+' px':fix(o.r)+' mm');
function liste(){const s=S(),n=s.o.length,g=s.o.filter(o=>o.ok).length,li=$('liste'),y=li.scrollTop;li.innerHTML=n?folge().map(zeile).join(''):`<li class="leer">${B[id].px?'Kein Vorlabel: Das Modell läuft in diesem Entwurf nicht. Umriss mit Zeichnen anlegen.':'Keine Objekte. Mit Zeichnen anlegen oder leer speichern.'}</li>`;li.scrollTop=y;detail();$('stand').textContent=n?`${g} von ${n} geprüft`:'';fuss()}
function fuss(){const s=S(),n=IDS.indexOf(id);const of=s.o.filter(o=>!o.ok).length;$('sp').classList.toggle('voll',!of);$('gutm').hidden=!akt()||akt().ok;$('spt').textContent=(of?`${of} offen. `:'')+(s.dreck?'Nicht gespeicherte Änderungen':s.zeit?`Gespeichert um ${s.zeit}, nur ${B[id].px&&!B[id].fest?'bis zum Neuladen':'in diesem Browser'}`:'Noch nicht gespeichert');$('rueck').disabled=!s.h.length;$('pos').innerHTML=`<b>${name(id)}</b>, ${n+1} von ${IDS.length}`;$('vor').disabled=!n;$('nach').disabled=n==IDS.length-1;
 $('film').innerHTML=IDS.map((i,j)=>{const t=st[i],w=t.dreck?'geändert':t.zeit?'gespeichert':t.o.length?`${t.o.filter(o=>!o.ok).length} offen`:'leer';return`<button data-i="${i}" title="${name(i)}" ${i==id?'aria-current="true"':''}><i><img src="${B[i].src}" alt=""><b aria-hidden="true">${t.o.filter(o=>!o.ok).length||'✓'}</b></i><span>${name(i)}<small class="${w=='gespeichert'?'ok':''}">${w}</small></span></button>`}).join('')}
const mal=()=>{bildZ();liste()};
function waehle(i,hin){sel=i;mal();const z=document.querySelector('li.an');if(z&&innerWidth>860)z.scrollIntoView({block:'nearest'});if(hin){const b=document.querySelector('li.an .zl');b&&b.focus({preventScroll:true})}}
function oeffne(i){id=i;zeich=null;werk();ganz();const f=folge().find(j=>!S().o[j].ok);sel=f??-1;mal()}
const SE=document.querySelector('.seite');
/* Aktionen */
function werk(){$('neu').setAttribute('aria-pressed',!!zeich);$('waehl').setAttribute('aria-pressed',!zeich)}
function zeichnen(an){zeich=an?[]:null;maus=null;if(an){sel=-1;nur=false;$('aus').setAttribute('aria-pressed',false);sag('Punkte um die Stelle setzen. Zum Schließen den ersten Punkt anklicken.')}else $('hin').hidden=true;werk();mal()}
function schliess(){if(zeich.length<3)return zeichnen(false);merk();const s=S();s.o.push(obj(1,null,zeich));zeichnen(false);waehle(s.o.length-1)}
function gut(){const o=akt();if(!o)return;if(!o.ok){merk();o.ok=true}const f=folge().find(j=>!S().o[j].ok);if(f===undefined){waehle(-1);sag('Alle Objekte geprüft.','Speichern und weiter',speich)}else waehle(f,true)}
function loesch(){if(!akt())return;merk();const n=K[akt().k][0];S().o.splice(sel,1);waehle(-1);sag(n+' gelöscht.','Rückgängig',rueck)}
function rueck(){const h=S().h.pop();if(h){[S().o,sel]=JSON.parse(h);if(sel>=S().o.length)sel=-1;mal()}}
function setK(k){if(akt()){merk();akt().k=+k;mal()}}
function setR(d){const o=akt();if(!o)return;merk();o.r=Math.round(kl(o.r+d,-4,4)*10)/10;mal()}
function speich(){const s=S();s.zeit=new Date().toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'});s.dreck=false;s.h=[];if(!B[id].px||B[id].fest){halt[id]={o:s.o,zeit:s.zeit};try{localStorage.setItem('werkbank-looks',JSON.stringify(halt))}catch(e){}}
 const n=B[id].name||id,off=IDS.find(i=>!st[i].zeit);const t=`${n} gespeichert.`;if(off&&off!=id)oeffne(off);else mal();sag(off?t:t+' Alle Bilder fertig.')}
SE.addEventListener('click',e=>{if(e.target.closest('#gut'))return gut();if(e.target.closest('#lo'))return loesch();const b=e.target.closest('.zl');if(b)waehle(+b.dataset.i==sel?-1:+b.dataset.i,true)});
SE.addEventListener('change',e=>{if(e.target.name=='kl'){const v=e.target.value;setK(v);document.querySelector(`.kl input[value="${v}"]`).focus()}});
let gem=null;SE.addEventListener('input',e=>{const t=e.target;if(t.id!='r'&&t.id!='g')return;if(gem!==t){merk();gem=t}const o=akt();o[t.id]=+t.value;if($('rv'))$('rv').textContent=wr(o);if($('gv'))$('gv').textContent=o.g;const R=SE.querySelector('[data-r=r]'),G=SE.querySelector('[data-r=g]');if(R){R.innerHTML=radR(o);G.innerHTML=radG(o)}const pf=form(o),Z=SE.querySelector('.gz');if(Z){Z.innerHTML=zahl(pf);SE.querySelector('.neben').innerHTML=neben(o,pf)}bildZ();fuss();document.querySelector('li.an .zl .gr').textContent=gr(form(o))});
SE.addEventListener('change',e=>{if(e.target.type=='range')gem=null});
/* Drehregler: ziehen verstellt, Doppelklick stellt auf null; Tastatur über das unsichtbare Eingabefeld */
let dreh=null;const stell=(i,v)=>{const el=$(i);el.value=v;el.dispatchEvent(new Event('input',{bubbles:true}))};
SE.addEventListener('pointerdown',e=>{const s=e.target.closest('[data-r]');if(!s)return;e.preventDefault();dreh={i:s.dataset.r,x:e.clientX-e.clientY,v:akt()[s.dataset.r]};s.setPointerCapture(e.pointerId);$(dreh.i).focus({focusVisible:false})});
SE.addEventListener('pointermove',e=>{if(dreh)stell(dreh.i,dreh.v+(e.clientX-e.clientY-dreh.x)/160*8)});
for(const t of['pointerup','pointercancel'])SE.addEventListener(t,()=>{if(dreh){dreh=null;gem=null;liste()}});
SE.addEventListener('dblclick',e=>{const s=e.target.closest('[data-r]');if(s){stell(s.dataset.r,0);gem=null;liste()}});
SE.addEventListener('wheel',e=>{const s=e.target.closest('[data-r]');if(s){e.preventDefault();stell(s.dataset.r,akt()[s.dataset.r]+(e.deltaY<0?1:-1)*(s.dataset.r=='r'?.1:1))}},{passive:false});
SE.addEventListener('toggle',e=>{if(e.target.tagName=='DETAILS')window.mehr=e.target.open},true);
$('neu').onclick=()=>zeichnen(!zeich);$('waehl').onclick=()=>zeichnen(false);$('rueck').onclick=rueck;$('plus').onclick=()=>{const o=akt(),p=o&&form(o);o?zoom(.6,p.reduce((s,a)=>s+a[0],0)/p.length,p.reduce((s,a)=>s+a[1],0)/p.length):zoom(.6)};$('fit').onclick=()=>{ganz();bildZ()};$('aus').onclick=()=>{nur=!nur;$('aus').setAttribute('aria-pressed',nur);bildZ()};
$('vor').onclick=()=>oeffne(IDS[IDS.indexOf(id)-1]);$('nach').onclick=()=>oeffne(IDS[IDS.indexOf(id)+1]);$('film').onclick=e=>{const b=e.target.closest('button');if(b)oeffne(b.dataset.i)};$('sp').onclick=speich;$('gutm').onclick=gut;
/* Zeiger */
const sv=$('bild'),ort=e=>{const q=new DOMPoint(e.clientX,e.clientY).matrixTransform(sv.getScreenCTM().inverse());return[q.x,q.y]};
sv.onpointerdown=e=>{const a=ort(e),d=e.target.dataset;if(zeich){const z=sv.getScreenCTM().a;if(zeich.length>2&&Math.hypot(a[0]-zeich[0][0],a[1]-zeich[0][1])*z<14)return schliess();zeich.push(a);return bildZ()}
 if(d.p!==undefined){merk();const o=akt();o.b=form(o);o.r=0;o.g=0;zieh={j:+d.p,a,s:o.b.map(q=>[...q])};sv.setPointerCapture(e.pointerId);return}
 if(d.o!==undefined&&+d.o!=sel)return waehle(+d.o);pan={x:e.clientX,y:e.clientY,v:[...V],w:false,leer:d.o===undefined};sv.setPointerCapture(e.pointerId)};
sv.onpointermove=e=>{if(zeich){maus=ort(e);if(zeich.length)bildZ();return}if(zieh){const a=ort(e),o=akt(),n=o.b.length;o.b=zieh.s.map((q,i)=>{let t=Math.abs(i-zieh.j);t=Math.min(t,n-t);const f=Math.exp(-t*t/3);return[kl(q[0]+f*(a[0]-zieh.a[0]),0,B[id].lmm),kl(q[1]+f*(a[1]-zieh.a[1]),0,B[id].qmm)]});return bildZ()}
 if(pan){const z=sv.getScreenCTM().a,dx=(e.clientX-pan.x)/z,dy=(e.clientY-pan.y)/z;if(Math.hypot(dx,dy)*z>4)pan.w=true;if(pan.w){V=[kl(pan.v[0]-dx,0,Math.max(0,B[id].lmm-V[2])),kl(pan.v[1]-dy,0,Math.max(0,B[id].qmm-V[3])),V[2],V[3]];bildZ()}}};
sv.onpointerup=sv.onpointercancel=()=>{if(zieh){zieh=null;liste()}else if(pan){const p=pan;pan=null;if(!p.w&&p.leer&&sel>=0)waehle(-1)}};
sv.addEventListener('wheel',e=>{e.preventDefault();const u=(e.deltaY||e.deltaX)<0;if(e.shiftKey)return setR(u?.1:-.1);const a=ort(e);zoom(u?.85:1/.85,a[0],a[1])},{passive:false});
addEventListener('keydown',e=>{if(e.target.closest&&e.target.closest('#leiste,#feld'))return;const t=e.target,fe=t.matches&&t.matches('input[type=range]');if(document.querySelector(':popover-open'))return;if((e.ctrlKey||e.metaKey)&&e.key=='z'){e.preventDefault();return rueck()}if(e.ctrlKey||e.metaKey||e.altKey)return;
 if(e.key=='Escape'&&zeich)return zeichnen(false);if(e.key=='Enter'){if(zeich){e.preventDefault();return schliess()}if(t==document.body||t.closest&&t.closest('li.an,#detail')&&!t.closest('#lo')&&!t.closest('summary')){e.preventDefault();return gut()}return}
 const k=KL[+e.key-1];if(k&&akt())return setK(k);if(fe)return;if(e.key=='Delete'||e.key=='Backspace')loesch();if(e.key=='+')setR(.1);if(e.key=='-')setR(-.1);if(e.key=='n')zeichnen(!zeich);if(e.key=='s')speich()});
/* Bilder hinein */
$('rein').onclick=()=>$('datei').click();$('datei').onchange=e=>rein(e.target.files);
const db=f=>new Promise((ja,nein)=>{try{const q=indexedDB.open('werkbank-looks',1);q.onupgradeneeded=()=>q.result.createObjectStore('b',{keyPath:'i'});q.onerror=nein;q.onsuccess=()=>{const t=q.result.transaction('b','readwrite'),r=f(t.objectStore('b'));t.oncomplete=()=>ja(r&&r.result);t.onerror=nein}}catch(e){nein(e)}});
const dazu=(i,n,f)=>new Promise(ja=>{const u=URL.createObjectURL(f),im=new Image;im.onerror=()=>ja(false);im.onload=()=>{B[i]={src:u,name:n.length>22?n.slice(0,19)+'…':n,lmm:168,qmm:168*im.naturalHeight/im.naturalWidth,px:im.naturalWidth/168,modell:[]};IDS.push(i);lade(i);ja(true)};im.src=u});
async function rein(fs){let erst;for(const f of fs){if(!f.type.startsWith('image/'))continue;const i='n'+Date.now()+Math.random();if(!await dazu(i,f.name,f)){sag(f.name+' lässt sich nicht öffnen.');continue}try{await db(s=>s.put({i,n:f.name,f}));B[i].fest=true}catch(e){sag('Bild bleibt nur bis zum Neuladen, der Browser erlaubt kein Ablegen.')}if(!erst){erst=i;oeffne(i)}else fuss()}$('datei').value=''}
const bu=document.querySelector('.buehne');bu.ondragover=e=>{e.preventDefault();bu.classList.add('ziel')};bu.ondragleave=()=>bu.classList.remove('ziel');bu.ondrop=e=>{e.preventDefault();bu.classList.remove('ziel');rein(e.dataTransfer.files)};
new ResizeObserver(()=>V&&bildZ()).observe(sv);gestalte();oeffne(IDS.find(i=>!st[i].zeit)||IDS[0]);
db(s=>s.getAll()).then(async a=>{for(const x of a||[])if(await dazu(x.i,x.n,x.f))B[x.i].fest=true;if(st[id].zeit&&!st[id].dreck)oeffne(IDS.find(i=>!st[i].zeit)||id);else fuss()}).catch(()=>{});
matchMedia('(max-width:860px)').addEventListener('change',()=>mal());

new ResizeObserver(e=>$('app').toggleAttribute('data-eng',e[0].contentRect.width<1250)).observe($('app'));
