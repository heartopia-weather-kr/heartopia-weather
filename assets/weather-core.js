(function (root) {
  'use strict';
  const catalog = [
    ['Sunny','맑음',245,105,125,114], ['Clear','쾌청',470,105,160,114], ['Cloudy','흐림',728,120,165,90],
    ['Sunshower','여우비',244,300,155,120], ['Light Rain','약한 비',510,300,145,120], ['Moderate Rain','보통 비',775,300,145,120], ['Heavy Rain','강한 비',1050,300,150,120], ['Moon Rain','달빛 비',1320,300,155,120],
    ['Light Snow','약한 눈',250,498,145,108], ['Snow','보통 눈',515,498,145,108], ['Moderate Snow','보통 눈',515,498,145,108], ['Heavy Snow','강한 눈',785,498,145,108],
    ['Thunderstorm','뇌우',515,498,145,108], ['Fortune Cloud','행운 구름',237,685,175,96],
    ['Rainbow','무지개',237,685,175,96], ['Moon Rainbow','달 무지개',504,682,175,99], ['Meteor Shower 1','유성우 1',795,683,145,98], ['Meteor Shower 2','유성우 2',1055,681,155,100], ['Meteor Shower 3','유성우 3',1310,680,165,101],
    ['Aurora 1','오로라 1',248,845,150,103], ['Aurora 2','오로라 2',515,845,150,103], ['Aurora 3','오로라 3',780,845,155,103], ['Heatwave','폭염',1050,840,155,108], ['Petal Rain','꽃잎 비',1320,845,150,103]
  ];
  const byName = new Map(catalog.map(item => [item[0].toLowerCase(), item]));
  function entry(weather) {
    const key = weather.trim().toLowerCase();
    if (key==='moderate snow') return byName.get('snow');
    if (/^rainbow(?:\s+\d+)?$/.test(key)) return byName.get('rainbow');
    if (/^(meteor shower|aurora)$/.test(key)) return byName.get(key + ' 1');
    return byName.get(key);
  }
  function name(row) { if (/^meteor shower(?:\s+[123])?$/i.test(row.weather.trim())) return '유성우'; return entry(row.weather)?.[1] || row.name || row.weather; }
  function special(row) { return Boolean(row.special || /^(rainbow(?:\s+\d+)?|moon rainbow|meteor shower(?:\s+\d+)?|aurora(?:\s+\d+)?)$/i.test(row.weather.trim())); }
  function kst(now = new Date()) {
    const date = new Date(now.getTime() + 9 * 3600000), hour = date.getUTCHours();
    const gameDate = date;
    return { date: date.toISOString().slice(0,10), hour, minute: date.getUTCMinutes(), gameDate: gameDate.toISOString().slice(0,10) };
  }
  const validDate=value=>typeof value==='string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0,10)===value;
  function validateDays(days) {
    const object=value=>value!==null && typeof value==='object' && !Array.isArray(value);
    const text=value=>typeof value==='string' && value.trim().length>0;
    if (!Array.isArray(days) || !days.length || days.length > 9) throw new Error('예보 날짜 데이터가 올바르지 않습니다.');
    days.forEach((day,index) => {
      if (!object(day) || !validDate(day.startDate) || !Array.isArray(day.weather) || day.weather.length !== 24) throw new Error('24시간 예보가 완전하지 않습니다.');
      if (!text(day.status) || !text(day.dateLabel)) throw new Error('예보 표시 정보가 올바르지 않습니다.');
      if (index && Date.parse(day.startDate) - Date.parse(days[index-1].startDate) !== 86400000) throw new Error('예보 날짜가 연속적이지 않습니다.');
      day.weather.forEach((row,i) => { if (!object(row) || row.time !== String(i).padStart(2,'0')+':00' || !text(row.weather) || typeof row.changed !== 'boolean' || ('name' in row && !text(row.name)) || ('special' in row && typeof row.special!=='boolean')) throw new Error('시간별 예보 형식이 올바르지 않습니다.'); });
      if (!Number.isInteger(day.changes) || (day.changeRate!==null && !Number.isFinite(day.changeRate)) || day.changes !== day.weather.filter(row => row.changed).length || (day.changeRate!==null && day.changeRate !== Math.round(day.changes/24*1000)/10)) throw new Error('예보 요약이 일치하지 않습니다.');
    });
  }
  function validate(data) {
    validateDays(data?.days);
    if (typeof data.updated!=='string' || !/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(data.updated) || !validDate(data.updated.slice(0,10)) || !/^([01]\d|2[0-3]):[0-5]\d$/.test(data.updated.slice(11))) throw new Error('갱신 시각이 올바르지 않습니다.');
    return data;
  }
  function validateAnnualHeader(annual) {
    if (annual?.version!==1 || !validDate(annual.basisDate) || !annual.days || Array.isArray(annual.days) || typeof annual.days!=='object') throw new Error('연간 예보 형식이 올바르지 않습니다.');
  }
  function validateAnnual(annual) {
    validateAnnualHeader(annual);
    validateDays([{startDate:annual.basisDate,dateLabel:annual.basisDate,status:annual.unknownStatus,weather:annual.unknownWeather,changes:0,changeRate:null}]);
    if (annual.unknownWeather.some(row=>row.weather!=='Unknown' || row.name!=='?' || row.mark!=='?')) throw new Error('누락된 예보의 형식이 올바르지 않습니다.');
    for (const [key,day] of Object.entries(annual.days)){
      if (day?.startDate!==key) throw new Error('예보 날짜가 일치하지 않습니다.');
      validateDays([day]);
    }
    return annual;
  }
  function annualWindow(annual, date) {
    validateAnnualHeader(annual);
    if (!validDate(date)) throw new Error('예보 날짜가 일치하지 않습니다.');
    const start=Date.parse(date);
    const days=Array.from({length:9}, (_, index)=>{
      const key=new Date(start+index*86400000).toISOString().slice(0,10);
      const day=annual.days[key];
      if (day!==undefined) {
        if (day?.startDate!==key) throw new Error('예보 날짜가 일치하지 않습니다.');
        return day;
      }
      return {
        startDate:key, endDate:key, dateLabel:`${Number(key.slice(5,7))}월 ${Number(key.slice(8))}일`,
        timeRange:'00:00 ~ 23:00', changes:0, changeRate:null,
        status:annual.unknownStatus, weather:annual.unknownWeather
      };
    });
    validateDays(days);
    return {basisDate:annual.basisDate, days};
  }
  function calculate(day,start,end) {
    if (![start,end].every(hour => Number.isInteger(hour) && hour>=0 && hour<24)) throw new Error('시간을 선택해 주세요.');
    const a=start, b=end;
    if (b<=a) throw new Error('종료 시간은 시작 시간보다 늦어야 합니다.');
    const rows=day.weather.slice(a,b+1);
    if(rows.some(row=>row.weather==='Unknown')) throw new Error('선택 구간에 날씨 데이터가 없어 변경 횟수를 계산할 수 없습니다.');
    const changes=rows.slice(1).filter(row=>row.changed).length;
    return {rows,changes,rate:(changes/(b-a)*100).toFixed(1)};
  }
  root.WeatherCore={catalog,entry,name,special,kst,validate,validateAnnual,annualWindow,calculate};
})(typeof window==='undefined'?globalThis:window);
