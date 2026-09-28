(function(root){
  'use strict';
  const fresh=()=>({status:'not_started',caught:[],startedDay:null,completedDay:null});
  function targets(world,engine,scenes){
    const layout=[['living',300,605],['living',630,805],['living',880,950],['living',490,1210],['library',320,320],['library',890,180],['library',1440,450],['museum',1000,660],['museum',1450,1200],['museum',1990,920]];
    return layout.map(([scene,x,y],i)=>({id:'student-'+(i+1),name:'逃课同学 '+(i+1),scene,...engine.safeNear(world,scenes[scene],x,y)}));
  }
  function validate(c,day){
    if(!c||!['not_started','active','complete'].includes(c.status)||!Array.isArray(c.caught)||new Set(c.caught).size!==c.caught.length||c.caught.some(id=>!/^student-([1-9]|10)$/.test(id)))throw Error('任务存档无效');
    if(c.status==='not_started'){if(c.caught.length||c.startedDay!==null||c.completedDay!==null)throw Error('任务状态不一致');}
    else if(!Number.isSafeInteger(c.startedDay)||c.startedDay<1||c.startedDay>day)throw Error('开课日期无效');
    if(c.status==='active'&&(c.caught.length>=10||c.completedDay!==null))throw Error('进行中任务无效');
    if(c.status==='complete'&&(c.caught.length!==10||!Number.isSafeInteger(c.completedDay)||c.completedDay<c.startedDay||c.completedDay>day))throw Error('完成任务无效');
    return c;
  }
  const api={fresh,targets,validate};if(typeof module!=='undefined')module.exports=api;else root.CampusCourse=api;
})(globalThis);
