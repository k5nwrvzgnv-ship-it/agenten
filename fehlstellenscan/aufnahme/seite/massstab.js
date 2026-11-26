/* cm-Raster und digitaler Zollstock in Labeln (Jan 26.11.2026: "Cm raster einstellbar, Digitalen Zollstock
   einblendbar (einmessbar)"). Das Bild liegt in mm (viewBox), darum zeichnen Raster und Zollstock direkt in mm.
   Einmessen: Zollstock mit zwei Klicks setzen, Enden auf zwei bekannte Punkte ziehen, echte Länge eingeben. Daraus
   wird mm je Pixel des Zuschnitts, gespeichert je Foto (/api/foto-massstab), gilt dann für Maße und Raster.
   Wird vor labeln.js geladen und nutzt dessen Namen (B, id, V, S, px, bildZ, sag, fehler, ruf) erst beim Aufruf. */
'use strict';
const MS=(()=>{
 const WEITEN=[10,20,50,100];let raster=false,weite=10,an=false,setzen=null,maus=null,zug=null;const L={};
 try{raster=localStorage.getItem('nl-raster')=='1';const w=+localStorage.getItem('nl-weite');if(WEITEN.includes(w))weite=w}catch(e){}
 const merken=()=>{try{localStorage.setItem('nl-raster',raster?'1':'0');localStorage.setItem('nl-weite',String(weite))}catch(e){}};
 const zahl=x=>x.toFixed(1).replace('.',',');
 const laenge=l=>Math.hypot(l.b[0]-l.a[0],l.b[1]-l.a[1]);
 const echt=()=>!px();
 /* Raster ab der linken oberen Bildecke, jede fünfte Linie kräftiger. Zu dicht gezeichnet wird nur die kräftige. */
 function rasterSvg(z){if(!raster||!echt())return'';const b=B[id];let w=weite,stark=5;if(w/z<6){w*=5;stark=1}if(w/z<6)return'';
  const x0=Math.max(0,Math.floor(V[0]/w)*w),x1=Math.min(b.lmm,V[0]+V[2]),y0=Math.max(0,Math.floor(V[1]/w)*w),y1=Math.min(b.qmm,V[1]+V[3]);let d1='',d2='';
  for(let x=x0,n=Math.round(x0/w);x<=x1+1e-6;x+=w,n++)(n%stark?(d1+=`M${x} ${y0}V${y1}`):(d2+=`M${x} ${y0}V${y1}`));
  for(let y=y0,n=Math.round(y0/w);y<=y1+1e-6;y+=w,n++)(n%stark?(d1+=`M${x0} ${y}H${x1}`):(d2+=`M${x0} ${y}H${x1}`));
  return`<g class="raster" pointer-events="none" fill="none"><path d="${d1}" stroke="#000" stroke-opacity=".35" stroke-width="${2*z}"/><path d="${d1}" stroke="#fff" stroke-opacity=".55" stroke-width="${z}"/><path d="${d2}" stroke="#000" stroke-opacity=".45" stroke-width="${3*z}"/><path d="${d2}" stroke="#fff" stroke-opacity=".85" stroke-width="${1.5*z}"/></g>`}
 /* Zollstock: Messkante von a nach b, gelbes Band auf einer Seite, mm-, halbe-cm- und cm-Teilung, Zahl je cm.
   Ohne Maßstab nur die Strecke in px: unbekannte Teilung wird nicht gezeichnet. */
 function linealSvg(z){if(!an||!id)return'';const l=L[id];const T=matchMedia('(pointer:coarse)').matches,hr=(T?18:12)*z;
  if(setzen){if(!setzen.length)return'';const a=setzen[0],m=maus||a;return`<g pointer-events="none"><path d="M${a}L${m}" stroke="${DUNKEL}" stroke-width="${4*z}"/><path d="M${a}L${m}" stroke="#f2c230" stroke-width="${2*z}"/><circle cx="${a[0]}" cy="${a[1]}" r="${5*z}" fill="#f2c230" stroke="${DUNKEL}" stroke-width="${1.5*z}"/></g>`}
  if(!l)return'';const n=laenge(l)||1e-9,u=[(l.b[0]-l.a[0])/n,(l.b[1]-l.a[1])/n],v=[u[1],-u[0]],P=(t,s)=>[l.a[0]+u[0]*t+v[0]*s*z,l.a[1]+u[1]*t+v[1]*s*z];
  const ang=Math.atan2(u[1],u[0])*180/Math.PI,txt=echt()?zahl(n)+' mm':Math.round(n*B[id].px)+' px';let g='';
  if(echt()){const h=26,ecke=[P(0,0),P(n,0),P(n,h),P(0,h)];g+=`<path class="zk" d="M${ecke.join('L')}Z" fill="#f2c230" fill-opacity=".5" stroke="${DUNKEL}" stroke-width="${z}"/>`;
   const fein=1/z>=4,halb=5/z>=5,schritt=fein?1:halb?5:10,ziffer=[1,2,5,10,20,50].find(k=>k*10/z>=26)||100;let t='',zi='';
   for(let mm=0;mm<=n+1e-6;mm+=schritt){const r=Math.round(mm),lang=r%10==0?13:r%5==0?9:5;t+=`M${P(mm,0)}L${P(mm,lang)}`;
    if(r%10==0&&(r/10)%ziffer==0&&r>0&&n-mm>2*z*10){const q=P(mm,20);zi+=`<text x="${q[0]}" y="${q[1]}" font-size="${11*z}" text-anchor="middle" dominant-baseline="middle" transform="rotate(${ang} ${q[0]} ${q[1]})" fill="#1b1b1b">${r/10}</text>`}}
   g+=`<path d="${t}" stroke="#1b1b1b" stroke-width="${z}" fill="none" pointer-events="none"/>${zi}`}
  else g+=`<path class="zk" d="M${l.a}L${l.b}" stroke="transparent" stroke-width="${20*z}"/><path d="M${l.a}L${l.b}" stroke="${DUNKEL}" stroke-width="${4*z}" pointer-events="none"/><path d="M${l.a}L${l.b}" stroke="#f2c230" stroke-width="${2*z}" pointer-events="none"/>`;
  for(const[e,q]of[['a',l.a],['b',l.b]])g+=`<circle cx="${q[0]}" cy="${q[1]}" r="${5*z}" fill="#f2c230" stroke="${DUNKEL}" stroke-width="${1.5*z}" pointer-events="none"/><circle class="ze" data-ze="${e}" cx="${q[0]}" cy="${q[1]}" r="${hr}" fill="transparent"/>`;
  const q=P(n/2,echt()?-14:-12),dreh=ang>90||ang<-90?ang+180:ang;
  g+=`<text x="${q[0]}" y="${q[1]}" font-size="${13*z}" text-anchor="middle" dominant-baseline="middle" transform="rotate(${dreh} ${q[0]} ${q[1]})" fill="#fff" stroke="#000" stroke-width="${4*z}" paint-order="stroke" stroke-linejoin="round" pointer-events="none">${txt}</text>`;
  return`<g class="zollstock">${g}</g>`}
 /* Knöpfe in der Werkzeugleiste: Zustand als gedrückter Knopf, Weite als gedrückte Zahl, Länge als Feld */
 function leiste(){$('raster').setAttribute('aria-pressed',raster);$('raster').classList.toggle('wartet',raster&&!echt());$('weiten').hidden=!raster||!echt();for(const b of $('weiten').querySelectorAll('button'))b.setAttribute('aria-pressed',+b.dataset.w==weite);
  $('zoll').setAttribute('aria-pressed',an);const l=id&&L[id],f=$('zl-l');$('einm').hidden=!an||!!setzen||!l;if(l&&(document.activeElement!=f||!f.value))f.placeholder=echt()?zahl(laenge(l)):'';
  $('bild').classList.toggle('setzen',!!setzen)}
 function zollAn(neu){an=neu;setzen=an&&!(id&&L[id])?[]:null;maus=null;zug=null;bildZ();leiste()}
 function rasterAn(neu){raster=neu;merken();if(raster&&!echt()&&!an)zollAn(true);bildZ();leiste()}
 /* Zeiger: true heißt, der Zollstock hat das Ereignis genommen */
 function runter(e,a){if(!an)return false;if(setzen){setzen.push(a);if(setzen.length==2){L[id]={a:setzen[0],b:setzen[1]};setzen=null;maus=null;bildZ();leiste();$('zl-l').focus({preventScroll:true})}else bildZ();return true}
  const d=e.target.dataset;if(d.ze){zug={e:d.ze,s:{a:[...L[id].a],b:[...L[id].b]},a};return true}if(e.target.classList.contains('zk')){zug={e:'ab',s:{a:[...L[id].a],b:[...L[id].b]},a};return true}return false}
 function zieh(e,a){if(setzen){maus=a;if(setzen.length)bildZ();return true}if(!zug)return false;const l=L[id],dx=a[0]-zug.a[0],dy=a[1]-zug.a[1];
  if(zug.e=='ab'){l.a=[zug.s.a[0]+dx,zug.s.a[1]+dy];l.b=[zug.s.b[0]+dx,zug.s.b[1]+dy]}
  else{const fest=zug.e=='a'?l.b:l.a;let p=[zug.s[zug.e][0]+dx,zug.s[zug.e][1]+dy];if(e.shiftKey){const r=Math.hypot(p[0]-fest[0],p[1]-fest[1]),w=Math.round(Math.atan2(p[1]-fest[1],p[0]-fest[0])/(Math.PI/12))*Math.PI/12;p=[fest[0]+r*Math.cos(w),fest[1]+r*Math.sin(w)]}l[zug.e]=p}
  bildZ();leiste();return true}
 function hoch(){if(!zug)return false;zug=null;return true}
 /* Maßstab umstellen: alles, was in mm des aktuellen Fotos liegt, mit dem Faktor mitziehen (Labels selbst sind in
    Anteilen gespeichert und ändern sich nicht). */
 function umrechnen(i,f){const b=B[i],s=st[i],x=o=>({...o,b:o.b.map(q=>[q[0]*f,q[1]*f]),r:o.r*f});b.lmm*=f;b.qmm*=f;s.o=s.o.map(x);
  for(const k of['h','v'])s[k]=s[k].map(j=>{const[o,sel_]=JSON.parse(j);return JSON.stringify([o.map(x),sel_])});
  if(i==id){V=V.map(w=>w*f);if(L[i])L[i]={a:L[i].a.map(w=>w*f),b:L[i].b.map(w=>w*f)}}}
 function anwenden(i,mmpx){const b=B[i];b.mmpx=mmpx;const ziel=mmpx?b.nw*mmpx:(b.laengs||168);if(mmpx||b.laengs)delete b.px;else b.px=b.nw/ziel;if(b.qmm)umrechnen(i,ziel/b.lmm)}
 async function speichern(i,mmpx){return ruf('/api/foto-massstab',{name:i,mm_je_px:mmpx})}
 async function einmessen(){const l=L[id],f=$('zl-l'),w=+String(f.value).replace(',','.');if(!l||!(w>0&&w<=100000))return f.focus();
  const bildpx=laenge(l)*B[id].nw/B[id].lmm;if(bildpx<5)return sag('Zollstock länger ziehen.');const mmpx=w/bildpx,i=id,vorher=B[i].mmpx||null;
  try{await speichern(i,mmpx)}catch(e){return fehler('Nicht eingemessen: '+(e instanceof TypeError?'Keine Verbindung zu Neurolign.':e.message))}
  anwenden(i,mmpx);f.value='';mal();leiste();sag(`${zahl(w)} mm`,'Rückgängig',async()=>{try{await speichern(i,vorher)}catch(e){return fehler('Nicht zurückgenommen: '+e.message)}anwenden(i,vorher);if(i==id){mal();leiste()}})}
 return{rasterSvg,linealSvg,leiste,runter,zieh,hoch,einmessen,setzt:()=>!!setzen,an:()=>an,
  raster:()=>rasterAn(!raster),zoll:()=>zollAn(!an),weite:w=>{weite=w;merken();bildZ();leiste()},
  foto:()=>{zug=null;maus=null;setzen=an&&!L[id]?[]:null},
  abbrechen:()=>{if(setzen){zollAn(false);return true}return false}}})();
