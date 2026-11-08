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
  root.WeatherVisual={normalize,actualChange};
})(typeof window==='undefined'?globalThis:window);
