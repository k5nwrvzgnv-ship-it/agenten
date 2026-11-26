// Körper eines Balkens: vier Seitenbilder als Mantel um die Längsachse, Stirnseiten grau. Lage der Seiten wie in
// koerper.py: Seite i liegt nach rotateX(90°·i), die nächste Seite stößt an die obere Bildkante.
const $=s=>document.querySelector(s),buehne=$('#kbuehne'),kk=$('#kk');
const START={rx:-22,ry:-32,zoom:1};let A={...START},M=null,id=null,bilder={},weg={};
const zahl=x=>(x>0?'+':x<0?'−':'±')+Math.abs(x).toFixed(1).replace('.',',')+' %';

async function json(weg){let a;try{a=await fetch(weg)}catch(e){throw Error('Das Programm auf dem Mac antwortet nicht. Im Terminal neu starten.')}
 let j={};try{j=await a.json()}catch(e){}if(!a.ok)throw Error(j.fehler||`Fehler ${a.status}`);return j}

function masse(b){const f=n=>b.seiten?.[n]?.plan?.flaeche_mm;
 return {L:b.laenge_mm,W1:f('1')||f('3')||b.hoehe_mm,W2:f('2')||f('4')||b.breite_mm}}

function bauen(){
 if(!M)return;const {L,W1,W2}=M,r=buehne.getBoundingClientRect();
 const k=Math.min(.68*r.width/L,.62*r.height/Math.hypot(W1,W2));
 const fl=[];
 for(let i=1;i<=4;i++){const w=L*k,h=(i%2?W1:W2)*k,d=(i%2?W2:W1)/2*k;
  fl.push(`<div class="kf${bilder[i]?' bild':''}${weg[i]?' weg':''}" data-s="${i}" style="width:${w}px;height:${h}px;left:${-w/2}px;top:${-h/2}px;transform:rotateX(${90*i}deg) translateZ(${d}px);${bilder[i]?`background-image:url('${bilder[i]}')`:''}"></div>`)}
 for(const s of[1,-1]){const w=W1*k,h=W2*k;
  fl.push(`<div class="kf ende" style="width:${w}px;height:${h}px;left:${-w/2}px;top:${-h/2}px;transform:rotateY(${90*s}deg) translateZ(${L*k/2}px)"></div>`)}
 kk.innerHTML=fl.join('');zeigen()}

function vorn(){ // Seite, die am meisten zum Betrachter zeigt
 const g=Math.PI/180,rx=A.rx*g,ry=A.ry*g;let best=0,bz=-2;
 for(let i=1;i<=4;i++){const t=90*i*g,y=-Math.sin(t),z=Math.cos(t),z1=z*Math.cos(ry),zz=Math.sin(rx)*y+Math.cos(rx)*z1;if(zz>bz){bz=zz;best=i}}
 return best}

function zeigen(){kk.style.transform=`scale(${A.zoom}) rotateX(${A.rx}deg) rotateY(${A.ry}deg)`;const v=vorn();
 for(const b of document.querySelectorAll('#kseiten button'))b.setAttribute('aria-pressed',String(+b.dataset.s===v))}

function seiteNachVorn(i){const ziel=-90*i;A.rx=ziel+360*Math.round((A.rx-ziel)/360);A.ry=360*Math.round(A.ry/360);zeigen()}

function knoepfe(K){const box=$('#kseiten');box.innerHTML='';
 for(let i=1;i<=4;i++){const s=K?.seiten?.[i],b=document.createElement('button');b.dataset.s=i;
  if(s?.grund){b.innerHTML=`<b>${i}</b><span class="ab weg">!</span>`;b.title=`Seite ${i}: ${s.grund}, nicht aufgeklebt`}
  else if(s){const a=s.abweichung_prozent,werte=[a.laenge,a.flaeche].filter(x=>x!=null),gross=werte.reduce((m,x)=>Math.abs(x)>Math.abs(m)?x:m,0);
   b.innerHTML=`<b>${i}</b><span class="ab${Math.abs(gross)>2?' warn':''}">${zahl(gross)}</span>`;
   b.title=`Seite ${i}: längs ${a.laenge==null?'nicht ganz im Bild':zahl(a.laenge)}, quer ${zahl(a.flaeche)} gegen die eingetragenen Maße`}
  else{b.innerHTML=`<b>${i}</b><span class="ab">–</span>`;b.title=`Seite ${i}: keine Fotos`}
  b.setAttribute('aria-label',`Seite ${i} nach vorn`);b.onclick=()=>seiteNachVorn(i);
  const hell=an=>kk.querySelector(`.kf[data-s="${i}"]`)?.classList.toggle('hell',an);
  b.onpointerenter=b.onfocus=()=>hell(true);b.onpointerleave=b.onblur=()=>hell(false);box.append(b)}
 zeigen()}

