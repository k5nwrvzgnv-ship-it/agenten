/* Geometrie, Maße, Doppelerkennung und Speichern nach werkbank-looks/bedienung.js, Oberfläche neu. */
'use strict';
const $=i=>document.getElementById(i),B={};let IDS=[];
/* Klasse: Name, Farbe, Strichmuster (zweites Merkmal neben der Farbe). Liste kommt aus klassen.json (/api/klassen),
   änderbar unter Klassen bearbeiten. Eine Farbe je Gruppe (Jan 25.11.2026), je Klasse überschreibbar; die letzte Gruppe
   ist eingeklappt. Gelöschte Klassen bleiben in K, damit alte Objekte bis zum Neuladen zeichnen. */
let K={},GRUPPEN=[],KL=[],HAUPT=0,KD=null,ICH='mac';
const GF=n=>KF(n<6?[0,3,1,4,5,2][n]:n);
function klassenSetzen(d){KD=d;ICH=d.ich||ICH;K={};const g=d.gruppen;GRUPPEN=g.map(n=>d.klassen.filter(k=>k.aktiv&&k.gruppe==n).map(k=>k.id));
 for(const k of d.klassen){const n=g.indexOf(k.gruppe);K[k.id]=[k.name,'',k.muster||''];Object.defineProperty(K[k.id],1,{get:()=>k.farbe||GF(n<0?0:n)})}
 KL=GRUPPEN.flat().map(String);HAUPT=GRUPPEN.length>1?KL.length-GRUPPEN.at(-1).length:KL.length}
