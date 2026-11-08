(() => {
  const errors=[],svg=document.querySelector('#clock-orbit'),matrix=svg.getScreenCTM();
  const card=document.querySelector('.clock-card').getBoundingClientRect();
  const rings=[...svg.querySelectorAll('.change-ring')];
  const labels=[...document.querySelectorAll('#clock-hours>.clock-time')].map(n=>n.getBoundingClientRect());
  const actual=rings.map(ring=>{
    const point=svg.createSVGPoint();point.x=Number(ring.getAttribute('cx'));point.y=Number(ring.getAttribute('cy'));
    const center=point.matrixTransform(matrix),radius=Number(ring.getAttribute('r'))*matrix.a;
    const hour=ring.dataset.hour,icon=document.querySelector(`.clock-hour[data-hour="${hour}"] .clock-icon-wrap`).getBoundingClientRect();
    if(Math.abs(center.x-(icon.left+icon.width/2))>.2 || Math.abs(center.y-(icon.top+icon.height/2))>.2)errors.push('off-center '+hour);
    if(Math.abs(matrix.a-matrix.d)>.001)errors.push('ellipse '+hour);
    labels.forEach(label=>{
      const dx=center.x-Math.max(label.left,Math.min(center.x,label.right));
      const dy=center.y-Math.max(label.top,Math.min(center.y,label.bottom));
      if(Math.hypot(dx,dy)<radius+.25*matrix.a)errors.push('ring/label overlap '+hour);
    });
    return {center,radius};
  });
  actual.forEach((a,i)=>actual.slice(i+1).forEach(b=>{
    if(Math.hypot(a.center.x-b.center.x,a.center.y-b.center.y)<a.radius+b.radius+2)errors.push('ring overlap');
  }));
  [...document.querySelectorAll('#clock-hours .weather-icon,#clock-hours>.clock-time')].forEach(node=>{
    const rect=node.getBoundingClientRect();
    if(rect.left<card.left || rect.right>card.right || rect.top<card.top || rect.bottom>card.bottom)errors.push('card overflow');
  });
  const base=svg.querySelector('.orbit-base'),green=svg.querySelector('.orbit-shift');
  for(const attr of ['cx','cy','r','pathLength','transform'])if(base?.getAttribute(attr)!==green?.getAttribute(attr))errors.push('orbit mismatch '+attr);
  const border=document.querySelector('.clock-center').getBoundingClientRect();
  actual.forEach(({center,radius})=>{
    if(Math.hypot(center.x-(border.left+border.width/2),center.y-(border.top+border.height/2))<radius+border.width/2)errors.push('center circle overlap');
  });
  return errors;
})()
