/* Geometrie, Maße, Doppelerkennung und Speichern nach werkbank-looks/bedienung.js, Oberfläche neu. */
'use strict';
const $=i=>document.getElementById(i),SCHL='werkbank-regler',B=DATEN.bilder,IDS=['153200004','153200015','153200022'];
/* Klasse: Name, Farbe, Strichmuster (zweites Merkmal neben der Farbe) */
const K={0:['Ast lebend','#22C55E',''],1:['Ast tot','#A78BFA','9 4'],2:['Astloch','#0080FF','3 3'],3:['Ast mit Riss','#EF4444','12 3 3 3'],4:['Riss','#EC4899','5 4'],6:['Harz','#26A69A','16 4']},KL=Object.keys(K);
KL.forEach((k,n)=>Object.defineProperty(K[k],1,{get:()=>KF(n)}));
const DUNKEL='#111318';
for(const i of IDS)B[i].src=(window.BILDER&&BILDER[i])||i+'.jpg';
const kl=(x,a,b)=>Math.max(a,Math.min(b,x)),fix=x=>x.toFixed(1).replace('.',',').replace('-','−'),esc=s=>String(s).replace(/[&<>"]/g,c=>'&#'+c.charCodeAt(0)+';');
const ic=n=>`<svg class="i" aria-hidden="true"><use href="#i-${n}"/></svg>`,muster=k=>`<svg class="mu" viewBox="0 0 24 8" aria-hidden="true"><path d="M0 4H24" stroke="${K[k][1]}" stroke-width="4" ${K[k][2]&&W().muster=='an'?`stroke-dasharray="${K[k][2]}"`:''}/></svg>`;
const flae=p=>p.reduce((s,a,i)=>{const b=p[(i+1)%p.length];return s+a[0]*b[1]-b[0]*a[1]},0);
function ber(p,n){const L=[0];p.forEach((a,i)=>{const b=p[(i+1)%p.length];L.push(L[i]+Math.hypot(b[0]-a[0],b[1]-a[1]))});const o=[];let j=0;for(let k=0;k<n;k++){const t=L[p.length]*k/n;while(j<p.length-1&&L[j+1]<t)j++;const a=p[j],b=p[(j+1)%p.length],f=(t-L[j])/((L[j+1]-L[j])||1);o.push([a[0]+f*(b[0]-a[0]),a[1]+f*(b[1]-a[1])])}return o}
const obj=(k,c,p)=>({k,c,b:ber(flae(p)<0?[...p].reverse():p,28),r:0,g:0,ok:false});
const lies=()=>{try{return JSON.parse(localStorage.getItem(SCHL)||'{}')||{}}catch(e){return{}}};
const st={},halt=lies();
function lade(i){const h=halt[i];st[i]={o:h&&h.o?h.o:B[i].modell.map(o=>obj(o.k,o.c,o.p)),zeit:h&&h.zeit||null,dreck:false,h:[],v:[]}}
IDS.forEach(lade);
let id=IDS[0],sel=-1,pkt=0,zeich=null,maus=null,zieh=null,pan=null,nur=false,auf=false,V=null,uhr,tab='liste';
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
function merk(){const s=S();s.h.push(JSON.stringify([s.o,sel]));if(s.h.length>80)s.h.shift();s.v=[];s.dreck=true}
function sag(t,k,f,bleibt){$('hin').hidden=false;$('hint').textContent=t;$('hink').hidden=!k;$('hink').textContent=k||'';$('hink').onclick=()=>{stumm();f&&f()};clearTimeout(uhr);if(!bleibt)uhr=setTimeout(stumm,5000)}
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
 if(!nur){const reihe=S().o.map((o,i)=>i).sort((a,b)=>(a==sel)-(b==sel));for(const i of reihe){const o=S().o[i],a=i==sel,p=form(o),f=K[o.k][1],d=pfad(p),da=K[o.k][2]&&w.muster=='an'?`stroke-dasharray="${K[o.k][2].split(' ').map(x=>x*z).join(' ')}"`:'';
 s+=`<path class="o" data-o="${i}" d="${d}" fill="${f}" fill-opacity="${a?w.fuell*.4:w.fuell}" stroke="${a?W().auswahl:DUNKEL}" stroke-width="${(a?sw+4.500:sw+2.500*w.saum)*z}"/>${a?`<path d="${d}" fill="none" stroke="${DUNKEL}" stroke-width="${(sw+1.500*w.saum)*z}" pointer-events="none"/>`:''}<path d="${d}" fill="none" stroke="${f}" stroke-width="${sw*z}" ${da} pointer-events="none"/>`;
 const xs=p.map(q=>q[0]),ys=p.map(q=>q[1]),li=Math.min(...xs),re=Math.max(...xs),ob=Math.min(...ys),un=Math.max(...ys);
 if(!a)tags+=tag((li+re)/2,doppelt(i)>=0?un+8*z:ob-26*z,bu(i)+(o.ok?' ✓':''),f,'m');
 else if(!zeich){if(w.linieM=='an'&&!angs(p)){const m=mass(p),P=x=>[m.u[0]*x+m.v[0]*m.m,m.u[1]*x+m.v[1]*m.m],A=P(m.lo),E=P(m.hi);s+=`<path d="M${A}L${E}" stroke="${DUNKEL}" stroke-width="${4*z}" pointer-events="none"/><path d="M${A}L${E}" stroke="${W().auswahl}" stroke-width="${1.500*z}" pointer-events="none"/>`}
  const dp=streit(i);if(dp>=0)s+=`<path d="${pfad(form(S().o[dp]))}" fill="none" stroke="${K[S().o[dp].k][1]}" stroke-width="${sw*z}" stroke-dasharray="${6*z} ${8*z}" pointer-events="none"/>`;
  p.forEach((q,j)=>{const hier=auf&&j==pkt;if(j%(T?4:2)&&!hier)return;const g=hier?w.pgr+3:w.pgr;if(w.punkte!='aus'||hier)s+=`<rect x="${q[0]-g*z}" y="${q[1]-g*z}" width="${2*g*z}" height="${2*g*z}" rx="${w.punkte=='rund'?g*z:0}" fill="${hier?W().akzent:W().auswahl}" stroke="${DUNKEL}" stroke-width="${z}" pointer-events="none"/><circle class="pk" data-p="${j}" cx="${q[0]}" cy="${q[1]}" r="${(T?16:11)*z}" fill="transparent"/>`});
  tags+=tag((li+re)/2,ob-32*z<V[1]?un+12*z:ob-32*z,w.schild=='kurz'?bu(i):`${bu(i)} ${K[o.k][0]}, ${gr(p)}`,W().auswahl,'m')}}
 s+=tags;
 if(zeich&&zeich.length){const l=[...zeich,maus||zeich.at(-1)].join(' ');s+=`<polyline points="${l}" fill="none" stroke="${DUNKEL}" stroke-width="${5*z}"/><polyline points="${l}" fill="none" stroke="${W().auswahl}" stroke-width="${2*z}"/>`;zeich.forEach((q,i)=>{const g=(i?4:8)*z;s+=`<rect x="${q[0]-g}" y="${q[1]-g}" width="${2*g}" height="${2*g}" fill="${W().auswahl}" stroke="${DUNKEL}" stroke-width="${z}"/>`})}}
 sv.innerHTML=s;sv.classList.toggle('zeichnen',!!zeich);$('fit').hidden=$('minus').disabled=voll();$('plus').disabled=V[2]<=12.01;
 const ein=px()?B[id].px:1,ziel=90*z*ein,e=10**Math.floor(Math.log10(ziel)),n=[5,2,1].find(x=>x*e<=ziel)*e;$('mstt').textContent=n+(px()?' px':' mm');$('mstb').style.width=n/ein/z+'px';knoepfe()}
function knoepfe(){const s=S();$('rueck').hidden=zeich?!zeich.length:!s.h.length;$('wieder').hidden=!!zeich||!s.v.length;$('sp').hidden=!s.dreck||!offen(id)}
/* Liste, Bearbeiten, Bilderleiste */
function liste(){const s=S(),n=s.o.length,g=n-offen(id);$('stand').textContent=n?`${g} von ${n} geprüft`:'';$('fort').max=n||1;$('fort').value=n?g:0;
 $('liste').innerHTML=n?folge().map(i=>{const o=s.o[i],p=form(o),c=o.c===null?'neu':Math.round(o.c*100)+' %',un=o.c!==null&&o.c<.7;return`<li><button class="zl" data-i="${i}" data-f="z${i}" aria-pressed="${i==sel}"><span class="n"><span class="bu">${bu(i)}</span>${muster(o.k)}<span>${K[o.k][0]}</span></span><span class="mx">${gr(p)}</span><span class="ki ${o.ok?'ok':''}">${o.ok?ic('check')+'<span class="vs">geprüft, </span>':un?ic('warning')+'<span class="vs">unsicher, </span>':''}<span class="kz">${c}</span>${o.c===null?'':`<i class="bk" style="--p:${o.c}"></i>`}</span></button></li>`}).join(''):`<li class="leer">${px()?'Kein Vorlabel: Das Modell läuft in diesem Entwurf nicht. Umriss mit Zeichnen anlegen.':'Keine Objekte. Mit Zeichnen anlegen oder so speichern.'}</li>`}
const kacheln=(o,p)=>`<div><span>kleinster ⌀</span><b>${gr(p)}</b></div><div><span>größter ⌀</span><b>${angs(p)?'–':wert(mass(p).x)}</b></div><div><span>KI sicher</span><b>${o.c===null?'neu':Math.round(o.c*100)+' %'}</b></div>`;
const rg=(i,n,a,lo,hi,s,t,k,g)=>`<div class="rg"><div><label for="${i}">${n}</label><output id="${i}v" for="${i}">${t}</output></div><div><button class="ib" data-s="${i}" data-v="-1" data-f="${i}-" aria-label="${n}: ${k}">${ic('minus')}</button><input id="${i}" data-f="${i}" type="range" min="${lo}" max="${hi}" step="${s}" value="${a}" aria-valuetext="${t}"><button class="ib" data-s="${i}" data-v="1" data-f="${i}+" aria-label="${n}: ${g}">${ic('plus')}</button></div></div>`;
function insp(){const o=akt(),e=$('p-insp');if(!o){e.innerHTML=`<p class="leer">${!S().o.length?'Kein Objekt im Bild.':offen(id)?'Objekt im Bild oder in der Liste wählen.':$('gut').hidden?'Alle Bilder geprüft und gespeichert.':'Alle Objekte geprüft.'}</p>`;return}
 const p=form(o);e.innerHTML=`<h2 class="titel">${bu(sel)} ${muster(o.k)} ${K[o.k][0]}${o.ok?' '+ic('check-circle'):''}</h2><div class="kpi">${kacheln(o,p)}</div>
<fieldset><legend>Klasse</legend><div class="kl">${KL.map((k,n)=>`<label><input type="radio" name="kl" value="${k}" data-f="k${k}" ${k==o.k?'checked':''}>${muster(k)}<span>${K[k][0]}</span><kbd aria-hidden="true">${n+1}</kbd></label>`).join('')}</div></fieldset>
<fieldset><legend>Umriss</legend>${rg('r','Größe',o.r,-4,4,.1,wr(o),'kleiner','größer')}${rg('g','Glätten',o.g,0,8,1,o.g,'weniger','mehr')}</fieldset>
<details ${auf?'open':''}><summary data-f="det">${ic('caret-right')}Einzelnen Punkt verschieben</summary><p>Punkte im Bild ziehen oder hier schrittweise, 0,5 mm je Klick.</p><div class="pkt"><button class="ib" data-n="-1" data-f="n-" aria-label="Voriger Punkt">${ic('arrow-left')}</button><span class="mono">Punkt ${pkt+1}</span><button class="ib" data-n="1" data-f="n+" aria-label="Nächster Punkt">${ic('arrow-right')}</button></div><div class="pkt" style="margin-top:8px">${[['Links',-1,0],['Rechts',1,0],['Hoch',0,-1],['Runter',0,1]].map(([t,x,y])=>`<button class="b" data-x="${x}" data-y="${y}" data-f="m${t}" aria-label="Punkt nach ${t.toLowerCase()}">${t}</button>`).join('')}</div></details>`}
function dopp(){const d=streit(sel);$('dopp').hidden=d<0;if(d<0){$('dopp').innerHTML='';return}$('dopp').innerHTML=`<p>${ic('warning')}<span>${bu(sel)} und ${bu(d)} liegen auf derselben Stelle.</span></p><div>${[sel,d].sort((a,b)=>bu(a)<bu(b)?-1:1).map(i=>`<button class="b" data-weg="${i==sel?d:sel}" data-f="w${i}">${bu(i)} behalten</button>`).join('')}</div>`}
function fuss(){const s=S(),n=IDS.indexOf(id),o=akt(),g=$('gut'),fertig=!offen(id);$('lo').hidden=!o;g.hidden=!!zeich||fertig&&!s.dreck&&!!s.zeit&&!IDS.some(i=>i!=id&&(!st[i].zeit||st[i].dreck||offen(i)));const t=o?(o.ok?(fertig?'Speichern, nächstes Bild':'Nächstes Objekt'):streit(sel)>=0?'Beide lassen':'Stimmt'):fertig?'Speichern, nächstes Bild':'Erstes offenes Objekt';g.querySelector('span').textContent=t;g.querySelector('use').setAttribute('href',fertig?'#i-floppy-disk':o&&!o.ok?'#i-check':'#i-arrow-right');
 $('spstand').textContent=s.dreck?'Nicht gespeicherte Änderungen':s.zeit?`Gespeichert ${s.zeit}, nur ${px()&&!B[id].fest?'bis zum Neuladen':'in diesem Browser'}`:'Noch nicht gespeichert';
 $('pos').innerHTML=`<b>${esc(name(id))}</b> <span>${n+1} von ${IDS.length}</span>`;$('vor').disabled=!n;$('nach').disabled=n==IDS.length-1;
 $('p-film').innerHTML=IDS.map(i=>{const t=st[i],of=offen(i),w=t.dreck?'geändert, nicht gespeichert':t.zeit?(of?`gespeichert, ${of} offen`:'gespeichert'):t.o.length?`${of} offen`:'leer';return`<button data-b="${i}" data-f="b${i}" ${i==id?'aria-current="true"':''}><img src="${B[i].src}" alt="" width="56" height="48"><span><b>${esc(name(i))}</b><small>${w}</small></span></button>`}).join('')+`<button id="rein" data-f="rein"><svg class="i" aria-hidden="true"><use href="#i-plus"/></svg>Bild hinzufügen</button>`;knoepfe()}
function mal(){const f=document.activeElement&&document.activeElement.dataset?document.activeElement.dataset.f:null,y=$('p-insp').scrollTop;bildZ();liste();fuss();insp();dopp();$('p-insp').scrollTop=y;if(f&&!(document.activeElement&&document.activeElement.dataset.f==f)){const e=document.querySelector(`[data-f="${f}"]`);e&&e.focus({preventScroll:true})}}
function fokus(){const b=document.querySelector('.zl[aria-pressed=true]');if(b&&b.offsetParent){b.focus({preventScroll:true});b.scrollIntoView({block:'nearest'})}else $('gut').focus({preventScroll:true})}
function zeig(i){const p=form(S().o[i]),m=mitte(p);if(!voll()&&(m[0]<V[0]||m[1]<V[1]||m[0]>V[0]+V[2]||m[1]>V[1]+V[3])){V[0]=m[0]-V[2]/2;V[1]=m[1]-V[3]/2;rand()}}
function waehle(i,f){if(i!=sel){pkt=0;auf=false}sel=i;if(i>=0)zeig(i);mal();if(f)fokus()}
function oeffne(i,f){id=i;zeich=null;werk();stumm();ganz();pkt=0;auf=false;sel=erstes();mal();if(f)fokus()}
function reiter(t,f){tab=t;for(const n of['liste','insp','film']){$('p-'+n).classList.toggle('an',n==t);$('t-'+n).setAttribute('aria-selected',n==t);$('t-'+n).tabIndex=n==t?0:-1}if(f)$('t-'+t).focus()}
document.querySelector('.tabs').addEventListener('click',e=>{const b=e.target.closest('button');b&&reiter(b.id.slice(2))});
document.querySelector('.tabs').addEventListener('keydown',e=>{const d={ArrowRight:1,ArrowLeft:-1}[e.key];if(d){const r=['liste','insp','film'];reiter(r[(r.indexOf(tab)+d+3)%3],true);e.stopPropagation()}});
/* Aktionen */
function werk(){$('neu').setAttribute('aria-pressed',!!zeich);$('neu').querySelector('span').textContent=zeich?'Abbrechen':'Zeichnen'}
function umrisse(aus){nur=aus;$('aus').setAttribute('aria-pressed',aus);bildZ()}
function zeichnen(an){zeich=an?[]:null;maus=null;if(an){sel=-1;umrisse(false);sag('Punkte setzen, der erste schließt.','Schließen',schliess,true);$('hink').hidden=true}else stumm();werk();mal()}
function zstand(){bildZ();$('hink').hidden=!zeich||zeich.length<3}
function schliess(){if(!zeich)return;if(zeich.length<3){sag('Mindestens drei Punkte setzen.','Schließen',schliess,true);$('hink').hidden=true;return}const p=zeich;zeichnen(false);merk();S().o.push(obj(1,null,p));waehle(S().o.length-1,true)}
function gut(){const o=akt();if(!o&&!offen(id)||o&&o.ok&&!offen(id))return speich();if(o&&!o.ok){merk();o.ok=true}const f=erstes();waehle(f);f<0?$('gut').focus({preventScroll:true}):fokus()}
function weg(j){const s=S(),bl=s.o[j==sel?doppelt(j):sel],n=`${bu(j)} ${K[s.o[j].k][0]}`;merk();s.o.splice(j,1);waehle(s.o.indexOf(bl),true);sag(n+' gelöscht.','Rückgängig',rueck)}
function loesch(){if(!akt()||zeich)return;const n=`${bu(sel)} ${K[akt().k][0]}`;merk();S().o.splice(sel,1);waehle(erstes(),true);sag(n+' gelöscht.','Rückgängig',rueck)}
function hin(von,nach){const s=S(),h=von.pop();if(!h)return;nach.push(JSON.stringify([s.o,sel]));[s.o,sel]=JSON.parse(h);if(sel>=s.o.length)sel=-1;s.dreck=true;mal()}
function rueck(){if(zeich){zeich.pop();maus=null;return zstand()}stumm();hin(S().h,S().v)}
function wieder(){if(!zeich)hin(S().v,S().h)}
function schritt(k,d){const o=akt(),n=k=='r'?Math.round(kl(o.r+d*.1,-4,4)*10)/10:kl(o.g+d,0,8);if(n==o[k])return;merk();o[k]=n;mal()}
function setK(k){const o=akt();if(o&&o.k!=k){merk();o.k=+k;mal()}}
function backe(o){o.b=form(o);o.r=0;o.g=0}
function schieb(basis,j,dx,dy){const n=basis.length;return basis.map((q,i)=>{let t=Math.abs(i-j);t=Math.min(t,n-t);const f=Math.exp(-t*t/3);return[kl(q[0]+f*dx,0,B[id].lmm),kl(q[1]+f*dy,0,B[id].qmm)]})}
function speich(){if(zeich)return sag('Erst den Umriss schließen oder abbrechen.');const s=S(),zeit=new Date().toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'});
 if(!px()||B[id].fest){try{const a=lies();a[id]={o:s.o,zeit};localStorage.setItem(SCHL,JSON.stringify(a))}catch(e){return fehler('Nicht gespeichert: Der Browser nimmt keine Daten an. Speicher freigeben oder privates Fenster verlassen, dann noch einmal speichern.')}}
 $('fehl').hidden=true;s.zeit=zeit;s.dreck=false;const alt=id,n=IDS.indexOf(id),of=offen(id),t=`${name(id)} gespeichert${of?`, ${of} noch offen`:''}.`;
 const naechst=[...IDS.slice(n+1),...IDS.slice(0,n)].find(i=>!st[i].zeit||st[i].dreck||offen(i));
 if(naechst){oeffne(naechst,true);sag(t,'Dorthin zurück',()=>oeffne(alt,true))}else{mal();sag(of?t:t+' Alle Bilder fertig.')}}
$('liste').onclick=e=>{const b=e.target.closest('.zl');if(b&&!zeich)waehle(+b.dataset.i,true)};
$('dopp').onclick=e=>{const b=e.target.closest('button');if(!b)return;weg(+b.dataset.weg)};
const I=$('p-insp');I.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const d=b.dataset;if(d.s)return schritt(d.s,+d.v);const o=akt(),n=o.b.length;if(d.n){pkt=(pkt+ +d.n+n)%n;return mal()}if(d.x){merk();backe(o);o.b=schieb(o.b,pkt,d.x*.5,d.y*.5);mal()}});
I.addEventListener('toggle',e=>{if(e.target.open!=auf){auf=e.target.open;bildZ()}},true);
let gem=null;I.addEventListener('input',e=>{const t=e.target;if(t.type!='range')return;if(gem!==t){merk();gem=t}const o=akt();o[t.id]=+t.value;const w=t.id=='r'?wr(o):o.g;$(t.id+'v').textContent=w;t.setAttribute('aria-valuetext',w);I.querySelector('.kpi').innerHTML=kacheln(o,form(o));bildZ();liste();fuss()});
I.addEventListener('change',e=>{if(e.target.name=='kl')setK(e.target.value);else{gem=null;mal()}});
$('neu').onclick=()=>zeichnen(!zeich);$('rueck').onclick=rueck;$('wieder').onclick=wieder;$('minus').onclick=()=>zoom(1/.6);$('plus').onclick=()=>{const o=akt();zoom(.6,...(o?mitte(form(o)):[]))};$('fit').onclick=()=>{ganz();bildZ()};$('aus').onclick=()=>umrisse(!nur);
const wechsel=d=>{const i=IDS[IDS.indexOf(id)+d];if(i)oeffne(i)};$('vor').onclick=()=>wechsel(-1);$('nach').onclick=()=>wechsel(1);$('p-film').onclick=e=>{const b=e.target.closest('button');if(b&&b.id=='rein')$('datei').click();else if(b)oeffne(b.dataset.b)};$('sp').onclick=speich;$('gut').onclick=gut;$('lo').onclick=loesch;