const DUNKEL='#111318';
const kl=(x,a,b)=>Math.max(a,Math.min(b,x)),fix=x=>x.toFixed(1).replace('.',',').replace('-','−'),esc=s=>String(s).replace(/[&<>"]/g,c=>'&#'+c.charCodeAt(0)+';');
const ic=n=>`<svg class="i" aria-hidden="true"><use href="#i-${n}"/></svg>`,muster=k=>`<svg class="mu" viewBox="0 0 24 8" aria-hidden="true"><path d="M0 4H24" stroke="${K[k][1]}" stroke-width="${Math.max(2,Math.min(4,W().strich*1.6))}" ${K[k][2]&&W().muster=='an'?`stroke-dasharray="${K[k][2]}"`:''}/></svg>`;
const flae=p=>p.reduce((s,a,i)=>{const b=p[(i+1)%p.length];return s+a[0]*b[1]-b[0]*a[1]},0);
function ber(p,n){const L=[0];p.forEach((a,i)=>{const b=p[(i+1)%p.length];L.push(L[i]+Math.hypot(b[0]-a[0],b[1]-a[1]))});const o=[];let j=0;for(let k=0;k<n;k++){const t=L[p.length]*k/n;while(j<p.length-1&&L[j+1]<t)j++;const a=p[j],b=p[(j+1)%p.length],f=(t-L[j])/((L[j+1]-L[j])||1);o.push([a[0]+f*(b[0]-a[0]),a[1]+f*(b[1]-a[1])])}return o}
const obj=(k,c,p)=>({k,c,b:ber(flae(p)<0?[...p].reverse():p,kl(Math.round(p.reduce((s,a,i)=>{const q=p[(i+1)%p.length];return s+Math.hypot(q[0]-a[0],q[1]-a[1])},0)/B[id].lmm*80),28,120)),r:0,g:0,ok:false});
const st={};
let letzte=1,id=null,sel=-1,pkt=0,zeich=null,maus=null,zieh=null,pan=null,nur=false,mehr=false,auf=false,messAuf=false,V=null,uhr,tab='liste';
const S=()=>st[id],akt=()=>S().o[sel],px=()=>!!B[id].px,name=i=>B[i].name||i,offen=i=>st[i].o.filter(o=>!o.ok).length;
function form(o){let p=o.b;for(let t=0;t<o.g;t++)p=p.map((a,j)=>{const n=p.length,v=p[(j+n-1)%n],w=p[(j+1)%n];return[a[0]*.5+(v[0]+w[0])*.25,a[1]*.5+(v[1]+w[1])*.25]});
 return p.map((a,j)=>{const n=p.length,v=p[(j+n-1)%n],w=p[(j+1)%n],x=w[0]-v[0],y=w[1]-v[1],l=Math.hypot(x,y)||1;return[kl(a[0]+o.r*y/l,0,B[id].lmm),kl(a[1]-o.r*x/l,0,B[id].qmm)]})}
const pfad=p=>{const n=p.length;return p.reduce((d,a,i)=>{const z=p[(i+n-1)%n],b=p[(i+1)%n],c=p[(i+2)%n];return d+`C${a[0]+(b[0]-z[0])/6} ${a[1]+(b[1]-z[1])/6} ${b[0]-(c[0]-a[0])/6} ${b[1]-(c[1]-a[1])/6} ${b[0]} ${b[1]}`},`M${p[0]}`)+'Z'};
function mass(p){let m={w:1e9},x=0;for(let g=0;g<180;g+=2){const u=[Math.cos(g*Math.PI/180),Math.sin(g*Math.PI/180)],q=p.map(a=>a[0]*u[0]+a[1]*u[1]),lo=Math.min(...q),hi=Math.max(...q);if(hi-lo<m.w)m={w:hi-lo,u,lo,hi};x=Math.max(x,hi-lo)}m.x=x;m.v=[-m.u[1],m.u[0]];const q=p.map(a=>a[0]*m.v[0]+a[1]*m.v[1]);m.m=(Math.min(...q)+Math.max(...q))/2;return m}
const angs=p=>p.some(a=>a[0]<.8||a[1]<.8||a[0]>B[id].lmm-.8||a[1]>B[id].qmm-.8);
const wert=x=>px()?Math.round(x*B[id].px)+' px':fix(x)+' mm',gr=p=>angs(p)?'am Rand':wert(mass(p).w),wr=o=>(o.r>0?'+':'')+wert(o.r);
const folge=()=>S().o.map((o,i)=>i).sort((a,b)=>(S().o[a].c??2)-(S().o[b].c??2)),bu=i=>{const n=folge().indexOf(i);return String.fromCharCode(65+n%26)+(n>25?Math.floor(n/26):'')};
const mitte=p=>[p.reduce((s,a)=>s+a[0],0)/p.length,p.reduce((s,a)=>s+a[1],0)/p.length];
const doppelt=i=>{const p=form(S().o[i]),m=mitte(p),w=mass(p).w;return S().o.findIndex((o,j)=>{if(j==i)return false;const q=form(o),n=mitte(q);return Math.hypot(m[0]-n[0],m[1]-n[1])<Math.min(w,mass(q).w)*.4})};
const streit=i=>{if(i<0)return-1;const d=doppelt(i);return d>=0&&!S().o[i].ok&&!S().o[d].ok?d:-1};
const erstes=()=>folge().find(j=>!S().o[j].ok)??-1;
function merk(){fwegZuletzt=gzurZuletzt=false;const s=S();s.h.push(JSON.stringify([s.o,sel]));if(s.h.length>80)s.h.shift();s.v=[];s.dreck=true}
function sag(t,k,f,bleibt){$('hin').hidden=false;$('hint').textContent=t;$('hink').hidden=!k;$('hink').innerHTML=k?ic({Rückgängig:'arrow-counter-clockwise',Schließen:'check'}[k]||'arrow-left')+`<span class="vs">${k}</span>`:'';$('hink').title=k||'';$('hink').onclick=()=>{stumm();f&&f()};clearTimeout(uhr);if(!bleibt)uhr=setTimeout(stumm,5000)}
function stumm(){$('hin').hidden=true;clearTimeout(uhr)}
function fehler(t){$('fehl').hidden=false;$('fehlt').textContent=t}$('fehlz').onclick=()=>$('fehl').hidden=true;
/* Bild */
const voll=()=>V[2]>=B[id].lmm-.01;
function ganz(){V=[0,0,B[id].lmm,B[id].qmm]}
function rand(){V[0]=kl(V[0],0,Math.max(0,B[id].lmm-V[2]));V[1]=kl(V[1],0,Math.max(0,B[id].qmm-V[3]))}
function zoom(f,x,y){x??=V[0]+V[2]/2;y??=V[1]+V[3]/2;const w=kl(V[2]*f,12,B[id].lmm),q=w/V[2];V=[x-(x-V[0])*q,y-(y-V[1])*q,w,V[3]*q];rand();bildZ()}
function schwenk(x,y){V[0]+=x*V[2]*.15;V[1]+=y*V[3]*.15;rand();bildZ()}
function bildZ(){const sv=$('bild'),r=sv.getBoundingClientRect();if(!r.width||!r.height)return;sv.setAttribute('viewBox',V.join(' '));const z=Math.max(V[2]/r.width,V[3]/r.height),T=matchMedia('(pointer:coarse)').matches;
 const w=W(),sw=w.strich;let s=`<image href="${B[id].src}" width="${B[id].lmm}" height="${B[id].qmm}" preserveAspectRatio="none"/>`,tags='';
 const tag=(x,y,t,f,anker)=>{if(w.schild=='aus')return'';const k=w.sgr/13,h=20*k*z,c=document.createElement.ctx||=document.createElement('canvas').getContext('2d');c.font=`600 ${w.sgr}px ${getComputedStyle(document.documentElement).getPropertyValue('--font-heading')}`;const b=(c.measureText(t).width+12*k)*z;x=kl(anker=='m'?x-b/2:x,V[0],Math.max(V[0],V[0]+V[2]-b));y=kl(y,V[1],V[1]+V[3]-h);const ka=w.schild=='kasten';return`<g pointer-events="none">${ka?`<rect x="${x}" y="${y}" width="${b}" height="${h}" rx="${Math.min(w.ecken,10)*z}" fill="${DUNKEL}" stroke="${f}" stroke-width="${z}"/>`:''}<text x="${x+6*k*z}" y="${y+14.5*k*z}" font-size="${w.sgr*z}" fill="${ka?'#E5E7EB':'#fff'}" ${ka?'':`stroke="#000" stroke-width="${4*z}" paint-order="stroke" stroke-linejoin="round"`}>${t}</text></g>`};
 if(!nur){const G_=grp(),reihe=S().o.map((o,i)=>i).sort((a,b)=>(a==sel||mw.has(S().o[a]))-(b==sel||mw.has(S().o[b])));for(const i of reihe){const o=S().o[i],a=i==sel&&!G_,h=a||G_&&mw.has(o),p=form(o),f=K[o.k][1],d=pfad(p),da=K[o.k][2]&&w.muster=='an'?`stroke-dasharray="${K[o.k][2].split(' ').map(x=>x*z).join(' ')}"`:'';
 s+=`<path class="o" data-o="${i}" d="${d}" fill="${f}" fill-opacity="${h?w.fuell*.4:w.fuell}" stroke="${h?W().auswahl:DUNKEL}" stroke-width="${(h?sw+1.500*w.saum+2*w.ring:sw+2.500*w.saum)*z}"/>${h?`<path d="${d}" fill="none" stroke="${DUNKEL}" stroke-width="${(sw+1.500*w.saum)*z}" pointer-events="none"/>`:''}<path d="${d}" fill="none" stroke="${f}" stroke-width="${sw*z}" ${da} pointer-events="none"/>`;
 const xs=p.map(q=>q[0]),ys=p.map(q=>q[1]),li=Math.min(...xs),re=Math.max(...xs),ob=Math.min(...ys),un=Math.max(...ys);
 if(!a)tags+=tag((li+re)/2,doppelt(i)>=0?un+8*z:ob-26*z,bu(i)+(o.ok?' ✓':''),f,'m');
 else if(!zeich){if(w.linieM=='an'&&!angs(p)){const m=mass(p),P=x=>[m.u[0]*x+m.v[0]*m.m,m.u[1]*x+m.v[1]*m.m],A=P(m.lo),E=P(m.hi);s+=`<path d="M${A}L${E}" stroke="${DUNKEL}" stroke-width="${(w.mlin+2.500*w.saum)*z}" pointer-events="none"/><path d="M${A}L${E}" stroke="${W().auswahl}" stroke-width="${w.mlin*z}" pointer-events="none"/>`}
  const dp=streit(i);if(dp>=0)s+=`<path d="${pfad(form(S().o[dp]))}" fill="none" stroke="${K[S().o[dp].k][1]}" stroke-width="${sw*z}" stroke-dasharray="${6*z} ${8*z}" pointer-events="none"/>`;
  p.forEach((q,j)=>{const hier=auf&&j==pkt;if(j%(T?4:2)&&!hier)return;const g=hier?w.pgr+3:w.pgr;if(w.punkte!='aus'||hier)s+=`<rect x="${q[0]-g*z}" y="${q[1]-g*z}" width="${2*g*z}" height="${2*g*z}" rx="${w.punkte=='rund'?g*z:0}" fill="${hier?W().akzent:W().auswahl}" stroke="${DUNKEL}" stroke-width="${z}" pointer-events="none"/><circle class="pk" data-p="${j}" cx="${q[0]}" cy="${q[1]}" r="${(T?16:11)*z}" fill="transparent"/>`});
  tags+=tag((li+re)/2,ob-32*z<V[1]?un+12*z:ob-32*z,w.schild=='kurz'?bu(i):`${bu(i)} ${K[o.k][0]}, ${gr(p)}`,W().auswahl,'m')}}
 s+=tags;
 if(zeich&&zeich.length){const l=[...zeich,maus||zeich.at(-1)].join(' ');s+=`<polyline points="${l}" fill="none" stroke="${DUNKEL}" stroke-width="${(sw+2.500*w.saum)*z}"/><polyline points="${l}" fill="none" stroke="${W().auswahl}" stroke-width="${sw*z}"/>`;zeich.forEach((q,i)=>{const g=(i?4:8)*z;s+=`<rect x="${q[0]-g}" y="${q[1]-g}" width="${2*g}" height="${2*g}" fill="${W().auswahl}" stroke="${DUNKEL}" stroke-width="${z}"/>`})}}
 sv.innerHTML=s;sv.classList.toggle('zeichnen',!!zeich);$('fit').hidden=$('minus').disabled=voll();$('plus').disabled=V[2]<=12.01;
 const ein=px()?B[id].px:1,ziel=90*z*ein,e=10**Math.floor(Math.log10(ziel)),n=[5,2,1].find(x=>x*e<=ziel)*e;$('mstt').textContent=n+(px()?' px':' mm');$('mstb').style.width=n/ein/z+'px';knoepfe()}
function knoepfe(){const s=S();$('rueck').hidden=zeich?!zeich.length:!s.h.length;$('wieder').hidden=!!zeich||!s.v.length;$('sp').hidden=!s.dreck||!offen(id)}
/* Liste, Bearbeiten, Bilderleiste */
function liste(){const s=S(),n=s.o.length,g=n-offen(id);$('stand').textContent=n?`${g} von ${n} geprüft`:'';$('fort').max=n||1;$('fort').value=n?g:0;
 const G_=grp();$('liste').innerHTML=n?folge().map(i=>{const o=s.o[i],p=form(o),c=o.c===null?'neu':Math.round(o.c*100)+' %',un=o.c!==null&&o.c<.7;return`<li><button class="zl${G_&&mw.has(o)?' mw':''}" data-i="${i}" data-f="z${i}" aria-pressed="${G_?mw.has(o):i==sel}"><span class="n"><span class="bu">${bu(i)}</span><span class="kw" title="Alle offenen ${esc(K[o.k][0])} wählen (K)">${muster(o.k)}</span><span>${K[o.k][0]}</span></span><span class="mx">${gr(p)}</span><span class="ki ${o.ok?'ok':''}"${o.c==null?'':` title="Alle offenen ab ${Math.round(o.c*100)} % wählen (G)"`}>${o.ok?ic('check')+'<span class="vs">geprüft, </span>':un?ic('warning')+'<span class="vs">unsicher, </span>':''}<span class="kz">${c}</span>${o.c===null?'':`<i class="bk" style="--p:${o.c}"></i>`}</span></button></li>`}).join(''):`<li class="leer">Keine Objekte. Mit Zeichnen anlegen oder so speichern.</li>`}
const kacheln=(o,p)=>`<div><span>kleinster ⌀</span><b>${gr(p)}</b></div><div><span>größter ⌀</span><b>${angs(p)?'–':wert(mass(p).x)}</b></div>`;
/* Am Holz gemessen (Messschieber): je Person eine Zeile, Abweichung Bild minus Holz in mm, nur mit Maßstab */
const meine=o=>(o.m||[]).find(m=>m.von==ICH)||{},dz=x=>x==null?'':String(x).replace('.',',');
function abw(bild,holz){if(holz==null||px())return'';const d=bild-holz,pz=d/holz*100,gross=Math.abs(d)>1&&Math.abs(pz)>10;return`<output class="dv${gross?' gross':''}" title="Bild minus Holz">${d>0?'+':''}${fix(d)} mm</output>`}
function messung(o,p){const m=meine(o),ms=mass(p),an=angs(p),bild=[an?null:ms.w,an?null:ms.x],an2=(o.m||[]).filter(x=>x.von!=ICH);
 return`<details class="mess" ${messAuf||(o.m||[]).length?'open':''}><summary data-f="mess">${ic('caret-right')}Am Holz gemessen</summary><div class="mz">${[['min','kleinster ⌀',0],['max','größter ⌀',1]].map(([f,n,j])=>`<label for="m-${f}">${n}</label><span class="me"><input id="m-${f}" data-f="m-${f}" data-m="${f}" type="number" inputmode="decimal" min="0.1" max="5000" step="0.1" value="${m[f]??''}"><span>mm</span></span>${bild[j]==null?'<output></output>':abw(bild[j],m[f])}`).join('')}</div>${an2.map(x=>`<p class="an">${esc(x.von)}: ${dz(x.min)||'–'} / ${dz(x.max)||'–'} mm</p>`).join('')}</details>`}
const rg=(i,n,a,lo,hi,s,t,k,g)=>`<div class="rg"><div><label for="${i}">${n}</label><output id="${i}v" for="${i}">${t}</output></div><div><button class="ib" data-s="${i}" data-v="-1" data-f="${i}-" aria-label="${n}: ${k}">${ic('minus')}</button><input id="${i}" data-f="${i}" type="range" min="${lo}" max="${hi}" step="${s}" value="${a}" aria-valuetext="${t}"><button class="ib" data-s="${i}" data-v="1" data-f="${i}+" aria-label="${n}: ${g}">${ic('plus')}</button></div></div>`;
function insp(){const o=akt(),e=$('p-insp');if(grp())return inspGruppe(e);if(!o){e.innerHTML=`<p class="leer">${!S().o.length?'Kein Objekt im Bild.':offen(id)?'Objekt im Bild oder in der Liste wählen.':$('gut').hidden?'Alle Bilder geprüft und gespeichert.':'Alle Objekte geprüft.'}</p>`;return}
 const p=form(o);e.innerHTML=`<h2 class="titel">${bu(sel)} ${muster(o.k)} ${K[o.k][0]}${o.ok?' '+ic('check-circle'):''}</h2><div class="kpi">${kacheln(o,p)}</div>${messung(o,p)}
<fieldset><legend>Klasse<button type="button" class="ib klb" id="klb" data-f="klb" aria-label="Klassen bearbeiten" title="Klassen bearbeiten">${ic('pencil-simple')}</button></legend>${(R=>`<div class="kl">${R(KL.slice(0,HAUPT),0)}</div><details class="mehr" ${mehr||KL.indexOf(String(o.k))>=HAUPT?'open':''}><summary data-f="mehr">${ic('caret-right')}Weitere</summary><div class="kl">${R(KL.slice(HAUPT),HAUPT)}</div></details>`)((l,v)=>l.map((k,j)=>{const n=v+j;return`<label><input type="radio" name="kl" value="${k}" data-f="k${k}" ${k==o.k?'checked':''}>${muster(k)}<span>${K[k][0]}</span>${n<9?`<kbd aria-hidden="true">${n+1}</kbd>`:''}</label>`}).join(''))}</fieldset>
<fieldset><legend>Umriss</legend>${rg('r','Größe',o.r,-4,4,.1,wr(o),'kleiner','größer')}${rg('g','Glätten',o.g,0,8,1,o.g,'weniger','mehr')}</fieldset>
<details ${auf?'open':''}><summary data-f="det">${ic('caret-right')}Einzelnen Punkt verschieben</summary><p>Punkte im Bild ziehen oder hier schrittweise, 0,5 mm je Klick.</p><div class="pkt"><button class="ib" data-n="-1" data-f="n-" aria-label="Voriger Punkt">${ic('arrow-left')}</button><span class="mono">Punkt ${pkt+1}</span><button class="ib" data-n="1" data-f="n+" aria-label="Nächster Punkt">${ic('arrow-right')}</button></div><div class="pkt" style="margin-top:8px">${[['Links',-1,0],['Rechts',1,0],['Hoch',0,-1],['Runter',0,1]].map(([t,x,y])=>`<button class="b" data-x="${x}" data-y="${y}" data-f="m${t}" aria-label="Punkt nach ${t.toLowerCase()}">${ic({Links:'arrow-left',Rechts:'arrow-right',Hoch:'arrow-left',Runter:'arrow-left'}[t]).replace('class="i"',`class="i" style="transform:rotate(${{Hoch:90,Runter:-90}[t]||0}deg)"`)}</button>`).join('')}</div></details>`}
function dopp(){const d=grp()?-1:streit(sel);$('dopp').hidden=d<0;if(d<0){$('dopp').innerHTML='';return}$('dopp').innerHTML=`<p>${ic('warning')}<span>${bu(sel)} und ${bu(d)} liegen auf derselben Stelle.</span></p><div>${[sel,d].sort((a,b)=>bu(a)<bu(b)?-1:1).map(i=>`<button class="b" data-weg="${i==sel?d:sel}" data-f="w${i}" title="${bu(i)} behalten">${ic('check')}<b class="bs" aria-hidden="true">${bu(i)}</b><span>${bu(i)} behalten</span></button>`).join('')}</div>`}
function fuss(){const s=S(),n=IDS.indexOf(id),o=akt(),g=$('gut'),fertig=!offen(id);$('lo').hidden=!o;$('lo').querySelector('.bs').textContent='';
 if(grp()){const z=zahlG();g.hidden=!!zeich||!z;$('lo').hidden=!z;const nf=weit?ziel().size:0,bz=weit?` auf ${nf} ${nf==1?'Foto':'Fotos'}`:'';g.querySelector('span').textContent='';g.querySelector('.bs').innerHTML=z+(weit?BALKENW+nf:'');g.classList.toggle('weit',weit);g.title=`${z} bestätigen${bz}${weit?'':' (Enter)'}`;g.setAttribute('aria-label',g.title);g.querySelector('use').setAttribute('href','#i-check');
  $('lo').querySelector('.bs').innerHTML=z+(weit?BALKENW+nf:'');$('lo').title=`${z} verwerfen${bz}${weit?'':' (Entf)'}`;$('lo').setAttribute('aria-label',$('lo').title);fussRest(s,n);return}
 g.classList.remove('weit');g.removeAttribute('aria-label');$('lo').title='Löschen (Entf)';$('lo').removeAttribute('aria-label');g.hidden=!!zeich||fertig&&!s.dreck&&!!s.zeit&&!IDS.some(i=>i!=id&&(!st[i].zeit||st[i].dreck||offen(i)));const t=o?(o.ok?(fertig?'Speichern, nächstes Bild':'Nächstes Objekt'):streit(sel)>=0?'Beide lassen':'Stimmt'):fertig?'Speichern, nächstes Bild':'Erstes offenes Objekt';g.querySelector('span').textContent=t;g.title=t+' (Enter)';{const d=streit(sel);g.querySelector('.bs').textContent=o&&!o.ok&&d>=0?[bu(sel),bu(d)].sort().join(' + '):''}g.querySelector('use').setAttribute('href',fertig?'#i-floppy-disk':o&&!o.ok?'#i-check':'#i-arrow-right');
 fussRest(s,n)}
function fussRest(s,n){$('spstand').textContent=s.dreck?'Nicht gespeicherte Änderungen':s.zeit?`Gespeichert ${s.zeit}`:'Noch nicht gespeichert';
 $('pos').innerHTML=`<b>${esc(name(id))}</b> <span>${n+1} von ${IDS.length}</span>`;$('vor').disabled=!n;$('nach').disabled=n==IDS.length-1;
 film();knoepfe()}
/* Bilderleiste (Jan 26.11.2026): Balken > Seite > Foto. Der aktuelle Balken ist offen, die anderen zu; zugeklappte
   Balken zeichnen keine Bilder, darum bleibt die Leiste auch bei vielen Balken schnell. Neu gebaut wird nur bei
   Wechsel, Auf/Zu, Verwerfen; sonst ändert sich nur das aktuelle Foto. */
let filmAuf=new Set,filmFuer=null,filmId=null;const fweg=[];let fwegZuletzt=false;
const fertigF=i=>!!st[i].zeit&&!st[i].dreck&&!offen(i),gruppe=b=>IDS.filter(i=>B[i].balken==b);
const darfWeg=i=>!SATZ_L&&(ICH=='mac'||B[i].frei);
function zust(i){const t=st[i],n=t.o.length,of=offen(i);
 if(t.dreck)return['geändert','<circle cx="7" cy="7" r="4" class="zd"/>'];
 if(t.zeit&&!of)return['geprüft','<circle cx="7" cy="7" r="6" class="zg"/><path d="M4.2 7.2l2 2 3.6-4" class="zh"/>'];
 if(!n)return['leer','<circle cx="7" cy="7" r="5" class="zr"/>'];
 const a=(n-of)/n,w=a*2*Math.PI,x=7+5*Math.sin(w),y=7-5*Math.cos(w);
 return[`${of} von ${n} offen`,`<circle cx="7" cy="7" r="5" class="zo"/>${a>0?`<path d="M7 7V2A5 5 0 ${a>.5?1:0} 1 ${x.toFixed(2)} ${y.toFixed(2)}Z" class="zp"/>`:''}`]}
const zsvg=i=>`<svg class="zs" viewBox="0 0 14 14" aria-hidden="true">${zust(i)[1]}</svg>`,flab=i=>`${name(i)}: ${zust(i)[0]}`;
function kopfZahl(b){const l=gruppe(b),f=l.filter(fertigF).length;return[f,l.length]}
function filmBau(still){const e=$('p-film'),cur=B[id].balken;if(filmFuer!=cur){filmFuer=cur;filmAuf=new Set([cur])}filmId=id;
 const g=new Map;for(const i of IDS){const b=B[i].balken;g.has(b)||g.set(b,[]);g.get(b).push(i)}let h=SATZ_L?'':`<div class="vlkopf">${VL.etikett()}</div>`;
 for(const[b,l]of g){const auf=filmAuf.has(b),f=l.filter(fertigF).length,nb=B[l[0]].nb;
  h+=`<section class="fg${auf?' auf':''}${b==cur?' akt':''}" data-g="${esc(b)}"><div class="fkr"><button class="fk" data-k="${esc(b)}" data-f="g${esc(b)}" aria-expanded="${auf}" aria-label="${esc(b)}${nb?' '+esc(nb):''}, ${f} von ${l.length} fertig">${ic('caret-right')}<b>${esc(b)}</b>${nb?`<span class="fn">${esc(nb)}</span>`:''}<span class="fz"><span>${f}/${l.length}</span><i style="--p:${f/l.length}"></i></span></button>${SATZ_L?'':VL.knopf(b,`data-vl="${esc(b)}" data-f="vl${esc(b)}"`,'Balken vorlabeln')}${b==cur?kopfKnoepfe(b,l):''}</div>`;
  if(auf){const s=new Map;for(const i of l){const k=B[i].seite||'';s.has(k)||s.set(k,[]);s.get(k).push(i)}
   h+='<div class="fi">'+[...s].map(([k,li])=>`<div class="fs" role="group" aria-label="${k?'Seite '+k:esc(b)}">${k?`<span class="sl" aria-hidden="true">S${k}</span>`:''}${li.map(i=>`${i==id?'<span class="fc">':''}<button class="fb" data-b="${i}" data-f="b${i}" aria-label="${esc(flab(i))}" title="${esc(flab(i))}${darfWeg(i)?' (Entf verwirft)':''}" ${i==id?'aria-current="true"':''}><img src="${B[i].klein}" loading="lazy" alt="" width="56" height="40">${zsvg(i)}</button>${i==id&&darfWeg(i)?`<button class="ib fweg" data-weg="${i}" aria-label="Foto verwerfen" title="Foto verwerfen (Entf)"><svg class="i fx" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14"/><path d="M9.5 9.5l5 5M14.5 9.5l-5 5"/></svg></button>`:''}${i==id&&!SATZ_L&&!VL.gesperrt(b)?VL.knopf(b,`data-vlf="${i}" data-f="vlf"`,'Foto vorlabeln'):''}${i==id?'</span>':''}`).join('')}</div>`).join('')+'</div>'}
  h+='</section>'}
 const f=document.activeElement&&e.contains(document.activeElement)?document.activeElement.dataset.f:null;
 e.innerHTML=h;const c=e.querySelector('[aria-current]');if(!still)c&&c.scrollIntoView({block:'nearest',inline:'nearest'});if(f){const x=e.querySelector(`[data-f="${CSS.escape(f)}"]`);x&&x.focus({preventScroll:true})}}
/* Balkenebene: Auswahl (Regel) auf alle Fotos des Balkens ausdehnen. Zeichnung: Balken mit Haken. */
const BALKENW='<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 9.5h19v8h-19zM8.5 9.5v8M14.5 9.5v8" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M8 5.2l2.2 2.2L15.5 2.8" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>';
function kopfKnoepfe(b,l){const of=l.reduce((s,i)=>s+offen(i),0);if(!of&&!weit)return'';const t=weit?'Nur dieses Foto (B)':'Auswahl auf den ganzen Balken (B)';
 return`<button class="ib fwb" data-weit="1" data-f="weit" aria-pressed="${weit}" aria-label="${t}" title="${t}">${BALKENW}${weit?`<b class="bs">${zahlG()}</b>`:''}</button>`}
function film(){if(filmId!=id||!$('p-film').firstChild)return filmBau();{const w=$('p-film').querySelector('.fwb'),neu=kopfKnoepfe(B[id].balken,gruppe(B[id].balken));if(!!w!=!!neu||w&&w.getAttribute('aria-pressed')!=String(weit))return filmBau();if(w&&weit)w.querySelector('.bs').textContent=zahlG()}const b=$('p-film').querySelector(`[data-b="${CSS.escape(id)}"]`);if(!b)return;
 const l=flab(id);if(b.getAttribute('aria-label')==l)return;b.setAttribute('aria-label',l);b.title=l+(darfWeg(id)?' (Entf verwirft)':'');b.querySelector('.zs').innerHTML=zust(id)[1];
 const k=$('p-film').querySelector(`.akt .fk`),[f,n]=kopfZahl(B[id].balken),nb=B[id].nb;if(k){k.querySelector('.fz span').textContent=`${f}/${n}`;k.querySelector('.fz i').style.setProperty('--p',f/n);k.setAttribute('aria-label',`${B[id].balken}${nb?' '+nb:''}, ${f} von ${n} fertig`)}}
async function ruf(weg,d){const a=await fetch(weg,{method:'POST',headers:{'X-Aufnahme':'1'},body:JSON.stringify(d)});let j={};try{j=await a.json()}catch(e){}if(!a.ok)throw new Error(j.fehler||'Fehler '+a.status);return j}
async function fotoWeg(i){if(!i||!B[i]||speichert||zeich&&i==id)return;if(!darfWeg(i))return sag('Fotobox-Fotos verwirft nur der Mac.');const b=B[i],fl=[...$('p-film').querySelectorAll('.fb')],war=document.activeElement&&document.activeElement.closest&&document.activeElement.closest('#p-film')?fl.findIndex(x=>x.dataset.b==i):-2;
 try{await ruf(ICH=='mac'?'/api/loeschen':'/api/foto-weg',{balken:b.balken,seite:b.seite,nr:b.nr})}catch(e){return fehler('Nicht verworfen: '+(e instanceof TypeError?'Keine Verbindung zu Neurolign.':e.message))}
 const n=IDS.indexOf(i);IDS.splice(n,1);fweg.push({i,n});fwegZuletzt=true;zurKnopf();
 if(!IDS.length){id=null;$('p-film').innerHTML='';$('leerseite').hidden=false;$('leerseite').innerHTML='<p>Noch keine Fotos.</p>';$('bild').innerHTML='';return}
 if(i==id){const g=gruppe(b.balken);await oeffne(g.find(x=>IDS.indexOf(x)>=n)||g.at(-1)||IDS[Math.min(n,IDS.length-1)])}else filmBau();
 if(war>-2){const n2=[...$('p-film').querySelectorAll('.fb')],f=i==id||war<0?$('p-film').querySelector('[aria-current]'):n2[Math.min(war,n2.length-1)];(f||$('p-film').querySelector('.fb,.fk')).focus()}}
async function fotoZurueck(){const w=fweg.at(-1);if(!w||speichert)return;const b=B[w.i];
 try{await ruf(ICH=='mac'?'/api/zurueck':'/api/foto-zurueck',{balken:b.balken,seite:b.seite,nr:b.nr})}catch(e){return fehler('Nicht zurückgeholt: '+(e instanceof TypeError?'Keine Verbindung zu Neurolign.':e.message))}
 fweg.pop();IDS.splice(Math.min(w.n,IDS.length),0,w.i);zurKnopf();$('leerseite').hidden=true;await oeffne(w.i)}
function zurKnopf(){const z=$('fzur'),w=fweg.at(-1);z.hidden=!w;document.body.classList.toggle('mitzur',!!w);if(!w)return;const l=`${name(w.i)} zurückholen`;z.title=l+' (Strg Z)';z.setAttribute('aria-label',l);z.querySelector('img').src=B[w.i].klein}
function mal(){const f=document.activeElement&&document.activeElement.dataset?document.activeElement.dataset.f:null,y=$('p-insp').scrollTop;bildZ();liste();fuss();insp();dopp();$('p-insp').scrollTop=y;if(f&&!(document.activeElement&&document.activeElement.dataset.f==f)){const e=document.querySelector(`[data-f="${f}"]`);e&&e.focus({preventScroll:true})}}
function fokus(){const b=document.querySelector('.zl[aria-pressed=true]');if(b&&b.offsetParent){b.focus({preventScroll:true});b.scrollIntoView({block:'nearest'})}else $('gut').focus({preventScroll:true})}
function zeig(i){const p=form(S().o[i]),m=mitte(p);if(!voll()&&(m[0]<V[0]||m[1]<V[1]||m[0]>V[0]+V[2]||m[1]>V[1]+V[3])){V[0]=m[0]-V[2]/2;V[1]=m[1]-V[3]/2;rand()}}
function waehle(i,f){leeren();if(i!=sel){pkt=0;auf=false}sel=i;if(i>=0)zeig(i);mal();if(f)fokus()}
async function oeffne(i,f){const n=++lfd;try{await messen(i)}catch(e){fehler(name(i)+': '+e.message);return}if(n!=lfd)return;id=i;zeich=null;leeren();werk();stumm();ganz();pkt=0;auf=false;sel=erstes();mal();if(f)fokus()}
function reiter(t,f){tab=t;if(t=='film')requestAnimationFrame(()=>{const c=$('p-film').querySelector('[aria-current]')||$('p-film').querySelector('.akt');c&&c.scrollIntoView({block:'center',inline:'nearest'})});for(const n of['liste','insp','film']){$('p-'+n).classList.toggle('an',n==t);$('t-'+n).setAttribute('aria-selected',n==t);$('t-'+n).tabIndex=n==t?0:-1}if(f)$('t-'+t).focus()}
document.querySelector('.tabs').addEventListener('click',e=>{const b=e.target.closest('button');b&&reiter(b.id.slice(2))});
document.querySelector('.tabs').addEventListener('keydown',e=>{const d={ArrowRight:1,ArrowLeft:-1}[e.key];if(d){const r=['liste','insp','film'];reiter(r[(r.indexOf(tab)+d+3)%3],true);e.stopPropagation()}});
/* Aktionen */
function werk(){$('neu').setAttribute('aria-pressed',!!zeich);$('neu').querySelector('span').textContent=zeich?'Abbrechen':'Zeichnen';$('neu').title=zeich?'Abbrechen (Esc)':'Neues Objekt zeichnen (N)';$('neu').querySelector('use').setAttribute('href',zeich?'#i-x':'#i-polygon')}
function umrisse(aus){nur=aus;$('aus').setAttribute('aria-pressed',aus);bildZ()}
function zeichnen(an){zeich=an?[]:null;maus=null;if(an){sel=-1;umrisse(false);sag('Punkte setzen, der erste schließt.','Schließen',schliess,true);$('hink').hidden=true}else stumm();werk();mal()}
function zstand(){bildZ();$('hink').hidden=!zeich||zeich.length<3}
function schliess(){if(!zeich)return;if(zeich.length<3){sag('Mindestens drei Punkte setzen.','Schließen',schliess,true);$('hink').hidden=true;return}const p=zeich;zeichnen(false);merk();{const o=obj(letzte,null,p);o.ok=true;S().o.push(o)};waehle(S().o.length-1,true)}
function gut(taste){if(grp())return taste&&weit?sag('Für den ganzen Balken bitte klicken.'):gruppeTun('ok');const o=akt();if(!o&&!offen(id)||o&&o.ok&&!offen(id))return speich();if(o&&!o.ok){merk();o.ok=true}const f=erstes();waehle(f);f<0?$('gut').focus({preventScroll:true}):fokus()}
function weg(j){const s=S(),bl=s.o[j==sel?doppelt(j):sel],n=`${bu(j)} ${K[s.o[j].k][0]}`;merk();s.o.splice(j,1);waehle(s.o.indexOf(bl),true);sag(n+' gelöscht.','Rückgängig',rueck)}
function loesch(taste){if(grp()&&!zeich)return taste&&weit?sag('Für den ganzen Balken bitte klicken.'):gruppeTun('weg');if(!akt()||zeich)return;const n=`${bu(sel)} ${K[akt().k][0]}`;merk();S().o.splice(sel,1);waehle(erstes(),true);sag(n+' gelöscht.','Rückgängig',rueck)}
function hin(von,nach){const s=S(),h=von.pop();if(!h)return;nach.push(JSON.stringify([s.o,sel]));[s.o,sel]=JSON.parse(h);leeren();if(sel>=s.o.length)sel=-1;s.dreck=true;mal()}
function rueck(){if(zeich){zeich.pop();maus=null;return zstand()}stumm();hin(S().h,S().v)}
function wieder(){if(!zeich)hin(S().v,S().h)}
function schritt(k,d){const o=akt(),n=k=='r'?Math.round(kl(o.r+d*.1,-4,4)*10)/10:kl(o.g+d,0,8);if(n==o[k])return;merk();o[k]=n;mal()}
function setK(k){if(grp())return gruppeTun('k',+k);const o=akt();if(o&&o.k!=k){merk();o.k=letzte=+k;mal()}}
function backe(o){o.b=form(o);o.r=0;o.g=0}
function schieb(basis,j,dx,dy){const n=basis.length;return basis.map((q,i)=>{let t=Math.abs(i-j);t=Math.min(t,n-t);const f=Math.exp(-t*t/3);return[kl(q[0]+f*dx,0,B[id].lmm),kl(q[1]+f*dy,0,B[id].qmm)]})}
let speichert=false;
/* Objekt so, wie der Server es speichert. Geöffnete Fotos haben Bearbeitungsform (b, r, g in mm), nie geöffnete noch
   die Form vom Server (p in Anteilen). form() rechnet mit dem aktuellen Foto, darum kurz umschalten. */
function zumServer(o,i){if(!B[i].qmm)return{...o,c:o.c??undefined};const alt=id;id=i;try{return{...o.x,k:o.k,ok:o.ok,c:o.c??undefined,m:o.m&&o.m.length?o.m:undefined,p:form(o).map(q=>[q[0]/B[i].lmm,q[1]/B[i].qmm])}}finally{id=alt}}
async function sichern(i){const t=st[i],j=await ruf('/api/label',{name:i,stand:B[i].zv,objekte:t.o.map(o=>zumServer(o,i))});t.zeit=uhrzeit(j.zeit);B[i].zv=j.zeit;t.dreck=false}

/* Gruppiert annehmen (Jan 26.11.2026): mehrere offene Vorlabel auf einmal bestätigen, verwerfen oder umklassifizieren.
   Auswahl in Liste und Bild: Strg/Cmd-Klick einzeln, Umschalt-Klick Bereich, Klick aufs Klassenmuster alle offenen
   dieser Klasse (K), Klick auf die Konfidenz alle offenen ab diesem Wert (G), Strg+A alle offenen. Eine Regel lässt
   sich auf den ganzen Balken ausdehnen (B, Knopf im Kopf der Bilderleiste); das wird sofort gespeichert. Rückgängig
   statt Nachfrage. */
let mw=new Set,regel=null,weit=false;const gzur=[];let gzurZuletzt=false;
const trifft=(o,r)=>!o.ok&&(r.art=='alle'||r.art=='k'&&o.k==r.k||r.art=='c'&&o.c!=null&&o.c>=r.c-1e-9);
function grp(){return mw.size>1||weit}
function leeren(){mw=new Set;regel=null;weit=false}
function ziel(){if(!weit)return new Map([[id,[...mw]]]);const m=new Map;for(const i of gruppe(B[id].balken)){const l=st[i].o.filter(o=>trifft(o,regel));if(l.length)m.set(i,l)}return m}
function zahlG(){let n=0;for(const l of ziel().values())n+=l.length;return n}
function einzeln(){const o=[...mw][0];leeren();sel=o?S().o.indexOf(o):-1}
function waehleRegel(r){if(zeich)return;regel=r;weit=false;mw=new Set(S().o.filter(o=>trifft(o,r)));if(mw.size<2)einzeln();mal();lFokus();if(sel<0&&!mw.size)sag('Nichts offen.')}
function umschalten(i){const o=S().o[i];if(!grp()){mw=new Set(sel>=0?[S().o[sel]]:[])}regel=null;weit=false;mw.has(o)?mw.delete(o):mw.add(o);sel=i;if(mw.size<2)einzeln();mal();lFokus()}
function bereich(i){if(sel<0)return waehle(i,true);const f=folge(),a=f.indexOf(sel),b=f.indexOf(i);regel=null;weit=false;mw=new Set(f.slice(Math.min(a,b),Math.max(a,b)+1).map(j=>S().o[j]));if(mw.size<2){leeren();return waehle(i,true)}mal()}
function balkenweit(){if(zeich)return;if(!weit&&!gruppe(B[id].balken).some(i=>offen(i)))return sag('Nichts offen.');if(weit){weit=false;mw=new Set(S().o.filter(o=>trifft(o,regel)));if(mw.size<2)einzeln()}else{regel=regel||{art:'alle'};weit=true;mw=new Set(S().o.filter(o=>trifft(o,regel)))}mal()}
function lFokus(){const b=document.querySelector('.zl.mw')||document.querySelector('.zl[aria-pressed=true]');if(b&&b.offsetParent&&document.activeElement&&document.activeElement.closest&&document.activeElement.closest('#liste'))b.focus({preventScroll:true})}
async function gruppeTun(art,k){const z=ziel(),n=zahlG();if(!n||speichert)return;const wort={ok:'bestätigt',weg:'verworfen',k:'→ '+(K[k]||[''])[0]}[art];
 if(!weit){merk();const s=S();if(art=='weg')s.o=s.o.filter(o=>!mw.has(o));else for(const o of mw)art=='ok'?o.ok=true:o.k=k;
  if(art=='k'){letzte=+k;mal()}else{leeren();sel=erstes();mal();fokus()}sag(`${n} ${wort}`,'Rückgängig',rueck);return}
 const vor=[];for(const[i,l]of z){const t=st[i],w=new Set(l);vor.push([i,JSON.stringify(t.o)]);if(art=='weg')t.o.splice(0,t.o.length,...t.o.filter(o=>!w.has(o)));else for(const o of l)art=='ok'?o.ok=true:o.k=+k;t.dreck=true}
 gzur.push(vor);fwegZuletzt=false;gzurZuletzt=true;if(art=='k')letzte=+k;leeren();sel=erstes();mal();filmBau();
 const fehl=await alleSichern(vor.map(v=>v[0]));mal();filmBau();if(fehl)return fehler('Nicht gespeichert: '+fehl);sag(`${n} ${wort}, ${z.size} ${z.size==1?'Foto':'Fotos'}`,'Rückgängig',gruppeRueck,true)}
async function alleSichern(l){speichert=true;let f='';try{for(const i of l){try{await sichern(i)}catch(e){f=`${name(i)}: ${e instanceof TypeError?'Keine Verbindung zu Neurolign.':e.message}`}}}finally{speichert=false}return f}
async function gruppeRueck(){const vor=gzur.pop();if(!vor||speichert)return;gzurZuletzt=gzur.length>0;stumm();for(const[i,j]of vor){const t=st[i];t.o.splice(0,t.o.length,...JSON.parse(j));t.dreck=true}
 leeren();sel=erstes();mal();filmBau();const fehl=await alleSichern(vor.map(v=>v[0]));mal();filmBau();if(fehl)fehler('Nicht gespeichert: '+fehl)}
function inspGruppe(e){const z=ziel(),je={};let n=0;for(const l of z.values())for(const o of l){je[o.k]=(je[o.k]||0)+1;n++}const ks=Object.keys(je),eins=ks.length==1?ks[0]:null;
 e.innerHTML=`<h2 class="titel gt"><span class="mono">${n}</span>${weit?`<span class="gw" title="Fotos dieses Balkens">${BALKENW}<span class="mono">${z.size}</span></span>`:''}</h2>
<ul class="gk">${ks.sort((a,b)=>je[b]-je[a]).map(k=>`<li>${muster(k)}<span>${esc(K[k][0])}</span><span class="mono">${je[k]}</span></li>`).join('')}</ul>
<fieldset><legend>Klasse</legend>${(R=>`<div class="kl">${R(KL.slice(0,HAUPT),0)}</div><details class="mehr" ${mehr||eins&&KL.indexOf(eins)>=HAUPT?'open':''}><summary data-f="mehr">${ic('caret-right')}Weitere</summary><div class="kl">${R(KL.slice(HAUPT),HAUPT)}</div></details>`)((l,v)=>l.map((k,j)=>{const m=v+j;return`<label><input type="radio" name="kl" value="${k}" data-f="k${k}" ${k==eins?'checked':''}>${muster(k)}<span>${K[k][0]}</span>${m<9?`<kbd aria-hidden="true">${m+1}</kbd>`:''}</label>`}).join(''))}</fieldset>
<div class="gb"><button class="b" data-weit="1" data-f="weit2" aria-pressed="${weit}" aria-label="${weit?'Nur dieses Foto':'Auswahl auf den ganzen Balken'}" title="${weit?'Nur dieses Foto':'Auswahl auf den ganzen Balken'} (B)">${BALKENW}</button><button class="b" data-leer="1" data-f="leer" aria-label="Auswahl aufheben" title="Auswahl aufheben (Esc)">${ic('x')}</button></div>`}
async function speich(){if(zeich)return sag('Erst den Umriss schließen oder abbrechen.');if(speichert)return;speichert=true;const alt=id,s=S(),vor=JSON.stringify(s.o);
 try{const a=await fetch('/api/label',{method:'POST',headers:{'X-Aufnahme':'1'},body:JSON.stringify({name:alt,stand:B[alt].zv,objekte:s.o.map(o=>zumServer(o,alt))})}),j=await a.json();if(!a.ok)throw Error(j.fehler);s.zeit=uhrzeit(j.zeit);B[alt].zv=j.zeit}
 catch(e){speichert=false;return fehler('Nicht gespeichert: '+(e instanceof TypeError?'Keine Verbindung zu Neurolign.':e.message))}
 speichert=false;s.dreck=JSON.stringify(s.o)!=vor;$('fehl').hidden=true;if(id!=alt||s.dreck)return mal();
 const n=IDS.indexOf(alt),of=offen(alt),t=`${name(alt)} gespeichert${of?`, ${of} noch offen`:''}.`,naechst=[...IDS.slice(n+1),...IDS.slice(0,n)].find(i=>!st[i].zeit||st[i].dreck||offen(i));
 if(naechst){await oeffne(naechst,true);sag(t,'Dorthin zurück',()=>oeffne(alt,true))}else{mal();sag(of?t:t+' Alle Fotos fertig.')}}
$('liste').onclick=e=>{const b=e.target.closest('.zl');if(!b||zeich)return;const i=+b.dataset.i,o=S().o[i];if(e.shiftKey)return bereich(i);if(e.ctrlKey||e.metaKey)return umschalten(i);
 if(e.target.closest('.kw'))return waehleRegel({art:'k',k:o.k});if(e.target.closest('.ki')&&o.c!=null)return waehleRegel({art:'c',c:o.c});waehle(i,true)};
$('dopp').onclick=e=>{const b=e.target.closest('button');if(!b)return;weg(+b.dataset.weg)};
const I=$('p-insp');I.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const d=b.dataset;if(d.weit)return balkenweit();if(d.leer){leeren();return mal()}if(d.s)return schritt(d.s,+d.v);const o=akt(),n=o.b.length;if(d.n){pkt=(pkt+ +d.n+n)%n;return mal()}if(d.x){merk();backe(o);o.b=schieb(o.b,pkt,d.x*.5,d.y*.5);mal()}});
I.addEventListener('toggle',e=>{if(e.target.classList.contains('mehr')){mehr=e.target.open;return}if(e.target.classList.contains('mess')){messAuf=e.target.open;return}if(e.target.open!=auf){auf=e.target.open;bildZ()}},true);
let gem=null;I.addEventListener('input',e=>{const t=e.target;if(t.type!='range')return;if(gem!==t){merk();gem=t}const o=akt();o[t.id]=+t.value;const w=t.id=='r'?wr(o):o.g;$(t.id+'v').textContent=w;t.setAttribute('aria-valuetext',w);I.querySelector('.kpi').innerHTML=kacheln(o,form(o));bildZ();liste();fuss()});
I.addEventListener('change',e=>{const t=e.target;if(t.name=='kl')setK(t.value);else if(t.dataset.m)messen_holz(t.dataset.m,t.value);else{gem=null;mal()}});
function messen_holz(f,roh){const o=akt();if(!o)return;const w=roh===''?null:+String(roh).replace(',','.');if(w!=null&&!(w>0&&w<=5000))return mal();merk();o.m=(o.m||[]).map(x=>({...x}));let m=o.m.find(x=>x.von==ICH);if(!m){m={von:ICH,min:null,max:null};o.m.push(m)}m[f]=w;o.m=o.m.filter(x=>x.min!=null||x.max!=null);mal()}
I.addEventListener('click',e=>{if(e.target.closest('#klb'))klDialog()});
$('neu').onclick=()=>zeichnen(!zeich);$('rueck').onclick=rueck;$('wieder').onclick=wieder;$('minus').onclick=()=>zoom(1/.6);$('plus').onclick=()=>{const o=akt();zoom(.6,...(o?mitte(form(o)):[]))};$('fit').onclick=()=>{ganz();bildZ()};$('aus').onclick=()=>umrisse(!nur);
const wechsel=d=>{const i=IDS[IDS.indexOf(id)+d];if(i)oeffne(i)};$('vor').onclick=()=>wechsel(-1);$('nach').onclick=()=>wechsel(1);$('p-film').onclick=e=>{const b=e.target.closest('button');if(!b)return;const d=b.dataset;if(d.k){filmAuf.has(d.k)?filmAuf.delete(d.k):filmAuf.add(d.k);filmBau();const k=$('p-film').querySelector(`[data-k="${CSS.escape(d.k)}"]`);k&&k.focus();return}if(d.weg)return fotoWeg(d.weg);if(d.weit)return balkenweit();if(b.classList.contains('vlmehr'))return VL.menue(b);
 if((d.vl||d.vlf)&&b.getAttribute('aria-disabled')!='true')return vorlabeln(d.vl||B[d.vlf].balken,d.vlf);if(d.vl||d.vlf)return;if(d.b&&!speichert)oeffne(d.b)};$('fzur').onclick=fotoZurueck;$('sp').onclick=speich;$('gut').onclick=()=>gut();$('lo').onclick=()=>loesch();

