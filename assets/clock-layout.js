/* One square coordinate system for CSS icon anchors and SVG clock decoration. */
(function(root){
  'use strict';
  const center=50,orbitRadius=39,ringRadius=8.8,labelRadius=52.5;
  function point(hour,radius=orbitRadius){
    const angle=(hour%12)*Math.PI/6;
    return {x:center+radius*Math.sin(angle),y:center-radius*Math.cos(angle)};
  }
  function sector(hour){
    const angle=(hour%12)*Math.PI/6,half=Math.PI/12,radius=60;
    const a={x:center+radius*Math.sin(angle-half),y:center-radius*Math.cos(angle-half)};
    const b={x:center+radius*Math.sin(angle+half),y:center-radius*Math.cos(angle+half)};
    return `M ${center} ${center} L ${a.x} ${a.y} A ${radius} ${radius} 0 0 1 ${b.x} ${b.y} Z`;
  }
  function labelPoint(hour,width,height,obstacles=[]){
    const angle=(hour%12)*Math.PI/6,sin=Math.sin(angle),cos=Math.cos(angle);
    const clearance=distance=>Math.hypot(Math.max(0,Math.abs(distance*sin)-width/2),Math.max(0,Math.abs(distance*cos)-height/2))-ringRadius-.225;
    // Halve normalized free space: at 130% desktop scale this is about 35%
    // less physical gap than before. Never shrink the full center distance,
    // which would put text inside the ring.
    const originalDistance=labelRadius-orbitRadius;
    const target=Math.max(.35,clearance(originalDistance)*.5);
    let low=ringRadius,high=originalDistance;
    for(let i=0;i<30;i++){const middle=(low+high)/2;if(clearance(middle)<target)low=middle;else high=middle;}
    let radius=orbitRadius+high;
    const blocked=radius=>{
      const p=point(hour,radius);
      return obstacles.some(box=>!(p.x+width/2+.2<=box.left || p.x-width/2-.2>=box.right || p.y+height/2+.2<=box.top || p.y-height/2-.2>=box.bottom));
    };
    // The same radial rule applies at every angle. Neighboring icon rectangles
    // impose a minimum gap on narrow screens; no per-hour pixel corrections.
    while(radius<labelRadius && blocked(radius))radius=Math.min(labelRadius,radius+.05);
    return point(hour,radius);
  }
  root.ClockLayout={center,orbitRadius,ringRadius,labelRadius,point,sector,labelPoint};
})(typeof window==='undefined'?globalThis:window);