/* Zeiger */
const sv=$('bild'),ort=e=>{const q=new DOMPoint(e.clientX,e.clientY).matrixTransform(sv.getScreenCTM().inverse());return[q.x,q.y]},drin=a=>[kl(a[0],0,B[id].lmm),kl(a[1],0,B[id].qmm)];
sv.onpointerdown=e=>{if(e.button)return;const a=ort(e),d=e.target.dataset;if(zeich){const z=sv.getScreenCTM().a;if(zeich.length>2&&Math.hypot(a[0]-zeich[0][0],a[1]-zeich[0][1])*z<16){e.preventDefault();return schliess()}zeich.push(drin(a));return zstand()}
 if(d.p!==undefined){zieh={j:+d.p,a,x:e.clientX,y:e.clientY,an:false};sv.setPointerCapture(e.pointerId);return}
 pan={x:e.clientX,y:e.clientY,v:[...V],w:false,o:d.o===undefined?-1:+d.o};sv.setPointerCapture(e.pointerId)};
sv.onpointermove=e=>{if(zeich){maus=e.pointerType=='touch'?null:drin(ort(e));if(zeich.length)bildZ();return}
 if(zieh){if(!zieh.an){if(Math.hypot(e.clientX-zieh.x,e.clientY-zieh.y)<4)return;merk();backe(akt());zieh.s=akt().b.map(q=>[...q]);zieh.an=true}const a=ort(e);akt().b=schieb(zieh.s,zieh.j,a[0]-zieh.a[0],a[1]-zieh.a[1]);return bildZ()}
 if(pan){const z=sv.getScreenCTM().a,dx=e.clientX-pan.x,dy=e.clientY-pan.y;if(Math.hypot(dx,dy)>4)pan.w=true;if(pan.w){V[0]=pan.v[0]-dx/z;V[1]=pan.v[1]-dy/z;rand();bildZ()}}};
