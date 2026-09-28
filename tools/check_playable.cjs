const assert=require('node:assert/strict');
require('../灰盒/world.js');
const E=require('../灰盒/engine.js'),w=CAMPUS_WORLD,p=E.prepare(w);
p.points.push(...require('../灰盒/course.js').targets(w,E,p.scenes));
// Polygon holes, shoreline edges, and swept movement through a thin wall.
const sample={obstacles:[{box:[20,20,80,80],rings:[[[20,20],[80,20],[80,80],[20,80]],[[40,40],[60,40],[60,60],[40,60]]]}]};
const room={bounds:[0,0,100,100]};
assert(E.blocked(sample,room,30,30,2));assert(!E.blocked(sample,room,50,50,2));assert(E.blocked(sample,room,19,30,2));
const mover={x:10,y:30};E.move(sample,room,mover,85,0);assert(mover.x<20);
// All actual scene entrances and landmarks must be reachable with the real footprint.
for(const scene of w.scenes){
  const step=8,b=scene.bounds,cols=Math.ceil((b[2]-b[0])/step),rows=Math.ceil((b[3]-b[1])/step);
  const free=new Uint8Array(cols*rows),position=i=>({x:b[0]+(i%cols)*step+4,y:b[1]+Math.floor(i/cols)*step+4});
  for(let i=0;i<free.length;i++){const a=position(i);free[i]=!E.blocked(w,scene,a.x,a.y);}
  const start=scene.id==='living'?p.spawn:p.points.find(v=>v.scene===scene.id&&v.kind==='portal');
  let seed=-1,distance=Infinity;for(let i=0;i<free.length;i++)if(free[i]){const a=position(i),d=Math.hypot(a.x-start.x,a.y-start.y);if(d<distance){distance=d;seed=i;}}
  assert(distance<16);const seen=new Set([seed]),queue=[seed];
  for(let head=0;head<queue.length;head++){const i=queue[head],x=i%cols,y=Math.floor(i/cols);for(const [nx,ny]of[[x-1,y],[x+1,y],[x,y-1],[x,y+1]]){const j=ny*cols+nx;if(nx<0||ny<0||nx>=cols||ny>=rows||!free[j]||seen.has(j))continue;const a=position(i),target=position(j);E.move(w,scene,a,target.x-a.x,target.y-a.y);if(Math.hypot(a.x-target.x,a.y-target.y)>.1)continue;seen.add(j);queue.push(j);}}
  for(const target of p.points.filter(v=>v.scene===scene.id)){assert(!E.blocked(w,scene,target.x,target.y,12));assert([...seen].some(i=>{const a=position(i);return Math.hypot(a.x-target.x,a.y-target.y)<16;}),`${scene.id}: unreachable ${target.name}`);}
  console.log(`${scene.name}: all ${p.points.filter(v=>v.scene===scene.id).length} interaction/transition points reachable`);
}
console.log('PASS: polygon holes, wall contact, anti-tunneling, all outdoor routes');
