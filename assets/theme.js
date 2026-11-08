/* Blocking head script: restore the theme before styles and the first paint. */
(() => {
  'use strict';
  const key='heartopiaTheme',root=document.documentElement;
  let current='light';
  try{if(localStorage.getItem(key)==='midnight')current='midnight';}catch{/* Storage is optional. */}
  function apply(theme,persist=true){
    current=theme==='midnight'?'midnight':'light';
    root.dataset.theme=current;root.style.colorScheme=current==='midnight'?'dark':'light';
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content',current==='midnight'?'#101426':'#f5f1ff');
    document.querySelectorAll('[data-theme-choice]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.themeChoice===current)));
    if(persist)try{localStorage.setItem(key,current);}catch{/* Keep this session's choice. */}
  }
  apply(current,false);
  window.WeatherTheme={set:apply,get:()=>current};
  document.addEventListener('DOMContentLoaded',()=>{
    document.querySelectorAll('[data-theme-choice]').forEach(button=>button.addEventListener('click',()=>apply(button.dataset.themeChoice)));
    apply(current,false);
  },{once:true});
})();
