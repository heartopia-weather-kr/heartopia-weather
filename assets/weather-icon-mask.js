/* Render-only alpha masks for the opaque source sheet; never recolor the artwork. */
(() => {
  'use strict';
  const masks=new Map();
  let sheet;
  function source(){
    if(!sheet)sheet=new Promise((resolve,reject)=>{
      const image=new Image();image.onload=()=>resolve(image);image.onerror=reject;
      image.src='design-reference/icons-light.png';
    });
    return sheet;
  }
  function mask(item){
    const key=item.slice(2).join(',');
    if(!masks.has(key))masks.set(key,source().then(image=>{
      const [x,y,width,height]=item.slice(2),canvas=document.createElement('canvas');
      canvas.width=width;canvas.height=height;
      const context=canvas.getContext('2d',{willReadFrequently:true});
      context.drawImage(image,x,y,width,height,0,0,width,height);
      const pixels=context.getImageData(0,0,width,height).data;
      const outside=new Uint8Array(width*height),queue=new Uint32Array(width*height);
      let head=0,tail=0;
      function visit(index){
        if(outside[index])return;
        const p=index*4,r=pixels[p],g=pixels[p+1],b=pixels[p+2];
        // Flood only near-white paper connected to the crop edge. Enclosed white
        // clouds, stars and highlights keep their original, fully opaque colors.
        if(Math.min(r,g,b)<235 || Math.max(r,g,b)-Math.min(r,g,b)>28)return;
        outside[index]=1;queue[tail++]=index;
      }
      for(let col=0;col<width;col++){visit(col);visit((height-1)*width+col);}
      for(let row=0;row<height;row++){visit(row*width);visit(row*width+width-1);}
      while(head<tail){
        const index=queue[head++],col=index%width,row=Math.floor(index/width);
        if(col)visit(index-1);if(col+1<width)visit(index+1);
        if(row)visit(index-width);if(row+1<height)visit(index+width);
      }
      const alpha=context.createImageData(width,height);
      for(let i=0;i<outside.length;i++){
        alpha.data[i*4]=alpha.data[i*4+1]=alpha.data[i*4+2]=255;
        alpha.data[i*4+3]=outside[i]?0:255;
      }
      context.putImageData(alpha,0,0);
      return canvas.toDataURL('image/png');
    }));
    return masks.get(key);
  }
  window.WeatherIconMask={mask};
})();
