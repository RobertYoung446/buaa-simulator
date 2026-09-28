const path=require('node:path'),{pathToFileURL}=require('node:url'),assert=require('node:assert/strict');
const {chromium}=require(path.join(process.env.TEMP,'buaa-browser-check/node_modules/playwright'));
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1360,height:980}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.resolve(__dirname,'../灰盒/试玩.html')).href+'?test=1');
  await page.waitForFunction(()=>window.campusDebug?.snapshot().ready);
  const snap=()=>page.evaluate(()=>campusDebug.snapshot());
  let before=await snap();await page.keyboard.down('d');await page.waitForTimeout(600);await page.keyboard.up('d');let after=await snap();assert(after.player.x>before.player.x+20,'keyboard movement');
  await page.locator('#reset').click();await page.keyboard.down('w');await page.waitForTimeout(1200);await page.keyboard.up('w');after=await snap();assert(after.collisions>0,'wall stops movement');
  assert(await page.evaluate(()=>{const s=campusDebug.snapshot();return !CampusEngine.blocked(CAMPUS_WORLD,CAMPUS_WORLD.scenes.find(x=>x.id===s.scene),s.player.x,s.player.y);}), 'player remains outside obstacle');
  const points=await page.evaluate(()=>campusDebug.points);
  for(const p of points){
   await page.evaluate(p=>campusDebug.place(p.scene,p.x,p.y),p);await page.waitForTimeout(50);
   await page.keyboard.press('e');
   if(p.kind==='portal')assert.equal((await snap()).scene,p.target,'portal '+p.id);
   else {await page.locator('#dialog').waitFor({state:'visible'});assert.equal(await page.locator('#dialogTitle').textContent(),p.name==='东区食堂'?'东区食堂 · 航空航天概论':p.name);await page.keyboard.press('Escape');}
  }
  assert.equal((await snap()).visited.length,6);
  await page.keyboard.press('m');before=await snap();await page.keyboard.down('d');await page.waitForTimeout(200);await page.keyboard.up('d');assert.deepEqual((await snap()).player,before.player,'map pauses walking');await page.keyboard.press('Escape');
  const p=points.find(p=>p.name==='8公寓');await page.evaluate(p=>campusDebug.place(p.scene,p.x,p.y),p);await page.waitForTimeout(2700);
  await page.screenshot({path:path.resolve(__dirname,'../灰盒/试玩截图.png'),fullPage:true});
  assert.deepEqual(errors,[]);
  await page.setViewportSize({width:420,height:860});await page.waitForTimeout(100);assert(await page.locator('[data-dir="up"]').isVisible());
  console.log('PASS: file:// loading, keyboard movement, collision, 6 dialogs, 6 directed scene transitions, map pause, mobile controls, no page errors');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
