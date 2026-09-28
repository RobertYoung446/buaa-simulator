(function (root) {
  'use strict';
  function inRing(x, y, ring) {
    let inside = false;
    for (let i=0,j=ring.length-1;i<ring.length;j=i++) {
      const a=ring[i],b=ring[j];
      if ((a[1]>y)!==(b[1]>y) && x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]) inside=!inside;
    }
    return inside;
  }
  function segmentDistance(x,y,a,b) {
    const dx=b[0]-a[0],dy=b[1]-a[1],n=dx*dx+dy*dy;
    const t=n?Math.max(0,Math.min(1,((x-a[0])*dx+(y-a[1])*dy)/n)):0;
    return Math.hypot(x-a[0]-t*dx,y-a[1]-t*dy);
  }
  function blocked(world,scene,x,y,r=5) {
    const b=scene.bounds;
    if(x-r<b[0]||y-r<b[1]||x+r>b[2]||y+r>b[3])return true;
    for(const o of world.obstacles){
      const b=o.box;if(x+r<b[0]||x-r>b[2]||y+r<b[1]||y-r>b[3])continue;
      let inside=false;for(const ring of o.rings)if(inRing(x,y,ring))inside=!inside;
      if(inside)return true;
      for(const ring of o.rings)for(let i=0;i<ring.length;i++)
        if(segmentDistance(x,y,ring[i],ring[(i+1)%ring.length])<r)return true;
    }
    return false;
  }
  function safeNear(world,scene,x,y,max=220){
    if(!blocked(world,scene,x,y,12))return {x,y};
    for(let d=4;d<=max;d+=4)for(let a=0;a<Math.PI*2;a+=Math.PI/24){
      const nx=x+Math.cos(a)*d,ny=y+Math.sin(a)*d;
      if(!blocked(world,scene,nx,ny,12))return {x:nx,y:ny};
    }
    throw Error('No safe position near '+x+','+y);
  }
  function move(world,scene,p,dx,dy){
    const steps=Math.max(1,Math.ceil(Math.hypot(dx,dy)/4));let hit=false;
    for(let i=0;i<steps;i++){
      if(!blocked(world,scene,p.x+dx/steps,p.y))p.x+=dx/steps;else hit=true;
      if(!blocked(world,scene,p.x,p.y+dy/steps))p.y+=dy/steps;else hit=true;
    }
    return hit;
  }
  function prepare(world){
    const scenes=Object.fromEntries(world.scenes.map(s=>[s.id,s]));
    const points=[];
    for(const p of world.places){
      const b=p.box;
      const pos=safeNear(world,scenes[p.scene],(b[0]+b[2])/2,b[3]+20);
      points.push({...p,...pos,kind:'place'});
    }
    const links=[['living','library',880,425],['living','museum',965,1180],['library','museum',1540,585]];
    for(const [a,b,x,y] of links){
      const overlap={bounds:[Math.max(scenes[a].bounds[0],scenes[b].bounds[0]),Math.max(scenes[a].bounds[1],scenes[b].bounds[1]),Math.min(scenes[a].bounds[2],scenes[b].bounds[2]),Math.min(scenes[a].bounds[3],scenes[b].bounds[3])]};
      const pos=safeNear(world,overlap,x,y);
      for(const [from,to]of[[a,b],[b,a]])points.push({id:from+'-'+to,scene:from,target:to,kind:'portal',name:'前往'+scenes[to].name,...pos});
    }
    const spawn=safeNear(world,scenes.living,800,650);
    return {scenes,points,spawn};
  }
  const api={inRing,blocked,move,safeNear,prepare};
  if(typeof module!=='undefined')module.exports=api;else root.CampusEngine=api;
})(globalThis);
