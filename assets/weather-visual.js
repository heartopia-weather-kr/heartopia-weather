/* Display-only comparison. Never use this for change counts or calculator results. */
(function (root) {
  'use strict';
  function normalize(weather) {
    const value=weather.trim().toLowerCase();
    // Same special/variant comparison as weather.py, without forced six-hour changes.
    return /^rainbow(?:\s+\d+)?$/.test(value)?'rainbow':value;
  }
  function actualChange(days,gameDate,hour) {
    const day=days.find(item=>item.startDate===gameDate);
    if(!day || !Number.isInteger(hour) || hour<0 || hour>23)return false;
    const index=(hour+18)%24, row=day.weather[index];
    let previous=day.weather[index-1];
    if(index===0){
      const date=new Date(gameDate+'T00:00:00Z');date.setUTCDate(date.getUTCDate()-1);
      previous=days.find(item=>item.startDate===date.toISOString().slice(0,10))?.weather[23];
    }
    return Boolean(row && previous && normalize(row.weather)!==normalize(previous.weather));
  }
  function shareText(day) {
    if(!day || !/^\d{4}-\d{2}-\d{2}$/.test(day.startDate) || !Array.isArray(day.weather) || day.weather.length!==24) throw new Error('완전한 하루 예보가 필요합니다.');
    const date=new Date(day.startDate+'T12:00:00+09:00');
    if(Number.isNaN(date.getTime()))throw new Error('예보 날짜가 올바르지 않습니다.');
    const weekday=new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',weekday:'short'}).format(date);
    const heading=`📅 ${date.getUTCMonth()+1}월 ${date.getUTCDate()}일 (${weekday}) 두근두근타운 날씨`;
    const entries=[];
    day.weather.forEach((row,index)=>{
      const hour=(index+6)%24, time=String(hour).padStart(2,'0')+':00';
      if(!row || row.time!==time || typeof row.weather!=='string' || !row.weather.trim() || !root.WeatherCore.entry(row.weather))throw new Error('시간별 예보가 완전하지 않습니다.');
      const regular=hour%6===0;
      const changed=index>0 && normalize(row.weather)!==normalize(day.weather[index-1].weather);
      if(regular || changed){
        const label=root.WeatherCore.name(row);
        entries.push(`${hour<6?'다음 날 ':''}${time} ${label}${regular?' [정기]':''}`);
      }
    });
    return heading+'\n\n'+entries.join('\n');
  }
  root.WeatherVisual={normalize,actualChange,shareText};
})(typeof window==='undefined'?globalThis:window);
