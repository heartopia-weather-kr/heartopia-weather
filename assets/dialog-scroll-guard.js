/* Prevent touch scroll chaining behind native modal dialogs on iOS.
   Keep the dialog itself scrollable and leave horizontal swipe gestures alone. */
(function(root){
  'use strict';
  function canScrollVertically(target,dialog,direction,getStyle){
    for(let node=target;node;node=node.parentElement){
      if(node.nodeType===1){
        const style=getStyle(node);
        const overflow=style.overflowY;
        if((node===dialog||overflow==='auto'||overflow==='scroll')&&node.scrollHeight>node.clientHeight+1){
          const max=node.scrollHeight-node.clientHeight;
          if(direction>0&&node.scrollTop>1)return true;
          if(direction<0&&node.scrollTop<max-1)return true;
        }
      }
      if(node===dialog)break;
    }
    return false;
  }
  function shouldBlockTouch(dialog,target,x,y,dx,dy,getStyle){
    if(!dialog)return false;
    const bounds=dialog.getBoundingClientRect();
    // Native <dialog> reports backdrop gestures with the dialog as target.
    if(x<bounds.left||x>bounds.right||y<bounds.top||y>bounds.bottom)return true;
    if(!dialog.contains(target))return true;
    // Grouped forecast uses horizontal touchend gestures; do not cancel them.
    if(Math.abs(dx)>Math.abs(dy))return false;
    if(Math.abs(dy)<0.5)return false;
    return !canScrollVertically(target,dialog,dy,getStyle);
  }
  function install(doc,win){
    let last=null;
    doc.addEventListener('touchstart',event=>{
      if(!doc.querySelector('dialog[open]')||event.touches.length!==1){last=null;return;}
      last={x:event.touches[0].clientX,y:event.touches[0].clientY};
    },{passive:true,capture:true});
    doc.addEventListener('touchmove',event=>{
      if(!last||event.touches.length!==1||!event.cancelable)return;
      const dialog=doc.querySelector('dialog[open]');
      if(!dialog){last=null;return;}
      const touch=event.touches[0],dx=touch.clientX-last.x,dy=touch.clientY-last.y;
      last={x:touch.clientX,y:touch.clientY};
      if(shouldBlockTouch(dialog,event.target,touch.clientX,touch.clientY,dx,dy,node=>win.getComputedStyle(node)))event.preventDefault();
    },{passive:false,capture:true});
    for(const type of ['touchend','touchcancel'])doc.addEventListener(type,()=>{last=null;},{passive:true,capture:true});
  }
  const api={canScrollVertically,shouldBlockTouch,install};
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.DialogScrollGuard=api;
})(typeof window!=='undefined'?window:globalThis);
