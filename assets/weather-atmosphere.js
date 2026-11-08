/* Decorative only: exact WeatherCore keys, no forecast or calculation changes. */
(() => {
  'use strict';
  const effects=Object.freeze({
    'Sunny':{id:'sunny',family:'warm',count:0,duration:28},
    'Clear':{id:'clear',family:'sunshine',count:3,duration:14},
    'Cloudy':{id:'cloudy',family:'cloud',count:2,duration:32},
    'Sunshower':{id:'sunshower',family:'rain',count:7,duration:3.8},
    'Light Rain':{id:'light-rain',family:'rain',count:10,duration:3.6},
    'Moderate Rain':{id:'moderate-rain',family:'rain',count:18,duration:2.9},
    'Heavy Rain':{id:'heavy-rain',family:'rain',count:26,duration:2.2},
    'Moon Rain':{id:'moon-rain',family:'rain',count:10,duration:4},
    'Light Snow':{id:'light-snow',family:'snow',count:8,duration:14},
    'Snow':{id:'snow',family:'snow',count:14,duration:12},
    'Heavy Snow':{id:'heavy-snow',family:'snow',count:22,duration:10},
    'Rainbow':{id:'rainbow',family:'rainbow',count:0,duration:26},
    'Moon Rainbow':{id:'moon-rainbow',family:'rainbow',count:0,duration:30},
    'Meteor Shower 1':{id:'meteor-1',family:'meteor',count:1,duration:22},
    'Meteor Shower 2':{id:'meteor-2',family:'meteor',count:2,duration:20},
    'Meteor Shower 3':{id:'meteor-3',family:'meteor',count:3,duration:18},
    'Aurora 1':{id:'aurora-1',family:'aurora',count:1,duration:28},
    'Aurora 2':{id:'aurora-2',family:'aurora',count:2,duration:25},
    'Aurora 3':{id:'aurora-3',family:'aurora',count:3,duration:22},
    'Heatwave':{id:'heatwave',family:'heat',count:0,duration:24},
    'Petal Rain':{id:'petal-rain',family:'petal',count:10,duration:15}
  });
  function select(weather){const key=typeof weather==='string'?window.WeatherCore.entry(weather)?.[0]:null;return effects[key]||null;}
  function create(host){
    const root=document.createElement('div');root.className='hero-atmosphere';root.setAttribute('aria-hidden','true');host.prepend(root);
    const motion=matchMedia('(prefers-reduced-motion: reduce)');
    let currentId=null,lastWeather=null,visible=true,destroyed=false;
    function pause(){root.dataset.paused=String(!visible || document.hidden || motion.matches);}
    const observer=window.IntersectionObserver?new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;pause();}):null;
    observer?.observe(host);
    function make(effect){
      const plane=document.createElement('div');plane.className='atmosphere-plane';plane.dataset.effect=effect.id;plane.dataset.family=effect.family;
      plane.style.setProperty('--effect-duration',effect.duration+'s');
      const haze=document.createElement('i');haze.className='atmosphere-haze';plane.append(haze);
      for(let i=0;i<effect.count;i++){
        const particle=document.createElement('i');particle.className='atmosphere-particle';
        particle.style.setProperty('--x',((i*61.803+13)%100).toFixed(2)+'%');
        particle.style.setProperty('--y',((i*37+9)%64)+'%');
        particle.style.setProperty('--delay',(-effect.duration*(i+.31)/Math.max(1,effect.count)).toFixed(2)+'s');
        particle.style.setProperty('--speed',(effect.duration*(.88+(i%4)*.08)).toFixed(2)+'s');
        particle.style.setProperty('--drift',(12+(i%5)*5)+'px');
        particle.style.setProperty('--index',i);plane.append(particle);
      }
      return plane;
    }
    function update(weather,force=false){
      if(destroyed)return;
      lastWeather=weather;const effect=select(weather),id=effect?.id||null;
      if(!force && id===currentId)return;
      currentId=id;root.dataset.effect=id||'none';
      if(motion.matches){root.replaceChildren();return;}
      // At most one fading old layer plus the new layer, even on rapid updates.
      root.querySelectorAll('.is-leaving').forEach(node=>node.remove());
      const previous=root.firstElementChild;
      if(previous){
        if(root.dataset.paused==='true')previous.remove();
        else{
          previous.classList.add('is-leaving');
          previous.addEventListener('animationend',event=>{if(event.target===previous && event.animationName==='atmosphere-exit')previous.remove();});
        }
      }
      if(effect)root.append(make(effect));
    }
    function motionChanged(){pause();update(lastWeather,true);}
    motion.addEventListener('change',motionChanged);
    document.addEventListener('visibilitychange',pause);pause();
    return {update,destroy(){if(destroyed)return;destroyed=true;observer?.disconnect();motion.removeEventListener('change',motionChanged);document.removeEventListener('visibilitychange',pause);root.remove();}};
  }
  window.WeatherAtmosphere={effects,select,create};
})();