async function laden(){
 try{const st=await json('/api/stand'),mit=st.balken.filter(b=>Object.values(b.seiten||{}).some(s=>Object.keys(s.fotos||{}).length));
  id=new URLSearchParams(location.search).get('id')||mit.at(-1)?.id;
  const b=st.balken.find(x=>x.id===id);if(!b)throw Error(id?`${id} gibt es nicht.`:'Noch kein Balken mit Fotos.');
  M=masse(b);$('#kid').textContent=b.name?`${id} ${b.name}`:id;$('#kmass').textContent=`${M.L} × ${b.breite_mm} × ${b.hoehe_mm} mm`;document.title=`Neurolign ${id}`;
  knoepfe(null);bauen();
  const K=await json('/api/koerper?id='+encodeURIComponent(id));
  // unplausible Seiten (schief, falsches Maß) nicht aufkleben, sondern rot markiert schraffieren
  for(const [n,s] of Object.entries(K.seiten)){if(s.grund)weg[n]=s.grund;else bilder[n]=`/koerper/${id}/S${n}.jpg?v=${K.stand}`}
  await Promise.all(Object.values(bilder).map(u=>new Promise(f=>{const i=new Image();i.onload=i.onerror=f;i.src=u})));
  knoepfe(K);bauen()}
 catch(e){$('#kfehler').textContent=e.message}
 finally{buehne.setAttribute('aria-busy','false')}}

let zug=null;
buehne.addEventListener('pointerdown',e=>{if(e.button)return;zug={x:e.clientX,y:e.clientY};buehne.setPointerCapture(e.pointerId);kk.classList.add('ziehen')});
buehne.addEventListener('pointermove',e=>{if(!zug)return;A.ry+=(e.clientX-zug.x)*.4;A.rx-=(e.clientY-zug.y)*.4;zug={x:e.clientX,y:e.clientY};zeigen()});
for(const t of['pointerup','pointercancel'])buehne.addEventListener(t,()=>{zug=null;kk.classList.remove('ziehen')});
buehne.addEventListener('wheel',e=>{e.preventDefault();A.zoom=Math.min(8,Math.max(.3,A.zoom*Math.exp(-e.deltaY*.0015)));zeigen()},{passive:false});
buehne.addEventListener('dblclick',()=>{A={...START};zeigen()});
buehne.addEventListener('keydown',e=>{const s={ArrowLeft:['ry',-15],ArrowRight:['ry',15],ArrowUp:['rx',15],ArrowDown:['rx',-15]}[e.key];
 if(s){A[s[0]]+=s[1]}else if(e.key==='+'||e.key==='='){A.zoom=Math.min(8,A.zoom*1.2)}else if(e.key==='-'){A.zoom=Math.max(.3,A.zoom/1.2)}
 else if(e.key==='0'||e.key==='Home'){A={...START}}else if(/^[1-4]$/.test(e.key)){return seiteNachVorn(+e.key)}else return;
 e.preventDefault();zeigen()});
// Zurück in die Galerie: kommt man von dort, wie Zurück im Browser (Lage in der Liste bleibt)
$('#kgalerie').onclick=e=>{try{if(new URL(document.referrer).pathname==='/galerie'&&new URL(document.referrer).host===location.host&&history.length>1){e.preventDefault();history.back()}}catch(x){}};
$('#kzurueck').onclick=()=>{A={...START};zeigen()};
addEventListener('resize',bauen);
laden();
