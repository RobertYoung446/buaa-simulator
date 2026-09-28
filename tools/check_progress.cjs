const path=require('node:path'),fs=require('node:fs'),os=require('node:os'),assert=require('node:assert/strict'),{pathToFileURL}=require('node:url');
const {chromium}=require(path.join(process.env.TEMP,'buaa-browser-check/node_modules/playwright'));
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'buaa-save-test-'));
const url=pathToFileURL(path.resolve(__dirname,'../灰盒/试玩.html')).href+'?test=1';
const options={executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,viewport:{width:1360,height:1000}};
(async()=>{let context;try{
 context=await chromium.launchPersistentContext(profile,options);let page=await context.newPage();await page.goto(url);await page.waitForFunction(()=>campusDebug.snapshot().ready);
 const snap=()=>page.evaluate(()=>campusDebug.snapshot());
 assert.equal((await snap()).day,1);assert.equal((await snap()).period,0);
 await page.keyboard.down('d');await page.waitForTimeout(150);await page.keyboard.up('d');assert.equal((await snap()).period,0);
 await page.locator('#rest').click();await page.keyboard.press('Escape');assert.equal((await snap()).period,0,'cancel does not consume time');
 for(const period of [1,2]){await page.locator('#rest').click();await page.locator('#dialogAction').click();assert.equal((await snap()).period,period);}
 await page.locator('#rest').click();assert.equal((await snap()).period,2,'evening does not wrap');
 const dorm=await page.evaluate(()=>campusDebug.points.find(p=>p.name==='8公寓'));
 await page.evaluate(p=>campusDebug.place(p.scene,p.x,p.y),dorm);await page.keyboard.press('e');await page.keyboard.press('Escape');assert.equal((await snap()).day,1,'cancel sleep does not advance');
 await page.keyboard.press('e');await page.evaluate(()=>{window.realSetItem=Storage.prototype.setItem;Storage.prototype.setItem=function(){throw Error('quota');};});await page.locator('#dialogAction').click();assert.equal((await snap()).day,1,'failed save does not advance');assert((await page.locator('#dialogText').textContent()).includes('保存失败'));
 await page.evaluate(()=>Storage.prototype.setItem=window.realSetItem);await page.locator('#dialogAction').click();assert.equal((await snap()).day,2);assert.equal((await snap()).period,0);const saved=await snap();
 await page.locator('#rest').click();await page.locator('#dialogAction').click();assert.equal((await snap()).period,1);
 await context.close();context=await chromium.launchPersistentContext(profile,options);page=await context.newPage();await page.goto(url);await page.waitForFunction(()=>campusDebug.snapshot().ready);
 assert.equal((await snap()).day,2);assert.equal((await snap()).period,0,'restored last sleep snapshot');assert.deepEqual((await snap()).visited,saved.visited);assert.deepEqual((await snap()).player,saved.player);
 await page.waitForTimeout(2700);await page.screenshot({path:path.resolve(__dirname,'../灰盒/试玩截图.png'),fullPage:true});
 await page.evaluate(()=>localStorage.setItem(CampusProgress.KEY,'{broken'));await page.reload();await page.waitForFunction(()=>campusDebug.snapshot().ready);assert.equal((await snap()).day,1);assert((await page.locator('#saveStatus').textContent()).includes('无法读取'));assert.equal(await page.evaluate(()=>localStorage.getItem(CampusProgress.KEY)),'{broken');
 console.log('PASS: three periods, cancel, evening bound, sleep, failed-save rollback, process restart restoration, visited/position preservation, corrupt-save recovery');
}finally{if(context)await context.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