/* Klassen bearbeiten (Jan 26.11.2026): umbenennen, Farbe, Gruppe, neu, löschen. Jede Änderung gilt sofort für alle.
   Löschen mit Objekten heißt zusammenlegen; Rückgängig unten im Fenster. */
const D=$('kld'),hexvon=f=>{const c=document.createElement.ctx2||=document.createElement('canvas').getContext('2d');c.fillStyle='#000';c.fillStyle=f;return c.fillStyle};
let kWeg=null;
function klDialog(){kWeg=null;klMal();$('klh').hidden=true;D.showModal()}
function klMal(){const d=KD,z=d.zahl||{},g=d.gruppen,akt_=d.klassen.filter(k=>k.aktiv),f=document.activeElement&&D.contains(document.activeElement)?document.activeElement.dataset.f:null;
 $('kll').innerHTML=g.map((gn,n)=>`<section><input class="gn" type="text" value="${esc(gn)}" data-g="${esc(gn)}" data-f="g${n}" aria-label="Gruppe ${esc(gn)}" maxlength="20"><ul>${akt_.filter(k=>k.gruppe==gn).map(k=>{const zahl=z[k.id]||0;
  if(kWeg==k.id)return`<li class="weg-zeile">${muster(k.id)}<span class="nm">${esc(k.name)}</span><span class="zz">${zahl}</span>${ic('arrow-right')}<select data-f="ziel" id="klziel" aria-label="Objekte von ${esc(k.name)} zu">${akt_.filter(x=>x.id!=k.id).map(x=>`<option value="${x.id}">${esc(x.name)}</option>`).join('')}</select><button type="button" class="ib prim" data-ok="${k.id}" data-f="ok${k.id}" aria-label="Zusammenlegen" title="Zusammenlegen">${ic('check')}</button><button type="button" class="ib" data-nein="1" data-f="nein" aria-label="Abbrechen" title="Abbrechen">${ic('x')}</button></li>`;
  return`<li><input type="color" value="${hexvon(K[k.id][1])}" data-c="${k.id}" data-f="c${k.id}" aria-label="Farbe ${esc(k.name)}" title="Farbe">${muster(k.id)}<input type="text" value="${esc(k.name)}" data-n="${k.id}" data-f="n${k.id}" aria-label="Name" maxlength="30"><select data-gr="${k.id}" data-f="gr${k.id}" aria-label="Gruppe von ${esc(k.name)}">${g.map(x=>`<option ${x==gn?'selected':''}>${esc(x)}</option>`).join('')}</select><span class="zz" title="Objekte">${zahl||''}</span><button type="button" class="ib weg" data-w="${k.id}" data-f="w${k.id}" aria-label="${esc(k.name)} löschen" title="Löschen" ${akt_.length<2?'disabled':''}>${ic('trash')}</button></li>`}).join('')}</ul><button type="button" class="ib" data-neu="${esc(gn)}" data-f="neu${n}" aria-label="Neue Klasse in ${esc(gn)}" title="Neue Klasse">${ic('plus')}</button></section>`).join('')+`<section><button type="button" class="b" data-neu="" data-f="neug" aria-label="Neue Gruppe" title="Neue Gruppe">${ic('plus')}${ic('list-bullets')}</button></section>`;
 if(f){const e=D.querySelector(`[data-f="${f}"]`);e&&e.focus()}else if(kWeg!=null)$('klziel').focus()}
