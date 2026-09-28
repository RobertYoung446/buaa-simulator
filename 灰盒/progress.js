(function(root){
  'use strict';
  const KEY='buaa-campus-progress-v1',PERIODS=['上午','下午','晚上'];
  const C=typeof module!=='undefined'?require('./course.js'):root.CampusCourse;
  function encode(state){return {version:2,day:state.day,period:state.period,scene:state.scene,player:{x:state.player.x,y:state.player.y},facing:state.facing,visited:[...state.visited],course:state.course||C.fresh(),savedAt:new Date().toISOString()};}
  function validate(data,world){
    if(!data||![1,2].includes(data.version)||!Number.isSafeInteger(data.day)||data.day<1||!Number.isInteger(data.period)||data.period<0||data.period>2||!world.scenes.some(s=>s.id===data.scene)||!data.player||!Number.isFinite(data.player.x)||!Number.isFinite(data.player.y)||!Array.isArray(data.visited)||!data.visited.every(id=>world.places.some(p=>p.id===id))||!['up','down','left','right'].includes(data.facing))throw Error('存档格式无效或版本不兼容');
    if(data.version===1){data.course=C.fresh();data.version=2;}C.validate(data.course,data.day);
    return data;
  }
  function load(storage,world){const raw=storage.getItem(KEY);return raw?validate(JSON.parse(raw),world):null;}
  function save(storage,state){const data=encode(state);storage.setItem(KEY,JSON.stringify(data));return data;}
  const api={KEY,PERIODS,encode,validate,load,save};if(typeof module!=='undefined')module.exports=api;else root.CampusProgress=api;
})(globalThis);
