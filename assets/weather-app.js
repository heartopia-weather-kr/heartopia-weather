/* Static dashboard: no generated forecast data is written by this application. */
(() => {
  'use strict';
  const C=window.WeatherCore, $=id=>document.getElementById(id);
  const readSetting=(key,fallback)=>{try{return localStorage.getItem(key)||fallback;}catch{return fallback;}};
  const saveSetting=(key,value)=>{try{localStorage.setItem(key,value);}catch{/* Browsing without storage remains usable. */}};
  const state={data:null,day:0,clockMode:C.kst().hour<12?'am':'pm',clockPeriod:C.kst().hour<12?'am':'pm',notice:null,loading:false,forecastMode:'full',forecastPeriod:0};
  const atmosphere=window.WeatherAtmosphere.create(document.querySelector('.hero'));
  const periodLabels=['오전 · 06:00 ~ 11:00','오후 · 12:00 ~ 17:00','저녁 · 18:00 ~ 23:00','새벽 · 다음 날 00:00 ~ 05:00'];
  function el(tag,className,text){const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;}
  let iconId=0;
  function icon(row,transparent=false){
    const item=C.entry(row.weather);
    if(!item)return el('span','unknown-icon','?');
    // Viewports use the original sheet; no generated or redesigned replacements.
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('viewBox',item.slice(2).join(' '));svg.setAttribute('class','weather-icon');svg.setAttribute('aria-hidden','true');svg.setAttribute('draggable','false');
    const clip=document.createElementNS(svg.namespaceURI,'clipPath'),rect=document.createElementNS(svg.namespaceURI,'rect'),id='weather-crop-'+(++iconId);clip.id=id;
    ['x','y','width','height'].forEach((key,i)=>rect.setAttribute(key,item[i+2]));clip.append(rect);
    const defs=document.createElementNS(svg.namespaceURI,'defs');defs.append(clip);svg.append(defs);
    const image=document.createElementNS(svg.namespaceURI,'image');image.setAttribute('class','icon-art');image.setAttribute('href','design-reference/icons-light.png');image.setAttribute('width','1536');image.setAttribute('height','1024');image.setAttribute('clip-path',`url(#${id})`);image.setAttribute('draggable','false');svg.append(image);
    const neon=document.createElementNS(svg.namespaceURI,'image');neon.setAttribute('class','icon-midnight');neon.setAttribute('href','assets/midnight-icons/'+window.MidnightIcons[item[0]]+'.png');neon.setAttribute('draggable','false');
    ['x','y','width','height'].forEach((key,i)=>neon.setAttribute(key,item[i+2]));svg.append(neon);svg.dataset.weatherKey=item[0];
    window.WeatherIconMask.mask(item).then(url=>{
      const mask=document.createElementNS(svg.namespaceURI,'mask'),alpha=document.createElementNS(svg.namespaceURI,'image');mask.id=id+'-alpha';mask.setAttribute('maskUnits','userSpaceOnUse');mask.setAttribute('maskContentUnits','userSpaceOnUse');
      ['x','y','width','height'].forEach((key,i)=>{mask.setAttribute(key,item[i+2]);alpha.setAttribute(key,item[i+2]);});alpha.setAttribute('href',url);mask.append(alpha);defs.append(mask);image.style.setProperty('--weather-alpha-mask',`url(#${mask.id})`);if(transparent)image.setAttribute('mask',`url(#${mask.id})`);svg.classList.add('alpha-ready');
    }).catch(()=>{/* Keep the source icon, without a rectangular fallback glow. */});
    return svg;
  }
  function rowCard(row,first=false){const node=el('div','weather-row'+(C.special(row)?' special':''));const mark=el('span','change-mark '+(first?'mark-start':row.changed?'mark-changed':'mark-unchanged'),first?'시작':row.changed?'◯':'−');mark.setAttribute('aria-label',first?'시작 날씨':row.changed?'날씨 변경':'날씨 유지');node.append(mark,el('strong','row-time',row.time),icon(row),el('span','row-name',C.name(row)));if(C.special(row))node.append(el('span','special-star','✧'));return node;}
  function dateLabel(date){return new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',month:'2-digit',day:'2-digit',weekday:'short'}).format(new Date(date+'T12:00:00+09:00'));}
  function currentDay(){return state.data?.days.find(day=>day.startDate===C.kst().gameDate);}
  function updateTodayDate(){
    const date=C.kst().gameDate, weekday=new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',weekday:'short'}).format(new Date(date+'T12:00:00+09:00'));
    $('today-date').dateTime=date;
    $('today-date').textContent=`${Number(date.slice(5,7))}월 ${Number(date.slice(8,10))}일 (${weekday})`;
  }
  function freshness(){
    if(!state.data)return;
    $('status').textContent=`마지막 업데이트: ${state.data.updated} (KST)`;
  }
  function renderToday(){
    updateTodayDate();
    const day=currentDay(), container=$('current-weather');container.replaceChildren();
    if(!day){atmosphere.update(null);container.append(el('p','empty','현재 날짜의 예보가 없어요. 아래에서 저장된 날짜를 확인해 주세요.'));$('today-changes').textContent='—';return;}
    $('today-changes').textContent=day.changes+'회';
    const index=(C.kst().hour+18)%24, now=day.weather[index];
    atmosphere.update(now.weather);
    const next=index<23?day.weather[index+1]:state.data.days.find(item=>item.startDate===C.kst(new Date(Date.now()+86400000)).gameDate)?.weather[0];
    function forecast(row,label){const box=el('div','hero-forecast');box.append(el('span','time-pill',label),icon(row),el('strong','',C.name(row)));return box;}
    container.append(forecast(now,now.time));
    const transition=el('div','hero-transition');transition.append(el('span','hero-arrow','→'));
    const change=el('span','current-change'+(next?(next.changed?' is-changed':' is-unchanged'):''),next?(next.changed?'⭕ 변경':'❌ 유지'):'다음 예보 없음');change.id='current-change';transition.append(change);container.append(transition);
    if(next)container.append(forecast(next,next.time));
  }
  let copyResetTimer;
  async function copyWeather(){
    const button=$('weather-copy'),label=$('weather-copy-text');
    clearTimeout(copyResetTimer);
    try{
      const day=currentDay();
      if(!day)throw new Error('현재 게임 날짜의 예보가 없습니다.');
      const content=window.WeatherVisual.shareText(day);
      if(navigator.clipboard && typeof navigator.clipboard.writeText==='function'){
        await navigator.clipboard.writeText(content);
      }else{
        const field=document.createElement('textarea');
        field.value=content;field.readOnly=true;field.setAttribute('aria-hidden','true');
        field.style.cssText='position:fixed;left:-9999px;top:0;opacity:0';
        document.body.append(field);field.focus();field.select();
        let copied=false;
        try{copied=document.execCommand('copy');}finally{field.remove();}
        if(!copied)throw new Error('클립보드 복사 실패');
      }
      label.textContent='복사 완료 ✓';
    }catch(error){
      label.textContent='복사 실패';
      console.warn('날씨 공유 복사 실패:',error);
    }
    copyResetTimer=setTimeout(()=>{label.textContent='복사';},2000);
  }
  $('weather-copy').addEventListener('click',copyWeather);
  function renderWeek(){
    $('week-days').replaceChildren();
    let shown=0;
    state.data.days.forEach((day,index)=>{
      if(day.startDate<=C.kst().gameDate||shown>=7)return;
      shown++;
      const representative=day.weather.find(C.special)||day.weather[0];
      const button=el('button','day-card'+(day.weather.some(C.special)?' special':'')+(day.startDate===C.kst().gameDate?' selected':''));button.type='button';button.setAttribute('aria-haspopup','dialog');button.setAttribute('aria-controls','forecast-dialog');button.setAttribute('aria-label',dateLabel(day.startDate)+' 상세 예보 보기');
      button.append(el('strong','day-date',dateLabel(day.startDate)),icon(representative),el('strong','day-weather',C.name(representative)));
      button.title='특수 날씨가 있으면 우선 표시 · 없으면 06시 예보';button.addEventListener('click',()=>{selectDay(index);openModal('forecast-dialog',button);});$('week-days').append(button);
    });
  }
  function selectDay(index){if(!state.data||index<0||index>=state.data.days.length||state.data.days[index].startDate<=C.kst().gameDate)return;state.day=index;renderSelected();}
  function renderSelected(){
    const day=state.data.days[state.day];$('selected-date').textContent=dateLabel(day.startDate);$('prev-date').disabled=state.day===0;$('next-date').disabled=state.day===state.data.days.length-1;
    // Preserve weather.py's <=25 / <=50 / <=75 / >75 thresholds.
    // Both upper levels share the requested green presentation.
    const badge=$('day-summary');badge.className='summary-badge '+(day.changeRate<=25?'level-low':day.changeRate<=50?'level-normal':'level-high');
    const count=el('span'),rate=el('span');count.append('● 변경 ',el('strong','',day.changes+'회'));rate.append('변동률 ',el('strong','',day.changeRate+'%'));
    badge.replaceChildren(count,el('span','badge-divider','|'),rate,el('span','badge-divider','|'),el('span','badge-level',day.status.replace(/^[^가-힣]+/,'')));
    renderPeriods();
  }
  function setForecastMode(mode){
    if(mode!=='full'&&mode!=='grouped')return;
    state.forecastMode=mode;
    renderPeriods();
  }
  function setForecastPeriod(index){
    if(index<0||index>3||state.forecastMode!=='grouped')return;
    state.forecastPeriod=index;
    renderPeriods();
  }
  function renderPeriods(){
    const day=state.data.days[state.day], container=$('periods'),grouped=state.forecastMode==='grouped';
    $('view-full').setAttribute('aria-pressed',String(!grouped));
    $('view-grouped').setAttribute('aria-pressed',String(grouped));
    $('group-navigation').hidden=!grouped;
    $('group-dots').hidden=!grouped;
    container.classList.toggle('grouped-periods',grouped);
    container.replaceChildren();
    const indices=grouped?[state.forecastPeriod]:[0,1,2,3];
    for(const i of indices){
      const rows=day.weather.slice(i*6,i*6+6), section=el('section','period');
      const header=el('div','period-heading');header.append(el('h3','',periodLabels[i]),el('span','period-count',`변경 ${rows.filter(row=>row.changed).length}회`));section.append(header);rows.forEach(row=>section.append(rowCard(row)));container.append(section);
    }
    if(grouped){
      const i=state.forecastPeriod;
      $('group-title').textContent=['오전','오후','저녁','새벽'][i];
      $('group-range').textContent=periodLabels[i].split(' · ')[1];
      $('group-prev').disabled=i===0;
      $('group-next').disabled=i===3;
      const dots=$('group-dots');dots.replaceChildren();
      for(let j=0;j<4;j++){
        const dot=el('button','group-dot'+(j===i?' active':''));dot.type='button';
        dot.setAttribute('aria-label',`${['오전','오후','저녁','새벽'][j]} 시간대 보기`);
        dot.setAttribute('aria-pressed',String(j===i));
        dot.addEventListener('click',()=>setForecastPeriod(j));
        dots.append(dot);
      }
    }
  }
  // Calendar hours 00-05 belong to the previous game day; 06-11 to the new one.
  // Keep the actual hourly forecast unchanged when the 06:00 game-date label rolls over.
  function clockForecast(hour,now,gameDay){
    const date=now.date,gameDate=now.gameDate;
    const previous=state.data.days.find(d=>d.endDate===date&&d.startDate!==date);
    const today=state.data.days.find(d=>d.startDate===date);
    const active=state.data.days.find(d=>d.startDate===gameDate);
    const source=hour<6?(previous||active):(today||active);
    const row=source?.weather[(hour+18)%24];
    return {row,source};
  }
  function renderClock(){
    const now=C.kst(),day=currentDay(),center=$('clock-center');
    if(!day){$('clock-hours').replaceChildren();$('clock-orbit').replaceChildren();center.textContent='현재 날짜의 예보가 없어요.';return;}
    $('clock-am').setAttribute('aria-pressed',String(state.clockMode==='am'));$('clock-pm').setAttribute('aria-pressed',String(state.clockMode==='pm'));
    $('clock-hours').replaceChildren();
    const layout=window.ClockLayout,overlay=$('clock-orbit');overlay.replaceChildren();
    const makeSvg=(tag,attrs)=>{const node=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([key,value])=>node.setAttribute(key,String(value)));return node;};
    const orbitAttrs={cx:layout.center,cy:layout.center,r:layout.orbitRadius,pathLength:360,transform:'rotate(-90 50 50)'};
    // Game-date ring is inside the existing change-effect orbit; each half represents six hours.
    const circle=(r,stroke,width,extra={})=>makeSvg('circle',{cx:50,cy:50,r,fill:'none',stroke,'stroke-width':width,...extra});
    const midnightSplit=state.clockMode==='am'&&now.hour<6;
    const colorOld='var(--clock-previous-day)',colorNew='var(--clock-current-day)';
    const ringRadius=29.4;
    const ring=circle(ringRadius,midnightSplit?colorOld:colorNew,2.7,{opacity:'.83'});
    overlay.append(ring);
    if(midnightSplit){
      // Left half: hours 06-11; right half: hours 00-05.
      overlay.append(makeSvg('path',{d:'M 50 20.6 A 29.4 29.4 0 0 0 50 79.4',fill:'none',stroke:colorNew,'stroke-width':2.7,opacity:'.95'}));
    }
    overlay.append(makeSvg('circle',{...orbitAttrs,class:'orbit-base'}));
    const defs=makeSvg('defs',{}),clip=makeSvg('clipPath',{id:'clock-change-sectors',clipPathUnits:'userSpaceOnUse'});defs.append(clip);overlay.append(defs);
    const highlighted=makeSvg('g',{'clip-path':'url(#clock-change-sectors)'});highlighted.append(makeSvg('circle',{...orbitAttrs,class:'orbit-shift'}));overlay.append(highlighted);
    const start=state.clockMode==='am'?0:12;
    for(let i=0;i<12;i++){
      const hour=start+i,{row,source}=clockForecast(hour,now,day);
      if(!row)continue;
      const point=layout.point(hour),labelPoint=layout.point(hour,layout.labelRadius);
      const changed=window.WeatherVisual.actualChange(state.data.days,source.startDate,hour);
      const slot=el('div','clock-hour');slot.style.left=point.x+'%';slot.style.top=point.y+'%';slot.dataset.hour=String(hour);slot.setAttribute('role','img');
      slot.setAttribute('aria-label',`${source.startDate} 게임 날짜 · ${hour<6?'다음 날 ':''}${row.time} ${C.name(row)}${changed?' · 실제 날씨 변경':''}`);
      const wrap=el('span','clock-icon-wrap'+(changed?' weather-shift':''));wrap.append(icon(row,true));slot.append(wrap);$('clock-hours').append(slot);
      const label=el('span','clock-time',hour===0?'00':String(hour%12||12));label.style.left=labelPoint.x+'%';label.style.top=labelPoint.y+'%';label.dataset.hour=String(hour);label.setAttribute('aria-hidden','true');$('clock-hours').append(label);
      if(changed){
        overlay.append(makeSvg('circle',{class:'change-ring',cx:point.x,cy:point.y,r:layout.ringRadius,'data-hour':hour}));
        clip.append(makeSvg('path',{d:layout.sector(hour),'data-hour':hour}));
      }
    }
    // Thin time-progress arc follows the selected 12-hour face; no clock hand.
    const elapsed=(now.hour%12+now.minute/60)/12;
    const progress=circle(25.6,'#67e8f9',1.1,{opacity:'.92','stroke-linecap':'round','stroke-dasharray':`${elapsed*160.85} 160.85`,transform:'rotate(-90 50 50)'});
    const activePeriod=(now.hour<12?'am':'pm')===state.clockMode;
    if(activePeriod){
      overlay.append(progress);

    }
    const current=clockForecast(now.hour,now,day).row||day.weather[(now.hour+18)%24];
    center.replaceChildren();center.append(icon(current),el('strong','',C.name(current)),el('strong','center-time',String(now.hour).padStart(2,'0')+':'+String(now.minute).padStart(2,'0')));
    positionClockLabels();
  }
  function positionClockLabels(){
    const rect=$('weather-clock').getBoundingClientRect();if(!rect.width)return;
    const toUnits=value=>value/rect.width*100;
    const obstacles=[...$('clock-hours').querySelectorAll('.weather-icon')].map(icon=>{
      const box=icon.getBoundingClientRect();return {left:toUnits(box.left-rect.left),right:toUnits(box.right-rect.left),top:toUnits(box.top-rect.top),bottom:toUnits(box.bottom-rect.top)};
    });
    $('clock-hours').querySelectorAll('.clock-time').forEach(label=>{
      const box=label.getBoundingClientRect(),point=window.ClockLayout.labelPoint(Number(label.dataset.hour),toUnits(box.width),toUnits(box.height),obstacles);
      label.style.left=point.x+'%';label.style.top=point.y+'%';
    });
  }
  if(window.ResizeObserver)new ResizeObserver(positionClockLabels).observe($('weather-clock'));
  else window.addEventListener('resize',positionClockLabels,{passive:true});
  const modalOpeners=new Map();
  function openModal(id,opener){
    if(document.querySelector('dialog[open]'))return;
    modalOpeners.set(id,opener);$(id).showModal();
  }
  function setupModal(id,closeId){
    const dialog=$(id);
    $(closeId).addEventListener('click',()=>dialog.close());
    dialog.addEventListener('click',event=>{const box=dialog.getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)dialog.close();});
    dialog.addEventListener('close',()=>{const opener=modalOpeners.get(id);if(opener?.isConnected)opener.focus({preventScroll:true});modalOpeners.delete(id);});
  }
  function populateCalculator(){
    const selected=$('calculator-date').selectedOptions[0]?.textContent;
    $('calculator-date').replaceChildren();state.data.days.forEach((day,i)=>{const option=el('option','',day.dateLabel);option.value=i;$('calculator-date').append(option);});
    const index=state.data.days.findIndex(day=>selected?day.dateLabel===selected:day.startDate===C.kst().gameDate);$('calculator-date').value=Math.max(0,index);$('calculator-run').disabled=false;
  }
  async function loadWeather(){
    if(state.loading)return;state.loading=true;
    try{
      const response=await fetch('weather.json?t='+Date.now(),{cache:'no-store'});if(!response.ok)throw new Error('예보 파일을 불러오지 못했습니다.');
      const data=C.validate(await response.json()), previous=state.data?.days[state.day]?.startDate;
      state.data=data;state.day=Math.max(0,data.days.findIndex(day=>day.startDate===previous&&day.startDate>C.kst().gameDate));if(state.day===0)state.day=Math.max(0,data.days.findIndex(day=>day.startDate>C.kst().gameDate));
      populateCalculator();renderToday();renderWeek();renderSelected();renderClock();freshness();$('load-error').hidden=true;
    }catch(error){
      $('load-error').hidden=false;$('load-error').textContent=error.message+(state.data?' 마지막으로 불러온 예보를 표시합니다.':' 예보는 자동으로 다시 불러옵니다.');
      if(!state.data){$('current-weather').replaceChildren(el('p','empty','날씨 정보를 불러오지 못했어요.'));$('week-days').replaceChildren(el('p','empty','7일 예보를 불러오지 못했어요.'));}
    }finally{state.loading=false;}
  }
  function noticeKey(){return `${state.notice?.id||'default'}-${C.kst().date}`;}
  function showNotice(){if(!state.notice?.enabled)return;const notice=state.notice;$('notice-title').textContent=(notice.icon||'')+' '+(notice.title||'이용 안내');$('notice-message').replaceChildren();const lines=Array.isArray(notice.message)?notice.message:[notice.message||''];lines.forEach(line=>$('notice-message').append(el('p','',String(line))));if(!$('notice-dialog').open)$('notice-dialog').showModal();}
  async function loadNotice(){try{const response=await fetch('notice.json?t='+Date.now(),{cache:'no-store'});if(!response.ok)throw new Error('공지 로딩 실패');state.notice=await response.json();$('notice-open').hidden=!state.notice.enabled;if(readSetting('noticeHiddenKey','')!==noticeKey())showNotice();}catch{$('notice-open').textContent='공지 다시 불러오기';}}
  setupModal('forecast-dialog','forecast-close');
  $('view-full').addEventListener('click',()=>setForecastMode('full'));
  $('view-grouped').addEventListener('click',()=>setForecastMode('grouped'));
  $('group-prev').addEventListener('click',()=>setForecastPeriod(state.forecastPeriod-1));
  $('group-next').addEventListener('click',()=>setForecastPeriod(state.forecastPeriod+1));
  // Recognize horizontal swipes on the six-hour content only; preserve vertical scrolling.
  const groupArea=$('periods');let gesture=null;
  groupArea.addEventListener('touchstart',event=>{
    if(state.forecastMode!=='grouped'||event.touches.length!==1){gesture=null;return;}
    gesture={x:event.touches[0].clientX,y:event.touches[0].clientY};
  },{passive:true});
  groupArea.addEventListener('touchend',event=>{
    if(!gesture||state.forecastMode!=='grouped')return;
    const dx=event.changedTouches[0].clientX-gesture.x,dy=event.changedTouches[0].clientY-gesture.y;
    gesture=null;
    if(Math.abs(dx)>55&&Math.abs(dx)>Math.abs(dy)*1.5)setForecastPeriod(state.forecastPeriod+(dx<0?1:-1));
  },{passive:true});
  groupArea.addEventListener('touchcancel',()=>{gesture=null;},{passive:true});
  setupModal('calculator-dialog','calculator-close');
  $('prev-date').addEventListener('click',()=>selectDay(state.day-1));$('next-date').addEventListener('click',()=>selectDay(state.day+1));
  ['am','pm'].forEach(mode=>$('clock-'+mode).addEventListener('click',()=>{state.clockMode=mode;renderClock();}));
  function swipe(node,callback){let x=0,y=0;node.addEventListener('touchstart',event=>{x=event.changedTouches[0].clientX;y=event.changedTouches[0].clientY;},{passive:true});node.addEventListener('touchend',event=>{const dx=event.changedTouches[0].clientX-x,dy=event.changedTouches[0].clientY-y;if(Math.abs(dx)>45&&Math.abs(dx)>Math.abs(dy)*1.4)callback(dx<0?1:-1);},{passive:true});}
  swipe(document.querySelector('.date-navigation'),direction=>selectDay(state.day+direction));
  $('calculator-toggle').addEventListener('click',()=>openModal('calculator-dialog',$('calculator-toggle')));
  for(let hour=0;hour<24;hour++){['start','end'].forEach(type=>{const option=el('option','',String(hour).padStart(2,'0')+':00'+(hour<6?' (다음 날)':''));option.value=hour;$('calculator-'+type).append(option);});}$('calculator-start').value=19;$('calculator-end').value=21;
  ['calculator-date','calculator-start','calculator-end'].forEach(id=>$(id).addEventListener('change',()=>$('calculator-result').replaceChildren()));
  $('calculator-form').addEventListener('submit',event=>{event.preventDefault();const result=$('calculator-result');result.replaceChildren();try{if(!state.data)throw new Error('예보를 먼저 불러와 주세요.');const day=state.data.days[Number($('calculator-date').value)], calculation=C.calculate(day,Number($('calculator-start').value),Number($('calculator-end').value));result.append(el('h3','',day.dateLabel),el('div','result-summary',`변경 ${calculation.changes}회 · 변동률 ${calculation.rate}%`));const details=el('details'),summary=el('summary','','시간별 날씨 흐름 펼쳐보기');details.append(summary);calculation.rows.forEach((row,i)=>details.append(rowCard(row,i===0)));result.append(details);}catch(error){result.append(el('p','form-error',error.message));}});
  $('notice-close').addEventListener('click',()=>$('notice-dialog').close());$('notice-hide').addEventListener('click',()=>{saveSetting('noticeHiddenKey',noticeKey());$('notice-dialog').close();});$('notice-open').addEventListener('click',()=>state.notice?showNotice():loadNotice());
  $('notice-dialog').addEventListener('click',event=>{const box=$('notice-dialog').getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)$('notice-dialog').close();});
  // The 06:00 KST game-day rollover is a local display change, not a network update.
  // The already downloaded eight-day forecast is sufficient for the new day.
  let lastGameDate=C.kst().gameDate;
  function refreshGameDay(){
    const gameDate=C.kst().gameDate;
    if(gameDate===lastGameDate)return;
    lastGameDate=gameDate;
    if(!state.data){updateTodayDate();return;}
    // The previous selected day may have become "today"; move to the first future day.
    const selected=state.data.days[state.day];
    if(!selected||selected.startDate<=gameDate){
      const next=state.data.days.findIndex(day=>day.startDate>gameDate);
      state.day=next>=0?next:state.data.days.length-1;
    }
    populateCalculator();
    renderToday();
    renderWeek();
    if(state.data.days[state.day]?.startDate>gameDate)renderSelected();
    else if($('forecast-dialog').open)$('forecast-dialog').close();
    renderClock();
    freshness();
  }
  function scheduleGameDayRollover(){
    const now=C.kst(),six=Date.parse(now.date+'T06:00:00+09:00');
    const next=six<=Date.now()?six+86400000:six;
    setTimeout(()=>{refreshGameDay();scheduleGameDayRollover();},Math.max(50,next-Date.now()+100));
  }
  scheduleGameDayRollover();
  // Also detect clock changes or background-tab timer throttling on the regular tick.
  setInterval(()=>{refreshGameDay();updateTodayDate();if(!state.data)return;freshness();renderToday();const period=C.kst().hour<12?'am':'pm';if(period!==state.clockPeriod){state.clockPeriod=period;state.clockMode=period;}renderClock();},60000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshGameDay();});
  setInterval(loadWeather,15*60000);
  updateTodayDate();loadWeather();loadNotice();
})();