function frei(basis,liste){let n=basis,i=2;while(liste.some(x=>x.toLowerCase()==n.toLowerCase()))n=`${basis} ${i++}`;return n}
async function klPost(daten,hin){try{const a=await fetch('/api/klassen',{method:'POST',headers:{'X-Aufnahme':'1'},body:JSON.stringify(daten)}),j=await a.json();if(!a.ok)throw Error(j.fehler);klassenSetzen(j);klMal();mal();if(hin)klHin(...hin);else $('klh').hidden=true;return j}
 catch(e){klHin(e instanceof TypeError?'Keine Verbindung zu Neurolign.':e.message);klMal()}}
function klHin(t,undo){$('klh').hidden=false;$('klht').textContent=t;$('klhz').hidden=!undo}
function umhaengen(alt,neu,zurueck){for(const i of IDS){for(const o of st[i].o){if(!zurueck&&o.k==alt){o.k=neu;o.x={...o.x,kv:alt}}else if(zurueck&&o.k==neu&&o.x&&o.x.kv==alt){o.k=alt;o.x={...o.x,kv:undefined}}}for(const o of B[i].roh||[]){if(!zurueck&&o.k==alt){o.k=neu;o.kv=alt}else if(zurueck&&o.k==neu&&o.kv==alt){o.k=alt;delete o.kv}}}}
D.addEventListener('change',e=>{const t=e.target,d=t.dataset;
 if(d.n!==undefined){const v=t.value.trim();if(!v||v==K[d.n][0]){t.value=K[d.n][0];return}klPost({art:'aendern',id:+d.n,name:v})}
 else if(d.c!==undefined)klPost({art:'aendern',id:+d.c,farbe:t.value});
 else if(d.gr!==undefined)klPost({art:'aendern',id:+d.gr,gruppe:t.value});
 else if(d.g!==undefined){const v=t.value.trim();if(!v||v==d.g){t.value=d.g;return}klPost({art:'gruppe',alt:d.g,neu:v})}});
