(() => {
  'use strict';
  const world=CAMPUS_WORLD,E=CampusEngine,P=CampusProgress,prepared=E.prepare(world);
  const $=id=>document.getElementById(id),canvas=$('game'),ctx=canvas.getContext('2d');
  const state={scene:'living',player:{...prepared.spawn},day:1,period:0,keys:new Set(),visited:new Set(),walk:0,facing:'down',camera:{x:0,y:0},ready:false,map:false,transfers:0,collisions:0};
  state.course=CampusCourse.fresh();
  const students=CampusCourse.targets(world,E,prepared.scenes);
  const quest=document.createElement('div');quest.id='quest';quest.setAttribute('role','status');$('stage').appendChild(quest);
  function updateQuest(){const c=state.course;quest.textContent=c.status==='not_started'?'今日安排：去东区食堂按 E，参加航空航天概论。':c.status==='active'?`老师的委托：抓住逃课同学 ${c.caught.length} / 10 · 直接碰到即可 · M 查看紫色目标`:state.day>c.completedDay?'航空航天概论与老师的委托已完成 · 成果已保存，可自由探索':'航空航天概论完成 · 已抓住 10 / 10 · 回8公寓睡觉保存，结束今天';}
  function startCourse(){
    if(state.course.status!=='not_started'||!$('dialog').open)return;
    state.course={status:'active',caught:[],startedDay:state.day,completedDay:null};
    state.period=Math.min(2,state.period+1);updateProgress();updateQuest();closeDialog();
    $('saveStatus').textContent='课程已开始 · 睡觉时保存';
    showDialog('航空航天概论 · 老师的委托','航概开课了！老师发现10名同学溜到了校园各处，请帮忙把他们抓回来。紫色同学会静止等待，走过去碰到即可抓住，无需按键。按 M 可查看位置，青色路口可切换区块。课程占用一个时段，抓人和走路不再耗时。','',null);
  }
  function catchStudents(){
    const c=state.course;if(c.status!=='active')return;
    for(const s of students){if(s.scene!==state.scene||c.caught.includes(s.id)||Math.hypot(s.x-state.player.x,s.y-state.player.y)>10||!hasLineOfSight(state.player,s))continue;
      c.caught.push(s.id);$('saveStatus').textContent='任务进度未存档 · 睡觉时保存';
      toast(`抓住了${s.name}！${c.caught.length} / 10`);
      if(c.caught.length===10){c.status='complete';c.completedDay=state.day;showDialog('航空航天概论 · 任务完成','10名逃课同学全部抓住！老师感谢你的帮助，本次航空航天概论已完成。现在可以自由逛校园，再回8公寓睡觉保存，迎接新的一天。','',null);}
      updateQuest();
    }
  }
  const map=new Image(),sprite=new Image();let vw=0,vh=0,last=0,toastTimer,transition=0,near=null;
  const scene=()=>prepared.scenes[state.scene];
  function resize(){const b=canvas.getBoundingClientRect();vw=b.width;vh=b.height;const d=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(vw*d);canvas.height=Math.round(vh*d);ctx.setTransform(d,0,0,d,0,0);}
  new ResizeObserver(resize).observe($('stage'));
  function toast(text){$('toast').textContent=text;$('toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('show'),2500);}
  function updateName(){$('sceneName').textContent=scene().name;}
  function updateProgress(){$('dayTime').textContent=`第 ${state.day} 天 · ${P.PERIODS[state.period]}`;$('visited').textContent=`已探索 ${state.visited.size} / 6`;$('rest').textContent=state.period===2?'今晚去睡觉':'休息至'+P.PERIODS[state.period+1];}
  function showDialog(title,text,label,action){state.keys.clear();$('dialogTitle').textContent=title;$('dialogText').textContent=text;$('dialogAction').hidden=!action;$('dialogAction').textContent=label||'';$('dialogAction').onclick=action||null;$('dialog').showModal();}
  function rest(){if(!state.ready||$('dialog').open)return;if(state.map)toggleMap(false);if(state.period===2){toast('已经是晚上，去8公寓按 E 睡觉，进入下一天。');return;}showDialog('休息一时段',`休息后从${P.PERIODS[state.period]}进入${P.PERIODS[state.period+1]}。自由走路和查看地点不会消耗时段。`,'确认休息',()=>{state.period++;updateProgress();$('saveStatus').textContent='本日进度未存档 · 睡觉时保存';closeDialog();toast('现在是'+P.PERIODS[state.period]);});}
  function sleep(){
    if(!$('dialog').open)return;
    const dorm=prepared.points.find(p=>p.id==='xueyuan/way/190430062');
    const next={...state,day:state.day+1,period:0,scene:'living',player:E.safeNear(world,prepared.scenes.living,dorm.x,dorm.y),facing:'down'};
    try{P.save(localStorage,next);}catch(error){$('dialogText').textContent='保存失败，日期没有推进。请允许此页面使用浏览器本地存储后重试。';$('saveStatus').textContent='保存失败 · 尚未进入下一天';return;}
    Object.assign(state,{day:next.day,period:0,scene:next.scene,player:next.player,facing:next.facing});updateName();updateProgress();updateQuest();$('saveStatus').textContent=`已保存 · 第 ${state.day} 天上午`;transition=.45;closeDialog();toast(`睡了个好觉！第 ${state.day} 天开始了，进度已保存。`);
  }
  function restore(){try{const saved=P.load(localStorage,world);if(!saved)return false;const dest=prepared.scenes[saved.scene];const position=E.blocked(world,dest,saved.player.x,saved.player.y)?{...prepared.spawn}:saved.player;Object.assign(state,{day:saved.day,period:saved.period,scene:position===saved.player?saved.scene:'living',player:{...position},facing:saved.facing,visited:new Set(saved.visited),course:saved.course});$('saveStatus').textContent=`已读取 · 第 ${state.day} 天${P.PERIODS[state.period]}`;return true;}catch(error){$('saveStatus').textContent='无法读取存档 · 当前从第1天开始，原记录未覆盖';return false;}}
  function hasLineOfSight(a,b){const distance=Math.hypot(a.x-b.x,a.y-b.y);for(let i=1;i<distance;i+=4){const t=i/distance;if(E.blocked(world,scene(),a.x+(b.x-a.x)*t,a.y+(b.y-a.y)*t,1))return false;}return true;}
  function nearest(){return prepared.points.filter(p=>p.scene===state.scene&&Math.hypot(p.x-state.player.x,p.y-state.player.y)<=48&&hasLineOfSight(state.player,p)).sort((a,b)=>Math.hypot(a.x-state.player.x,a.y-state.player.y)-Math.hypot(b.x-state.player.x,b.y-state.player.y))[0]||null;}
  function closeDialog(){$('dialog').close();state.keys.clear();$('stage').focus();}
  function interact(){
    if(!state.ready)return;
    if($('dialog').open){closeDialog();return;}if(state.map)return;
    const p=nearest();if(!p){toast('走近橙色地点标记或青色路口指示牌，再按 E');return;}
    state.keys.clear();
    if(p.kind==='portal'){
      state.scene=p.target;state.player=E.safeNear(world,scene(),p.x,p.y);state.transfers++;transition=.45;near=null;updateName();toast('已到达 '+scene().name);$('stage').focus();
    }else{
      if(!state.visited.has(p.id))$('saveStatus').textContent='新增探索未存档 · 睡觉时保存';
      state.visited.add(p.id);$('visited').textContent=`已探索 ${state.visited.size} / 6`;
      const dorm=p.id==='xueyuan/way/190430062';
      if(p.id==='xueyuan/way/190427995'){
        const c=state.course;
        showDialog('东区食堂 · 航空航天概论',c.status==='not_started'?'今天的航空航天概论在食堂开讲。开始课程占用一个时段，并接受老师的抓人委托；如果已是晚上，则使用今晚时段，睡觉后才进入明天。':c.status==='active'?`老师正在等你：已抓住 ${c.caught.length} / 10 名逃课同学。走到紫色同学身边即可抓住。`:'课程已完成，10名同学全部归队！回8公寓睡觉可保存本次成果。',c.status==='not_started'?'开始在食堂上航概，真下饭！':'',c.status==='not_started'?startCourse:null);return;
      }
      showDialog(p.name,p.text+(dorm?` 现在是第${state.day}天${P.PERIODS[state.period]}。睡觉会结束今天剩余时段，进入明天上午并保存进度。`:''),dorm?'睡觉并保存 · 进入明天':'',dorm?sleep:null);
    }
  }
  function toggleMap(force){state.map=force??!state.map;$('minimapPanel').hidden=!state.map;state.keys.clear();if(state.map)drawMinimap();else $('stage').focus();}
  function reset(){state.scene='living';state.player={...prepared.spawn};state.keys.clear();near=null;updateName();toggleMap(false);if($('dialog').open)closeDialog();toast('已回到生活区起点');}
  function drawMinimap(){const c=$('minimap'),m=c.getContext('2d'),s=c.width/world.width;m.clearRect(0,0,c.width,c.height);m.drawImage(map,0,0,c.width,c.height);const b=scene().bounds;m.strokeStyle='#183f37';m.lineWidth=2;m.strokeRect(b[0]*s,b[1]*s,(b[2]-b[0])*s,(b[3]-b[1])*s);for(const p of prepared.points){m.fillStyle=p.kind==='portal'?'#187e87':'#d85f32';m.beginPath();m.arc(p.x*s,p.y*s,3,0,Math.PI*2);m.fill();}if(state.course.status==='active')for(const t of students){if(state.course.caught.includes(t.id))continue;m.fillStyle='#793fbc';m.beginPath();m.arc(t.x*s,t.y*s,4,0,Math.PI*2);m.fill();}m.fillStyle='#ffea42';m.strokeStyle='#34462c';m.beginPath();m.arc(state.player.x*s,state.player.y*s,5,0,Math.PI*2);m.fill();m.stroke();}
  function marker(p){const isNear=near?.id===p.id;ctx.fillStyle=p.kind==='portal'?'#357c80':'#b86939';ctx.strokeStyle='#fffcdd';ctx.lineWidth=2;ctx.beginPath();ctx.arc(p.x,p.y,7+(isNear?2:0),0,Math.PI*2);ctx.fill();ctx.stroke();ctx.font='12px "Microsoft YaHei",sans-serif';ctx.textAlign='center';const label=p.kind==='portal'?'↗ '+prepared.scenes[p.target].name:p.name;const width=ctx.measureText(label).width+14;ctx.fillStyle=isNear?'#233e35ef':'#fffbeded';ctx.fillRect(p.x-width/2,p.y-31,width,20);ctx.fillStyle=isNear?'#fff5ce':'#395749';ctx.fillText(label,p.x,p.y-17);}
  function render(dt){
    const b=scene().bounds,scale=1.25;
    const cw=vw/scale,ch=vh/scale;
    const clamp=(v,min,max)=>max<min?(min+max)/2:Math.max(min,Math.min(max,v));
    state.camera={x:clamp(state.player.x-cw/2,b[0],b[2]-cw),y:clamp(state.player.y-ch/2,b[1],b[3]-ch)};
    ctx.clearRect(0,0,vw,vh);ctx.save();ctx.scale(scale,scale);ctx.translate(-state.camera.x,-state.camera.y);ctx.drawImage(map,0,0,world.width,world.height);
    ctx.fillStyle='#213d3860';ctx.fillRect(0,0,world.width,b[1]);ctx.fillRect(0,b[3],world.width,world.height-b[3]);ctx.fillRect(0,b[1],b[0],b[3]-b[1]);ctx.fillRect(b[2],b[1],world.width-b[2],b[3]-b[1]);
    ctx.strokeStyle='#4a766c';ctx.lineWidth=2;ctx.setLineDash([7,7]);ctx.strokeRect(b[0],b[1],b[2]-b[0],b[3]-b[1]);ctx.setLineDash([]);
    for(const p of prepared.points)if(p.scene===state.scene)marker(p);
    if(state.course.status==='active')for(const s of students){
      if(s.scene!==state.scene||state.course.caught.includes(s.id))continue;
      ctx.fillStyle='#44395d44';ctx.beginPath();ctx.ellipse(s.x,s.y+1,6,3,0,0,Math.PI*2);ctx.fill();
      ctx.fillStyle='#4b3d63';ctx.fillRect(s.x-5,s.y-7,4,8);ctx.fillRect(s.x+1,s.y-7,4,8);
      ctx.fillStyle='#9567c8';ctx.fillRect(s.x-7,s.y-20,14,15);
      ctx.fillStyle='#f5d1a6';ctx.beginPath();ctx.arc(s.x,s.y-24,5,0,Math.PI*2);ctx.fill();
      ctx.fillStyle='#392950';ctx.font='11px sans-serif';ctx.textAlign='center';ctx.fillText(s.name,s.x,s.y-34);
    }
    const p=state.player,bob=state.moving?Math.sin(state.walk):0;
    ctx.fillStyle='#293f3545';ctx.beginPath();ctx.ellipse(p.x,p.y+1,6,3,0,0,Math.PI*2);ctx.fill();
    ctx.save();ctx.translate(p.x,p.y+bob);if(state.facing==='left')ctx.scale(-1,1);ctx.rotate(state.moving?Math.sin(state.walk)*.035:0);ctx.drawImage(sprite,-12,-31,24,36);ctx.restore();
    // Direction indicator keeps facing legible with the single reference-based sprite.
    const dir={up:[0,-1],down:[0,1],left:[-1,0],right:[1,0]}[state.facing];ctx.fillStyle='#fff6b0';ctx.beginPath();ctx.arc(p.x+dir[0]*10,p.y+dir[1]*7,1.5,0,Math.PI*2);ctx.fill();
    ctx.restore();
    if(state.period){ctx.fillStyle=state.period===1?'rgba(243,168,63,.06)':'rgba(29,40,87,.21)';ctx.fillRect(0,0,vw,vh);}
    if(transition>0){transition-=dt;ctx.fillStyle=`rgba(241,237,219,${Math.max(0,transition/.45)*.8})`;ctx.fillRect(0,0,vw,vh);}
  }
  function frame(time){
    const dt=Math.min((time-last)/1000||0,0.05);last=time;
    if(state.ready){
      state.moving=false;
      if(!state.map&&!$('dialog').open){
        const k=state.keys;let dx=0,dy=0;
        // Four-direction movement; vertical input has priority when held together.
        if(k.has('w')||k.has('arrowup'))dy=-1;else if(k.has('s')||k.has('arrowdown'))dy=1;
        else if(k.has('a')||k.has('arrowleft'))dx=-1;else if(k.has('d')||k.has('arrowright'))dx=1;
        if(dx||dy){state.facing=dx<0?'left':dx>0?'right':dy<0?'up':'down';const speed=k.has('shift')?200:125;const before={...state.player};if(E.move(world,scene(),state.player,dx*speed*dt,dy*speed*dt))state.collisions++;state.moving=Math.hypot(before.x-state.player.x,before.y-state.player.y)>.01;if(state.moving)state.walk+=dt*13;}
        catchStudents();near=nearest();$('prompt').hidden=!near||$('dialog').open;if(near)$('interact').textContent='E · '+(near.kind==='portal'?near.name:'查看 '+near.name);
      }else $('prompt').hidden=true;
      render(dt);
    }
    requestAnimationFrame(frame);
  }
  const movement=new Set(['w','a','s','d','arrowup','arrowdown','arrowleft','arrowright','shift']);
  window.addEventListener('keydown',e=>{const key=e.key.toLowerCase();if(movement.has(key)){if(e.target.tagName==='BUTTON'&&key===' ' )return;e.preventDefault();state.keys.add(key);}else if(!e.repeat&&['e','m','escape'].includes(key)){e.preventDefault();if(key==='e')interact();else if(key==='m') {if(!$('dialog').open)toggleMap();}else if($('dialog').open)closeDialog();else toggleMap(false);}});
  window.addEventListener('keyup',e=>state.keys.delete(e.key.toLowerCase()));window.addEventListener('blur',()=>state.keys.clear());document.addEventListener('visibilitychange',()=>{if(document.hidden)state.keys.clear();});
  $('dialog').addEventListener('cancel',e=>{e.preventDefault();closeDialog();});$('closeDialog').onclick=closeDialog;$('interact').onclick=interact;$('touchE').onclick=interact;$('mapButton').onclick=()=>toggleMap();$('closeMap').onclick=()=>toggleMap(false);$('reset').onclick=reset;
  $('rest').onclick=rest;
  const codes={up:'w',down:'s',left:'a',right:'d'};
  document.querySelectorAll('[data-dir]').forEach(button=>{button.onpointerdown=e=>{e.preventDefault();button.setPointerCapture(e.pointerId);state.keys.add(codes[button.dataset.dir]);};for(const name of ['pointerup','pointercancel','lostpointercapture'])button.addEventListener(name,()=>state.keys.delete(codes[button.dataset.dir]));});
  function load(img,src){return new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=()=>reject(Error('无法载入 '+src));img.src=src;});}
  Promise.all([load(map,'campus.svg'),load(sprite,'assets/player.png')]).then(()=>{const loaded=restore();state.ready=true;$('loading').hidden=true;updateName();updateProgress();updateQuest();resize();$('stage').focus();toast(loaded?'已继续上次睡觉存档。':'欢迎来到校园！走路不耗时，到8公寓睡觉存档。');}).catch(e=>{$('loading').textContent=e.message+'，请保留试玩文件与素材目录的相对位置。';});
  // Read-only state and a gated test driver for browser regression checks.
  window.campusDebug={snapshot:()=>({scene:state.scene,player:{...state.player},day:state.day,period:state.period,ready:state.ready,near:nearest()?.id,visited:[...state.visited],transfers:state.transfers,collisions:state.collisions,course:JSON.parse(JSON.stringify(state.course))}),students,points:prepared.points};
  if(new URLSearchParams(location.search).has('test'))window.campusDebug.place=(sceneId,x,y)=>{if(!prepared.scenes[sceneId]||E.blocked(world,prepared.scenes[sceneId],x,y))throw Error('Unsafe test position');state.scene=sceneId;state.player={x,y};updateName();};
  requestAnimationFrame(frame);
})();
