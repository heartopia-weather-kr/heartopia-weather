const assert=require('node:assert/strict');
const guard=require('../assets/dialog-scroll-guard.js');
const style=()=>({overflowY:'auto'});
function scenario(top,max=600){
  const dialog={nodeType:1,parentElement:null,scrollTop:top,clientHeight:400,scrollHeight:400+max,getBoundingClientRect:()=>({left:10,right:310,top:20,bottom:620})};
  dialog.contains=node=>node===dialog||node===child;
  const child={nodeType:1,parentElement:dialog,scrollTop:0,clientHeight:50,scrollHeight:50};
  return {dialog,child};
}
{
  const {dialog,child}=scenario(250);
  assert.equal(guard.shouldBlockTouch(dialog,child,100,200,0,-20,style),false,'scroll down within dialog');
  assert.equal(guard.shouldBlockTouch(dialog,child,100,200,0,20,style),false,'scroll up within dialog');
  assert.equal(guard.shouldBlockTouch(dialog,child,100,200,80,5,style),false,'grouped horizontal swipe');
  assert.equal(guard.shouldBlockTouch(dialog,dialog,100,700,0,20,style),true,'backdrop drag');
}
{
  const {dialog,child}=scenario(0);
  assert.equal(guard.shouldBlockTouch(dialog,child,100,200,0,20,style),true,'top edge must not scroll background');
  assert.equal(guard.shouldBlockTouch(dialog,child,100,200,0,-20,style),false,'top edge can scroll down');
}
{
  const {dialog,child}=scenario(600);
  assert.equal(guard.shouldBlockTouch(dialog,child,100,200,0,-20,style),true,'bottom edge must not scroll background');
  assert.equal(guard.shouldBlockTouch(dialog,child,100,200,0,20,style),false,'bottom edge can scroll up');
}
{
  const {dialog,child}=scenario(0,0);
  assert.equal(guard.shouldBlockTouch(dialog,child,100,200,0,-20,style),true,'short calculator dialog cannot drag background');
}
{
  const {dialog,child}=scenario(600);
  const nested={nodeType:1,parentElement:child,scrollTop:30,clientHeight:100,scrollHeight:200};
  dialog.contains=()=>true;
  assert.equal(guard.shouldBlockTouch(dialog,nested,100,200,0,-20,style),false,'nested scrollable content still scrolls');
}
assert.equal(guard.shouldBlockTouch(null,null,100,200,0,-20,style),false,'no modal leaves page scroll enabled');
console.log('PASS: modal scroll chain blocked at edges, internal vertical and grouped horizontal gestures preserved');