D.addEventListener('keydown',e=>{if(e.key=='Enter'&&e.target.matches('input[type=text]')){e.preventDefault();e.target.blur()}});
D.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;const d=b.dataset;
 if(d.w){const id_=+d.w,lokal=IDS.reduce((s,i)=>s+st[i].o.filter(o=>o.k==id_).length,0);if((KD.zahl||{})[id_]||lokal){kWeg=id_;return klMal()}const n=K[id_][0];await klPost({art:'weg',id:id_},[`${n} gelöscht`,true])}
 else if(d.ok){const alt=+d.ok,neu=+$('klziel').value,n=K[alt][0],z=Math.max(KD.zahl[alt]||0,IDS.reduce((s,i)=>s+st[i].o.filter(o=>o.k==alt).length,0));kWeg=null;const j=await klPost({art:'weg',id:alt,in:neu},[`${n} → ${K[neu][0]}: ${z}`,true]);if(j){umhaengen(alt,neu);mal()}}
 else if(d.nein){kWeg=null;klMal()}
 else if(d.neu!==undefined){const gr=d.neu||frei('Neue Gruppe',KD.gruppen),n=frei('Neue Klasse',KD.klassen.filter(k=>k.aktiv).map(k=>k.name));const j=await klPost({art:'neu',name:n,gruppe:gr});if(j){const k=j.klassen.find(x=>x.aktiv&&x.name==n);const f=k&&D.querySelector(`[data-n="${k.id}"]`);if(f){f.focus();f.select()}}}});
