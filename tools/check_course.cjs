const path=require('node:path'),assert=require('node:assert/strict'),{pathToFileURL}=require('node:url');
const {chromium}=require(path.join(process.env.TEMP,'buaa-browser-check/node_modules/playwright'));
(async()=>{const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});try{
 const page=await browser.newPage({viewport:{width:1360,height:980}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(path.resolve(__dirname,'../灰盒/试玩.html')).href+'?test=1');await page.waitForFunction(()=>campusDebug.snapshot().ready);
 const snap=()=>page.evaluate(()=>campusDebug.snapshot());
 const pts=await page.evaluate(()=>campusDebug.points),targets=await page.evaluate(()=>campusDebug.students);
 assert.equal(targets.length,10);assert.equal((await snap()).course.status,'not_started');
 const place=async p=>{await page.evaluate(p=>campusDebug.place(p.scene,p.x,p.y),p);await page.waitForTimeout(80);};
 await place(targets[0]);assert.equal((await snap()).course.caught.length,0,'cannot catch before course');
 await place(pts.find(p=>p.name==='东区食堂'));await page.keyboard.press('e');assert.equal(await page.locator('#dialogAction').textContent(),'开始在食堂上航概，真下饭！');
 await page.locator('#dialogAction').click();assert.equal((await snap()).course.status,'active');assert.equal((await snap()).period,1);await page.keyboard.press('Escape');
 // Collision pickup happens through normal directional movement, with no interact key.
 const approach=await page.evaluate(t=>{const s=CAMPUS_WORLD.scenes.find(s=>s.id===t.scene);for(const [dx,dy,key]of[[-18,0,'d'],[18,0,'a'],[0,-18,'s'],[0,18,'w']])if(!CampusEngine.blocked(CAMPUS_WORLD,s,t.x+dx,t.y+dy))return {...t,x:t.x+dx,y:t.y+dy,key};throw Error('No approach');},targets[0]);
 await place(approach);await page.keyboard.down(approach.key);await page.waitForTimeout(180);await page.keyboard.up(approach.key);assert.equal((await snap()).course.caught.length,1);
 await page.screenshot({path:path.resolve(__dirname,'../灰盒/课程进行中截图.png'),fullPage:true});
 for(const t of targets.slice(1,3))await place(t);await place(targets[0]);assert.equal((await snap()).course.caught.length,3,'same target not counted twice');
 const dorm=pts.find(p=>p.name==='8公寓');await place(dorm);await page.keyboard.press('e');await page.locator('#dialogAction').click();await page.reload();await page.waitForFunction(()=>campusDebug.snapshot().ready);assert.equal((await snap()).course.caught.length,3);assert.equal((await snap()).course.status,'active');
 assert.deepEqual(await page.evaluate(()=>campusDebug.students),targets,'targets remain stationary and stable after reload');
 for(const t of targets.slice(3))await place(t);assert.equal((await snap()).course.status,'complete');assert.equal((await snap()).course.caught.length,10);assert.equal(await page.locator('#dialogTitle').textContent(),'航空航天概论 · 任务完成');await page.keyboard.press('Escape');
 await place(pts.find(p=>p.name==='东区食堂'));await page.keyboard.press('e');assert(await page.locator('#dialogAction').isHidden(),'completed course cannot restart');await page.keyboard.press('Escape');
 await place(dorm);await page.keyboard.press('e');await page.locator('#dialogAction').click();await page.reload();await page.waitForFunction(()=>campusDebug.snapshot().ready);assert.equal((await snap()).course.status,'complete');assert.equal((await snap()).day,3);
 assert.deepEqual(errors,[]);await page.waitForTimeout(2700);await page.screenshot({path:path.resolve(__dirname,'../灰盒/课程任务截图.png'),fullPage:true});
 // Version 1 sleep saves are still loadable, with the course not yet started.
 assert(await page.evaluate(()=>{const d=CampusProgress.encode({...campusDebug.snapshot(),visited:new Set(),facing:'down'});d.version=1;delete d.course;return CampusProgress.validate(d,CAMPUS_WORLD).course.status==='not_started';}));
 console.log('PASS: exact course option, time cost, ten reachable static targets, movement pickup without E, no duplicate catch/restart, partial and complete save restoration, v1 migration');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