sv.onpointerup=()=>{if(zieh){const w=zieh;zieh=null;if(w.an)mal();else{pkt=w.j;mal()}}else if(pan){const p=pan;pan=null;if(!p.w&&p.o!=sel)waehle(p.o)}};
sv.onpointercancel=()=>{if(zieh&&zieh.an)mal();zieh=pan=null};
sv.addEventListener('wheel',e=>{e.preventDefault();const a=ort(e);zoom((e.deltaY||e.deltaX)<0?.85:1/.85,a[0],a[1])},{passive:false});
const fin=new Map;let zwei=null;const lage=()=>{const[a,b]=[...fin.values()];return{x:(a[0]+b[0])/2,y:(a[1]+b[1])/2,d:Math.hypot(a[0]-b[0],a[1]-b[1])||1}};
sv.addEventListener('pointerdown',e=>{if(e.pointerType!='touch')return;fin.set(e.pointerId,[e.clientX,e.clientY]);if(fin.size==2){if(zieh&&zieh.an)return;zieh=pan=null;if(zeich){zeich.pop();zstand()}zwei=lage();e.stopPropagation()}else if(fin.size>2)e.stopPropagation()},true);
sv.addEventListener('pointermove',e=>{if(!fin.has(e.pointerId))return;fin.set(e.pointerId,[e.clientX,e.clientY]);if(!zwei)return;e.stopPropagation();if(fin.size<2)return;const n=lage(),z=sv.getScreenCTM().a;V[0]-=(n.x-zwei.x)/z;V[1]-=(n.y-zwei.y)/z;rand();const m=ort({clientX:n.x,clientY:n.y});zoom(zwei.d/n.d,m[0],m[1]);zwei=n},true);
for(const t of['pointerup','pointercancel'])sv.addEventListener(t,e=>{fin.delete(e.pointerId);if(zwei){e.stopPropagation();if(!fin.size)zwei=null}},true);
addEventListener('beforeunload',e=>{if(IDS.some(i=>st[i].dreck)||zeich&&zeich.length){e.preventDefault();e.returnValue=''}});
addEventListener('keydown',e=>{const t=e.target;if(t.closest&&t.closest('#feld'))return;const tk=e.key.toLowerCase(),strg=e.ctrlKey||e.metaKey,hat=s=>t.closest&&t.closest(s);
 if(e.repeat&&(['Enter','Delete','Backspace'].includes(e.key)||'snu'.includes(tk)))return e.preventDefault();
 if(strg&&(tk=='y'||tk=='z'&&e.shiftKey)){e.preventDefault();return wieder()}if(strg&&tk=='z'){e.preventDefault();return rueck()}if(strg||e.altKey)return;
 if(e.key=='Escape'&&zeich)return zeichnen(false);
 if(e.key=='Enter'){if(zeich){if(hat('button'))return;e.preventDefault();return schliess()}if(t==document.body||t==sv||hat('.zl[aria-pressed=true]')||hat('#p-insp input')){e.preventDefault();gut()}return}
 if(zeich){if(e.key=='Backspace'){e.preventDefault();rueck()}else if(tk=='n')zeichnen(false);return}
 const k=KL[+e.key-1];if(k)return setK(k);
 if(e.key=='PageUp'||e.key=='PageDown'){e.preventDefault();return wechsel(e.key=='PageUp'?-1:1)}
 const pf={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[e.key];if(pf&&(t==sv||t==document.body)){e.preventDefault();return schwenk(...pf)}
 if(e.key=='Delete'||e.key=='Backspace')loesch();else if(e.key=='+')zoom(.6);else if(e.key=='-')zoom(1/.6);else if(e.key=='0'){ganz();bildZ()}else if(tk=='n')zeichnen(true);else if(tk=='u')umrisse(!nur);else if(tk=='s')speich()});
/* Bilder hinzufügen */
const db=f=>new Promise((ja,nein)=>{try{const q=indexedDB.open(SCHL,1);q.onupgradeneeded=()=>q.result.createObjectStore('b',{keyPath:'i'});q.onerror=nein;q.onsuccess=()=>{const t=q.result.transaction('b','readwrite'),r=f(t.objectStore('b'));t.oncomplete=()=>ja(r&&r.result);t.onerror=t.onabort=nein}}catch(e){nein(e)}});
const dazu=(i,n,f)=>new Promise(ja=>{const u=URL.createObjectURL(f),im=new Image;im.onerror=()=>ja(false);im.onload=()=>{B[i]={src:u,name:n.length>22?n.slice(0,19)+'…':n,lmm:168,qmm:168*im.naturalHeight/im.naturalWidth,px:im.naturalWidth/168,modell:[]};IDS.push(i);lade(i);ja(true)};im.src=u});
async function rein(fs){let erst;for(const f of fs){const i='n'+Date.now()+Math.random();if(!f.type.startsWith('image/')||!await dazu(i,f.name,f)){fehler(f.name+' lässt sich nicht als Bild öffnen. JPG oder PNG wählen.');continue}try{await db(s=>s.put({i,n:f.name,f}));B[i].fest=true}catch(e){fehler('Das Bild bleibt nur bis zum Neuladen, der Browser erlaubt kein Ablegen.')}erst??=i}if(erst){oeffne(erst);sag('Bild hinzugefügt.')}$('datei').value=''}
$('datei').onchange=e=>rein([...e.target.files]);
const bh=$('buehne');bh.ondragover=e=>{e.preventDefault();bh.classList.add('ziel')};bh.ondragleave=()=>bh.classList.remove('ziel');bh.ondrop=e=>{e.preventDefault();bh.classList.remove('ziel');rein([...e.dataTransfer.files])};
gestalte();reiter('liste');oeffne(IDS.find(i=>!st[i].zeit||offen(i))||IDS[0]);new ResizeObserver(()=>bildZ()).observe(sv);
db(s=>s.getAll()).then(async a=>{for(const x of a||[])if(await dazu(x.i,x.n,x.f))B[x.i].fest=true;fuss()}).catch(()=>{});