$('klhz').onclick=async()=>{const l=KD.zurueck;const j=await klPost({art:'zurueck'});if(j&&l&&l.in!=null){umhaengen(l.id,l.in,true);mal()}};
$('klx').onclick=()=>D.close();D.addEventListener('close',()=>{const b=$('klb');b&&b.focus()});

/* Zeiger */
const sv=$('bild'),ort=e=>{const q=new DOMPoint(e.clientX,e.clientY).matrixTransform(sv.getScreenCTM().inverse());return[q.x,q.y]},drin=a=>[kl(a[0],0,B[id].lmm),kl(a[1],0,B[id].qmm)];
sv.onpointerdown=e=>{if(e.button)return;const a=ort(e),d=e.target.dataset;if(zeich){const z=sv.getScreenCTM().a;if(zeich.length>2&&Math.hypot(a[0]-zeich[0][0],a[1]-zeich[0][1])*z<16){e.preventDefault();return schliess()}zeich.push(drin(a));return zstand()}
 if(d.p!==undefined){zieh={j:+d.p,a,x:e.clientX,y:e.clientY,an:false};sv.setPointerCapture(e.pointerId);return}
 pan={x:e.clientX,y:e.clientY,v:[...V],w:false,o:d.o===undefined?-1:+d.o};sv.setPointerCapture(e.pointerId)};
