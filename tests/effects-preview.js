/* Development state lives only here: no localStorage and no real forecast fetch. */
window.previewControllers=[];
const grid=document.getElementById('preview-grid'),detail=document.getElementById('preview-detail');
let detailController=null,lastOpener=null,previewIconId=0;
function previewIcon(item){
  const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox',item.slice(2).join(' '));svg.setAttribute('class','weather-icon');svg.setAttribute('aria-hidden','true');
  const defs=document.createElementNS(ns,'defs'),clip=document.createElementNS(ns,'clipPath'),rect=document.createElementNS(ns,'rect'),id='preview-crop-'+(++previewIconId);clip.id=id;
  ['x','y','width','height'].forEach((key,i)=>rect.setAttribute(key,item[i+2]));clip.append(rect);defs.append(clip);svg.append(defs);
  const light=document.createElementNS(ns,'image');light.setAttribute('class','icon-art');light.setAttribute('href','../design-reference/icons-light.png');light.setAttribute('width','1536');light.setAttribute('height','1024');light.setAttribute('clip-path',`url(#${id})`);svg.append(light);
  const neon=document.createElementNS(ns,'image');neon.setAttribute('class','icon-midnight');neon.setAttribute('href','../assets/midnight-icons/'+MidnightIcons[item[0]]+'.png');['x','y','width','height'].forEach((key,i)=>neon.setAttribute(key,item[i+2]));svg.append(neon);return svg;
}
function openDetail(item,opener){
  if(detail.open)return;lastOpener=opener;
  document.getElementById('preview-detail-title').textContent=item[1]+' · 확대 미리보기';
  const weather=document.getElementById('preview-detail-weather');weather.replaceChildren();
  for(const [i,time] of ['17:00','18:00'].entries()){
    if(i){const arrow=document.createElement('span');arrow.className='hero-arrow';arrow.textContent='→';weather.append(arrow);}
    const box=document.createElement('div');box.className='hero-forecast';const pill=document.createElement('span');pill.className='time-pill';pill.textContent=time;
    const name=document.createElement('strong');name.textContent=item[1];box.append(pill,previewIcon(item),name);weather.append(box);
  }
  detailController=WeatherAtmosphere.create(document.getElementById('preview-detail-card'));detailController.update(item[0]);
  grid.dataset.suspended='true';detail.showModal();
}
WeatherCore.catalog.forEach(item=>{
  const card=document.createElement('section');card.className='card hero preview-hero';card.dataset.weather=item[0];card.tabIndex=0;card.setAttribute('role','button');card.setAttribute('aria-haspopup','dialog');card.setAttribute('aria-controls','preview-detail');card.setAttribute('aria-label',item[1]+' 확대 미리보기');
  const title=document.createElement('h2');title.className='preview-title';title.textContent=item[1];card.append(title);
  const caption=document.createElement('p');caption.className='preview-title';caption.textContent=item[0];card.append(caption);grid.append(card);
  const controller=WeatherAtmosphere.create(card);controller.update(item[0]);window.previewControllers.push(controller);
  card.addEventListener('click',()=>openDetail(item,card));card.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();openDetail(item,card);}});
});
document.querySelectorAll('[data-preview-theme]').forEach(button=>button.addEventListener('click',()=>{
  const midnight=document.documentElement.dataset.theme!=='midnight';document.documentElement.dataset.theme=midnight?'midnight':'light';
  document.querySelectorAll('[data-preview-theme]').forEach(node=>node.textContent=midnight?'Light 보기':'Midnight 보기');
}));
document.querySelectorAll('[data-preview-strength]').forEach(input=>input.addEventListener('input',()=>{
  const value=Number(input.value);document.documentElement.style.setProperty('--preview-strength',value/100);
  document.querySelectorAll('[data-preview-strength]').forEach(node=>node.value=value);
  document.querySelectorAll('[data-preview-strength-value]').forEach(node=>node.textContent=value+'%');
}));
document.getElementById('preview-detail-close').addEventListener('click',()=>detail.close());
detail.addEventListener('click',event=>{const box=detail.getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)detail.close();});
detail.addEventListener('close',()=>{detailController?.destroy();detailController=null;grid.dataset.suspended='false';lastOpener?.focus({preventScroll:true});});