sv.onpointermove=e=>{if(zeich){maus=e.pointerType=='touch'?null:drin(ort(e));if(zeich.length)bildZ();return}
 if(zieh){if(!zieh.an){if(Math.hypot(e.clientX-zieh.x,e.clientY-zieh.y)<4)return;merk();backe(akt());zieh.s=akt().b.map(q=>[...q]);zieh.an=true}const a=ort(e);akt().b=schieb(zieh.s,zieh.j,a[0]-zieh.a[0],a[1]-zieh.a[1]);return bildZ()}
 if(pan){const z=sv.getScreenCTM().a,dx=e.clientX-pan.x,dy=e.clientY-pan.y;if(Math.hypot(dx,dy)>4)pan.w=true;if(pan.w){V[0]=pan.v[0]-dx/z;V[1]=pan.v[1]-dy/z;rand();bildZ()}}};
sv.onpointerup=e=>{if(zieh){const w=zieh;zieh=null;if(w.an)mal();else{pkt=w.j;mal()}}else if(pan){const p=pan;pan=null;if(p.w)return;if(p.o>=0&&(e.ctrlKey||e.metaKey))return umschalten(p.o);if(p.o>=0&&e.shiftKey)return bereich(p.o);if(grp()||p.o!=sel)waehle(p.o)}};
sv.onpointercancel=()=>{if(zieh&&zieh.an)mal();zieh=pan=null};
sv.addEventListener('wheel',e=>{e.preventDefault();const a=ort(e);zoom((e.deltaY||e.deltaX)<0?.85:1/.85,a[0],a[1])},{passive:false});
const fin=new Map;let zwei=null;const lage=()=>{const[a,b]=[...fin.values()];return{x:(a[0]+b[0])/2,y:(a[1]+b[1])/2,d:Math.hypot(a[0]-b[0],a[1]-b[1])||1}};
sv.addEventListener('pointerdown',e=>{if(e.pointerType!='touch')return;fin.set(e.pointerId,[e.clientX,e.clientY]);if(fin.size==2){if(zieh&&zieh.an)return;zieh=pan=null;if(zeich){zeich.pop();zstand()}zwei=lage();e.stopPropagation()}else if(fin.size>2)e.stopPropagation()},true);
sv.addEventListener('pointermove',e=>{if(!fin.has(e.pointerId))return;fin.set(e.pointerId,[e.clientX,e.clientY]);if(!zwei)return;e.stopPropagation();if(fin.size<2)return;const n=lage(),z=sv.getScreenCTM().a;V[0]-=(n.x-zwei.x)/z;V[1]-=(n.y-zwei.y)/z;rand();const m=ort({clientX:n.x,clientY:n.y});zoom(zwei.d/n.d,m[0],m[1]);zwei=n},true);
for(const t of['pointerup','pointercancel'])sv.addEventListener(t,e=>{fin.delete(e.pointerId);if(zwei){e.stopPropagation();if(!fin.size)zwei=null}},true);
addEventListener('beforeunload',e=>{if(IDS.some(i=>st[i].dreck)||zeich&&zeich.length){e.preventDefault();e.returnValue=''}});
addEventListener('keydown',e=>{if(!id)return;const t=e.target;if(t.closest&&t.closest('dialog,input[type=number],input[type=text],select'))return;const tk=e.key.toLowerCase(),strg=e.ctrlKey||e.metaKey,hat=s=>t.closest&&t.closest(s);
 if(e.repeat&&(['Enter','Delete','Backspace'].includes(e.key)||'snu'.includes(tk)))return e.preventDefault();
 if(strg&&(tk=='y'||tk=='z'&&e.shiftKey)){e.preventDefault();return wieder()}if(strg&&tk=='z'){e.preventDefault();return gzurZuletzt&&gzur.length?gruppeRueck():fwegZuletzt&&fweg.length?fotoZurueck():rueck()}if(strg&&tk=='a'&&!zeich){e.preventDefault();return waehleRegel({art:'alle'})}if(strg||e.altKey)return;
 if(e.key=='Escape'&&zeich)return zeichnen(false);if(e.key=='Escape'&&grp()){leeren();return mal()}
 if((e.key=='Delete'||e.key=='Backspace')&&hat('#p-film .fb,#p-film .fweg')){e.preventDefault();return fotoWeg(t.dataset.b||t.dataset.weg)}
 if(e.key=='Enter'){if(zeich){if(hat('button'))return;e.preventDefault();return schliess()}if(t==document.body||t==sv||hat('.zl[aria-pressed=true]')||hat('#p-insp input')){e.preventDefault();gut(true)}return}
 if(zeich){if(e.key=='Backspace'){e.preventDefault();rueck()}else if(tk=='n')zeichnen(false);return}
 const k=KL[+e.key-1];if(k)return setK(k);
 if(tk=='k'&&akt())return waehleRegel({art:'k',k:akt().k});if(tk=='g'&&akt()&&akt().c!=null)return waehleRegel({art:'c',c:akt().c});if(tk=='b')return balkenweit();
 if(e.key=='PageUp'||e.key=='PageDown'){e.preventDefault();return wechsel(e.key=='PageUp'?-1:1)}
 const pf={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[e.key];if(pf&&(t==sv||t==document.body)){e.preventDefault();return schwenk(...pf)}
 if(e.key=='Delete'||e.key=='Backspace')loesch(true);else if(e.key=='+')zoom(.6);else if(e.key=='-')zoom(1/.6);else if(e.key=='0'){ganz();bildZ()}else if(tk=='n')zeichnen(true);else if(tk=='u')umrisse(!nur);else if(tk=='s')speich()});
/* Fotos vom Server */
let lfd=0;const uhrzeit=t=>t.slice(11,16);
const dicht=p=>{const q=flae(p)<0?[...p].reverse():p;return q.length>120?ber(q,120):q},messen=i=>new Promise((ja,nein)=>{const b=B[i];if(b.qmm)return ja();const im=new Image;im.onerror=async()=>{let t='Bild nicht ladbar.';try{const a=await fetch(b.src);if(!a.ok)t=(await a.json()).fehler}catch(e){t='Keine Verbindung zu Neurolign.'}nein(Error(t))};
 im.onload=()=>{const l=b.laengs||168;b.lmm=l;b.qmm=l*im.naturalHeight/im.naturalWidth;if(!b.laengs)b.px=im.naturalWidth/l;
  st[i]={o:(b.roh||[]).map(o=>({k:o.k,c:o.c??null,ok:o.ok,r:0,g:0,b:dicht(o.p.map(q=>[q[0]*b.lmm,q[1]*b.qmm])),x:{q:o.q,kv:o.kv},m:o.m||[]})),zeit:st[i].zeit,dreck:false,h:[],v:[]};ja()};im.src=b.src});
const SATZ_L=new URLSearchParams(location.search).get('satz')=='kodytek';
/* Vorlabeln (vorlabeln.js): Knopf im Kopf jeder Balken-Gruppe und am aktuellen Foto. Ist ein Balken fertig, holt die
   Seite seine Labels neu; Fotos mit ungespeicherten Änderungen bleiben (ihr Speichern meldet dann den Konflikt). */
async function vorlabeln(b,foto){try{await VL.start([b],foto?[foto]:[])}catch(e){fehler('Nicht vorgelabelt: '+e.message)}}
async function nachVorlabeln(b){let a;try{a=await(await fetch('/api/bilder')).json()}catch(e){return}let neuAuf=false;
 for(const x of a){const i=x.name;if(x.balken!=b||!B[i]||st[i].dreck)continue;if((B[i].zv||null)==(x.zeit||null))continue;
  B[i].roh=x.objekte;B[i].zv=x.zeit||null;delete B[i].qmm;st[i]={o:(x.objekte||[]),zeit:x.zeit&&uhrzeit(x.zeit),dreck:false,h:[],v:[]};if(i==id)neuAuf=true}
 if(neuAuf)await oeffne(id);else if(id)filmBau(true)}
if(!SATZ_L){VL.beiStand=()=>{if(id)filmBau(true)};VL.beiFertig=b=>nachVorlabeln(b);VL.laden()}
(async()=>{try{const n=(await(await fetch('/api/saetze')).json()).kodytek;$('satz').hidden=!n;$('satz').value=SATZ_L?'kodytek':''}catch(e){}})();
$('satz').onchange=()=>{const w=$('satz').value;$('satz').value=SATZ_L?'kodytek':'';location.href='/labeln'+(w?'?satz='+w:'')};
addEventListener('pageshow',()=>$('satz').value=SATZ_L?'kodytek':'');
gestalte();reiter('liste');
(async()=>{let a;try{klassenSetzen(await(await fetch('/api/klassen')).json());a=await(await fetch('/api/bilder'+(SATZ_L?'?satz=kodytek':''))).json()}catch(e){return fehler('Keine Verbindung zu Neurolign.')}
 for(const x of a){IDS.push(x.name);B[x.name]={src:`/zuschnitt/${x.name}.jpg`,klein:`/zuschnitt/${x.name}_k.jpg`,name:x.titel,balken:x.balken,seite:x.seite,nr:x.nr,nb:x.name_b||'',frei:!!x.frei,laengs:x.laengs_mm,roh:x.objekte,zv:x.zeit||null};st[x.name]={o:(x.objekte||[]),zeit:x.zeit&&uhrzeit(x.zeit),dreck:false,h:[],v:[]}}
 if(!IDS.length){$('leerseite').hidden=false;$('leerseite').innerHTML='<p>Noch keine Fotos.</p><a href="/">Zur Aufnahme</a>';$('aktion').hidden=$('sp').hidden=true;return}
 const w=new URLSearchParams(location.search).get('balken'),l=w?a.filter(x=>x.balken===w).map(x=>x.name):IDS;
 await oeffne((l.length?l:IDS).find(i=>!st[i].zeit||offen(i))||(l[0]||IDS[0]));if(id)new ResizeObserver(()=>bildZ()).observe(sv)})();
