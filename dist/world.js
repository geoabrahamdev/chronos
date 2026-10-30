const $ = (s) => document.querySelector(s);
const worldCanvas = $('#world'), brainCanvas = $('#brain');
const wctx = worldCanvas.getContext('2d'), bctx = brainCanvas.getContext('2d');
let latest = null, busy = false;
let currentFrame = 'world', worldlineData = null, timeCursor = 1, branchData = null;
let brainMode = 'schematic'; const brain3d = { yaw: Math.PI/5, pitch: 0.25 };
// Cell positions are read from node.coord.norm (computed server-side from real MaleCNS synapse coordinates).
const WORLD_SPAN = 10;
const FLY_HORIZON = 0.9;  // CHRONOS sensory horizon, world units; shared with brain panel assumptions
const camera = {yaw:Math.PI/4,pitch:.78,zoom:1,follow:false,focus:{x:5,y:5}};

function fit(canvas, ctx) { const r=canvas.getBoundingClientRect(), d=devicePixelRatio||1; canvas.width=r.width*d;canvas.height=r.height*d;ctx.setTransform(d,0,0,d,0,0); return r; }
function pos(c,x,y){return [c.width/devicePixelRatio*x,c.height/devicePixelRatio*y]}
function ellipse(ctx,x,y,rx,ry,color){ctx.fillStyle=color;ctx.beginPath();ctx.ellipse(x,y,rx,ry,0,0,Math.PI*2);ctx.fill()}
function text(ctx,value,x,y,size=10,color='#fff',align='left'){ctx.fillStyle=color;ctx.font=`${size}px DM Mono`;ctx.textAlign=align;ctx.fillText(value,x,y)}

function project(W,H,x,y,z=0){
  const dx=(x-camera.focus.x)/WORLD_SPAN,dy=(y-camera.focus.y)/WORLD_SPAN,cos=Math.cos(camera.yaw),sin=Math.sin(camera.yaw);
  const right=dx*cos-dy*sin,depth=dx*sin+dy*cos;
  return [W*.5+right*W*.566*camera.zoom,H*.53+depth*H*.41*camera.pitch*camera.zoom-z*H*.50*(1.35-camera.pitch*.35)*camera.zoom];
}
function groundPoint(rect,clientX,clientY){
  const sx=(clientX-rect.left)/rect.width,sy=(clientY-rect.top)/rect.height;
  const right=(sx-.5)/(.566*camera.zoom),depth=(sy-.53)/(.41*camera.pitch*camera.zoom),cos=Math.cos(camera.yaw),sin=Math.sin(camera.yaw);
  return {x:Math.max(.08,Math.min(9.92,camera.focus.x+WORLD_SPAN*(right*cos+depth*sin))),y:Math.max(.08,Math.min(9.92,camera.focus.y+WORLD_SPAN*(-right*sin+depth*cos)))};
}
function refreshView(){
  const degrees=((camera.yaw*180/Math.PI)%360+360)%360;
  $('#viewReadout').textContent=`${Math.round(degrees)}° / ${camera.zoom.toFixed(1)}×`;
  $('#followView').classList.toggle('active',camera.follow);
  $('#followView').textContent=camera.follow?'FOLLOWING':'FOLLOW';
  if(latest)drawWorld(latest);
}
function drawWorld(data){
  if(currentFrame==='block') return drawBlock(data);
  if(currentFrame==='fly')   return drawFly(data);
  const r=fit(worldCanvas,wctx), W=r.width,H=r.height; wctx.clearRect(0,0,W,H);
  const f=data.fly;camera.focus=camera.follow?{x:f.x,y:f.y}:{x:5,y:5};
  const sky=wctx.createLinearGradient(0,0,0,H);sky.addColorStop(0,'#142a31');sky.addColorStop(.40,'#6caeb1');sky.addColorStop(.58,'#adc688');sky.addColorStop(1,'#365c36');wctx.fillStyle=sky;wctx.fillRect(0,0,W,H);
  // Isometric 3D ground plane, depth grid and distant tree-line.
  const corners=[[0,0],[WORLD_SPAN,0],[WORLD_SPAN,WORLD_SPAN],[0,WORLD_SPAN]].map(p=>project(W,H,p[0],p[1],0));wctx.fillStyle='#426e3e';wctx.beginPath();corners.forEach(([x,y],i)=>i?wctx.lineTo(x,y):wctx.moveTo(x,y));wctx.closePath();wctx.fill();
  data.world.biomes.forEach(b=>{const zone=[[b.x,b.y],[b.x+b.w,b.y],[b.x+b.w,b.y+b.h],[b.x,b.y+b.h]].map(p=>project(W,H,p[0],p[1],0));wctx.fillStyle=b.color;wctx.beginPath();zone.forEach(([x,y],i)=>i?wctx.lineTo(x,y):wctx.moveTo(x,y));wctx.closePath();wctx.fill();wctx.strokeStyle='rgba(225,245,203,.14)';wctx.stroke();const label=project(W,H,b.x+b.w/2,b.y+b.h/2,.01);text(wctx,b.label,label[0],label[1],7,'rgba(235,246,220,.55)','center')});
  for(let q=1;q<WORLD_SPAN;q+=1){wctx.strokeStyle='rgba(211,239,174,.12)';wctx.lineWidth=1;[[q,0,q,WORLD_SPAN],[0,q,WORLD_SPAN,q]].forEach(([a,b,c,d])=>{const p=project(W,H,a,b),e=project(W,H,c,d);wctx.beginPath();wctx.moveTo(...p);wctx.lineTo(...e);wctx.stroke()})}
  (data.world.roads||[]).forEach(road=>{const a=project(W,H,road.x1,road.y1,.012),b=project(W,H,road.x2,road.y2,.012);wctx.strokeStyle='#48534b';wctx.lineWidth=40;wctx.beginPath();wctx.moveTo(...a);wctx.lineTo(...b);wctx.stroke();wctx.strokeStyle='#f0d86a';wctx.lineWidth=2;wctx.setLineDash([11,9]);wctx.beginPath();wctx.moveTo(...a);wctx.lineTo(...b);wctx.stroke();wctx.setLineDash([]);text(wctx,`${road.label} • CROSSABLE`,a[0]+12,a[1]-15,7,'#f0d86a')});
  (data.world.trees||[]).forEach(({x:tx,y:ty,h})=>{const base=project(W,H,tx,ty,0),top=project(W,H,tx,ty,h);wctx.strokeStyle='#294a2d';wctx.lineWidth=4;wctx.beginPath();wctx.moveTo(...base);wctx.lineTo(...top);wctx.stroke();ellipse(wctx,top[0],top[1],16,11,'#235f34');ellipse(wctx,top[0]-9,top[1]+4,10,8,'#31743c');ellipse(wctx,top[0]+10,top[1]+3,11,8,'#438346')});
  const [wx,wy,wz]=data.world.wind;
  for(let i=0;i<24;i++){const a=((i*.17+(performance.now()/20000)%1)%1)*WORLD_SPAN,b=(i*.31%1)*WORLD_SPAN,z=.12+(i%4)*.08,p=project(W,H,a,b,z),e=project(W,H,a+wx*.45,b+wy*.45,z+wz*2);wctx.strokeStyle='rgba(231,251,229,.28)';wctx.beginPath();wctx.moveTo(...p);wctx.lineTo(...e);wctx.stroke()}
  data.world.sources.slice().sort((a,b)=>a.x+a.y-b.x-b.y).forEach(s=>{
    const [x,y]=project(W,H,s.x,s.y,s.z||0);
    if((s.z||0)>.07){const base=project(W,H,s.x,s.y,0);wctx.setLineDash([2,3]);wctx.strokeStyle='rgba(232,249,209,.5)';wctx.beginPath();wctx.moveTo(...base);wctx.lineTo(x,y);wctx.stroke();wctx.setLineDash([])}
    if(s.kind==='food'){for(let i=4;i>0;i--){const plume=project(W,H,s.x+wx*.12*i,s.y+wy*.12*i,(s.z||0)+.03*i);ellipse(wctx,plume[0],plume[1],12+i*7,6+i*4,`${s.color}${(8+i*5).toString(16).padStart(2,'0')}`)}}
    if(s.kind==='water'){ellipse(wctx,x,y,26,10,'#3d98ad');ellipse(wctx,x-7,y-3,10,3,'#a6dce2')}
    else if(s.kind==='rest'){ellipse(wctx,x,y,22,10,'#69492d');ellipse(wctx,x,y-5,18,8,'#a47842')}
    else if(s.kind==='threat'){ellipse(wctx,x,y,12,7,'#17221a');for(let a=0;a<6;a++){let q=a*Math.PI/3;wctx.strokeStyle='#17221a';wctx.beginPath();wctx.moveTo(x,y);wctx.lineTo(x+Math.cos(q)*18,y+Math.sin(q)*13);wctx.stroke()}}
    else {ellipse(wctx,x,y,12,8,s.color);ellipse(wctx,x+7,y-9,5,11,'#f2ebd0')}
    text(wctx,`${s.label.toUpperCase()}${(s.z||0)>.07?` / Z${s.z.toFixed(2)}`:''}`,x,y-18,8,s.user_created?'#d4f16b':'#f8f9e9','center');
  });
  (data.world.cars||[]).forEach(car=>{const p=project(W,H,car.x,car.y,car.z||.025),road=(data.world.roads||[]).find(item=>item.id===car.road),end=road?project(W,H,road.x2,road.y2,.025):[p[0]+1,p[1]],angle=Math.atan2(end[1]-p[1],end[0]-p[0])+(car.direction<0?Math.PI:0);wctx.save();wctx.translate(...p);wctx.rotate(angle);wctx.fillStyle=car.color;wctx.fillRect(-16,-8,32,16);wctx.fillStyle='#bcd6df';wctx.fillRect(-4,-6,12,12);wctx.fillStyle='#17201c';wctx.fillRect(-12,-10,6,4);wctx.fillRect(7,6,6,4);wctx.restore();text(wctx,'PASSING CAR',p[0],p[1]-14,6,'#f4df87','center')});
  // Make the vertical decision visible: resource goals get a ground-contact guide,
  // while a threat creates an upward escape cue beside the fly.
  const flight=data.flight||{},targetSource=data.world.sources.find(source=>source.id===flight.target_id);
  if(targetSource&&flight.mode!=='climb / evade'){
    const ground=project(W,H,targetSource.x,targetSource.y,targetSource.z||0),contact=project(W,H,targetSource.x,targetSource.y,flight.contact_z||.045);
    wctx.setLineDash([3,4]);wctx.strokeStyle='rgba(212,241,107,.85)';wctx.lineWidth=1.5;wctx.beginPath();wctx.moveTo(...ground);wctx.lineTo(...contact);wctx.stroke();wctx.setLineDash([]);
    ellipse(wctx,contact[0],contact[1],6,3,'rgba(212,241,107,.85)');text(wctx,`${flight.mode.toUpperCase()} Z ${flight.target_z.toFixed(2)}`,contact[0],contact[1]-9,7,'#d4f16b','center');
  }
  const home=data.world.home,homeP=project(W,H,home[0],home[1],0);wctx.setLineDash([4,5]);wctx.strokeStyle='rgba(218,244,126,.55)';wctx.beginPath();wctx.ellipse(homeP[0],homeP[1],23,9,0,0,Math.PI*2);wctx.stroke();wctx.setLineDash([]);
  if(f.trail.length>1){wctx.strokeStyle=data.compass_enabled?'rgba(212,241,107,.62)':'rgba(255,113,102,.68)';wctx.lineWidth=1.4;wctx.beginPath();f.trail.forEach((p,i)=>{const q=project(W,H,p[0],p[1],p[2]||0);i?wctx.lineTo(...q):wctx.moveTo(...q)});wctx.stroke()}
  const [x,y]=project(W,H,f.x,f.y,f.z);wctx.save();wctx.translate(x,y);wctx.rotate(f.heading+Math.PI/2);wctx.fillStyle='#111d18';wctx.beginPath();wctx.ellipse(0,2,8,15,0,0,Math.PI*2);wctx.fill();wctx.fillStyle='rgba(211,240,232,.74)';wctx.beginPath();wctx.ellipse(-10,0,12,3,-.45,0,Math.PI*2);wctx.ellipse(10,0,12,3,.45,0,Math.PI*2);wctx.fill();wctx.fillStyle='#e6f86f';wctx.beginPath();wctx.arc(0,-11,4,0,Math.PI*2);wctx.fill();wctx.restore();
  const interaction=data.interaction||{};
  if(interaction.active){wctx.strokeStyle='#d4f16b';wctx.lineWidth=3;wctx.beginPath();wctx.arc(x,y,22,-Math.PI/2,-Math.PI/2+Math.PI*2*interaction.progress);wctx.stroke();text(wctx,`${interaction.mode.toUpperCase()} ${Math.round(interaction.progress*100)}% • ${interaction.remaining.toFixed(1)}s`,x,y-31,8,'#d4f16b','center')}
  if(flight.mode==='climb / evade'){wctx.strokeStyle='#ff7166';wctx.lineWidth=2;wctx.beginPath();wctx.moveTo(x+14,y+12);wctx.lineTo(x+14,y-20);wctx.lineTo(x+9,y-14);wctx.moveTo(x+14,y-20);wctx.lineTo(x+19,y-14);wctx.stroke();text(wctx,'CLIMB / EVADE',x+20,y-22,7,'#ff9b90')}
  text(wctx,`FLY ALT ${f.z.toFixed(2)}  •  WIND XYZ ${wx.toFixed(2)},${wy.toFixed(2)},${wz.toFixed(2)}`,18,H-55,9,'#d4f16b');
}

let brainGroupsHit = [];
function drawBrain(data){
  if(brainMode === 'wiring3d') return drawBrain3D(data);
  const r=fit(brainCanvas,bctx),W=r.width,H=r.height,path=data.pathway;
  bctx.fillStyle='#111714';bctx.fillRect(0,0,W,H);
  text(bctx,'ONE VERIFIED MALECNS ROUTE · CLICK ANY CARD',20,58,10,'#d7e6d3');
  text(bctx,'REAL DIRECTED EDGES  •  LIVE RATE IS A CHRONOS MODEL',20,74,8,'#748978');
  brainGroupsHit = [];
  const groups=[
    {label:'1  SMELL',meaning:'antenna detects DM1 odor',nodes:[0],color:'#ffbe58'},
    {label:'2  RELAY',meaning:'projection neuron carries odor',nodes:[1],color:'#64ddc2'},
    {label:'3  CONTEXT',meaning:'higher-order processing',nodes:[2,3,4,5,6],color:'#64ddc2'},
    {label:'4  COMPASS',meaning:'central-complex route',nodes:[7,8,9],color:'#b28af4'},
    {label:'5  DESCEND',meaning:'command leaves brain',nodes:[10],color:'#64ddc2'},
    {label:'6  MOVE',meaning:'VNC motor neuron',nodes:[11],color:'#d4f16b'}
  ];
  const nodeGroup=Object.fromEntries(groups.flatMap((group,index)=>group.nodes.map(node=>[node,index])));
  const cardX=20,cardW=W-40,cardH=54,startY=92,gap=9;
  groups.forEach((group,index)=>{
    const y=startY+index*(cardH+gap),active=Math.max(...group.nodes.map(n=>path.nodes[n].rate));
    brainGroupsHit.push({ y, cardH, group, cssYRatio: y/H, cssHRatio: cardH/H });
    bctx.fillStyle=active>.002?'#173a33':'#17201c';bctx.strokeStyle=active>.002?group.color:'rgba(173,198,173,.22)';bctx.lineWidth=1;
    bctx.fillRect(cardX,y,cardW,cardH);bctx.strokeRect(cardX,y,cardW,cardH);
    bctx.fillStyle=group.color;bctx.fillRect(cardX,y,4,cardH);
    text(bctx,group.label,cardX+14,y+17,9,group.color);text(bctx,group.meaning,cardX+14,y+35,8,'#a8b7a6');
    const names=group.nodes.map(n=>path.nodes[n].type).join('  ·  ');
    text(bctx,names,cardX+cardW-14,y+21,Math.min(9,Math.max(6,10-names.length/18)),active>.002?'#f0fff2':'#cad4c9','right');
    text(bctx,group.nodes.length===1?`CELL ${path.nodes[group.nodes[0]].body}`:`${group.nodes.length} REAL CELLS`,cardX+cardW-14,y+38,7,'#748978','right');
    if(index<groups.length-1){
      const links=path.edges.filter(edge=>nodeGroup[path.nodes.findIndex(n=>n.body===edge.pre)]===index&&nodeGroup[path.nodes.findIndex(n=>n.body===edge.post)]===index+1);
      const internal=path.edges.filter(edge=>nodeGroup[path.nodes.findIndex(n=>n.body===edge.pre)]===index&&nodeGroup[path.nodes.findIndex(n=>n.body===edge.post)]===index);
      const count=links.reduce((sum,edge)=>sum+edge.synapses,0);
      bctx.strokeStyle=active>.002?group.color:'rgba(173,198,173,.25)';bctx.lineWidth=active>.002?2:1;bctx.beginPath();bctx.moveTo(W*.5,y+cardH);bctx.lineTo(W*.5,y+cardH+gap);bctx.stroke();
      if(count)text(bctx,`${count} SYN.`,W*.5+7,y+cardH+gap-1,7,'#8ea99a');
      if(internal.length)text(bctx,`${internal.length} REAL EDGES INSIDE`,W*.84,y+cardH+gap-1,7,'#8ea99a','right');
    }
  });
  const finalRate=path.nodes[path.nodes.length-1].rate;
  const status=finalRate>.002?'ODOR SIGNAL REACHING MOTOR OUTPUT':'NO DM1 SIGNAL AT THE FLY — ROUTE IS IDLE';
  text(bctx,status,W*.5,H-68,9,finalRate>.002?'#d4f16b':'#8d9a8e','center');
  text(bctx,'CARD ORDER IS A FUNCTIONAL SCHEMATIC, NOT A PHYSICAL BRAIN SHAPE.',W*.5,H-52,7,'#69776b','center');
}


function drawBrain3D(data){
  const r=fit(brainCanvas,bctx),W=r.width,H=r.height;
  bctx.fillStyle='#0a1013'; bctx.fillRect(0,0,W,H);
  const path=data.pathway;
  const scale = Math.min(W,H) * 0.42;
  const cx = W*0.5, cy = H*0.5 + 20;

  function proj(p){
    const cy_y = Math.cos(brain3d.yaw), sy = Math.sin(brain3d.yaw);
    const x1 =  p.x*cy_y + p.z*sy;
    const z1 = -p.x*sy   + p.z*cy_y;
    const cp = Math.cos(brain3d.pitch), sp = Math.sin(brain3d.pitch);
    const y1 = p.y*cp - z1*sp;
    const z2 = p.y*sp + z1*cp;
    const d  = z2 + 2.4;
    return { sx: cx + (x1*scale)/d, sy: cy + (y1*scale)/d, depth: z2 };
  }

  // Honest fallback: if a cell has no real coord yet (first tick before pathway loads), it stays off-screen.
  const points = path.nodes.map(node => {
    const c = node.coord && node.coord.norm;
    const pos = c ? { x:c[0], y:c[1], z:c[2] } : null;
    const roi = (node.coord && node.coord.sample_count) || 0;
    return { node, pos, available: !!pos, proj: pos ? proj(pos) : null, nSamples: roi };
  }).filter(p => p.available);

  if(!points.length){
    text(bctx, 'LOADING PATHWAY COORDINATES...', W*0.5, H*0.5, 11, '#8ea99a', 'center');
    return;
  }

  // Reference axes rooted at the pathway centroid origin (0,0,0 in normalized space).
  const axLen = 0.9;
  [['#78906e', {x:axLen,y:0,z:0}, 'X'],
   ['#78906e', {x:0,y:axLen,z:0}, 'Y'],
   ['#78906e', {x:0,y:0,z:axLen}, 'Z']].forEach(([col,end,lbl])=>{
    const o = proj({x:0,y:0,z:0}), e = proj(end);
    bctx.strokeStyle = col+'55'; bctx.lineWidth = 1;
    bctx.beginPath(); bctx.moveTo(o.sx,o.sy); bctx.lineTo(e.sx,e.sy); bctx.stroke();
    text(bctx, lbl, e.sx+4, e.sy-2, 7, col+'bb');
  });

  // Edges, sorted far-to-near.
  const bodyToIdx = new Map(path.nodes.map((n,i)=>[n.body, i]));
  const edgesWithDepth = path.edges.map(edge => {
    const preIdx = bodyToIdx.get(edge.pre);
    const postIdx = bodyToIdx.get(edge.post);
    if(preIdx==null || postIdx==null) return null;
    const p = points.find(pt => pt.node.body === edge.pre);
    const q = points.find(pt => pt.node.body === edge.post);
    if(!p || !q) return null;
    return { edge, p, q, depth: (p.proj.depth + q.proj.depth)/2 };
  }).filter(Boolean).sort((a,b)=> b.depth - a.depth);

  edgesWithDepth.forEach(({edge, p, q, depth}) => {
    const activityScalar = edge.synapses ? (edge.activity||0) / edge.synapses : 0;
    const alpha = Math.max(0.2, Math.min(0.95, 0.95 - depth*0.25));
    const col = activityScalar > 0.3 ? `rgba(212,241,107,${alpha.toFixed(2)})` : `rgba(142,169,154,${(alpha*0.55).toFixed(2)})`;
    bctx.strokeStyle = col;
    bctx.lineWidth = Math.max(1, Math.sqrt(edge.synapses) * 0.35);
    bctx.beginPath(); bctx.moveTo(p.proj.sx, p.proj.sy); bctx.lineTo(q.proj.sx, q.proj.sy); bctx.stroke();
    if(edge.synapses >= 100){
      const mx = (p.proj.sx+q.proj.sx)/2, my = (p.proj.sy+q.proj.sy)/2;
      text(bctx, `${edge.synapses}`, mx, my - 2, 7, '#d4f16b', 'center');
    }
  });

  // Cells with bounded radius; stagger labels to reduce collisions.
  const nodesSorted = points.slice().sort((a,b)=> b.proj.depth - a.proj.depth);
  const placedLabels = [];
  nodesSorted.forEach(({node, pos, proj: pr, nSamples}, drawIdx) => {
    const activity = node.rate || 0;
    const radius = Math.max(4, Math.min(14, 12 - pr.depth*3));
    const glow = bctx.createRadialGradient(pr.sx, pr.sy, 0, pr.sx, pr.sy, radius*2.2);
    glow.addColorStop(0, activity > 0.1 ? `rgba(212,241,107,${(0.3+activity*0.6).toFixed(2)})` : 'rgba(100,221,194,0.18)');
    glow.addColorStop(1, 'rgba(0,0,0,0)');
    bctx.fillStyle = glow;
    bctx.beginPath(); bctx.arc(pr.sx, pr.sy, radius*2.2, 0, Math.PI*2); bctx.fill();
    bctx.fillStyle = activity > 0.1 ? '#d4f16b' : '#64ddc2';
    bctx.beginPath(); bctx.arc(pr.sx, pr.sy, radius, 0, Math.PI*2); bctx.fill();
    bctx.strokeStyle = '#0a1013'; bctx.lineWidth = 1.5; bctx.stroke();
    // Compact single-line label: type and ROI inline. Nudge above or below if colliding with earlier labels.
    const sampledRoi = node.coord && path.edges.find(e=>e.post===node.body)?.primary_post_roi;
    const label = `${node.type}  ${sampledRoi || 'ROI N/A'}`;
    let ly = pr.sy - radius - 5;
    let dir = -1;
    while(placedLabels.some(L => Math.abs(L.y - ly) < 11 && Math.abs(L.x - pr.sx) < 60)){
      ly += dir * 12;
      dir = dir === -1 ? 1 : -1;
      if(Math.abs(ly - pr.sy) > radius + 60) break;
    }
    placedLabels.push({x: pr.sx, y: ly});
    text(bctx, label, pr.sx, ly, 8, '#f0f6e9', 'center');
  });

  // Captions placed BELOW the 47-px card header band so they stay visible.
  // Count retained partner-pair coordinate samples once per edge. Cell sample counts
  // include both pre- and post-synaptic endpoints, so summing them would double-count.
  const retainedPairs = path.edges.reduce((sum,edge)=>sum + (edge.synapse_coordinate_sample?.length||0), 0);
  const selectedRows = path.synapse_evidence?.selected_partner_rows || retainedPairs;
  const minSamples = Math.min(...points.map(p=>p.nSamples||0));
  const maxSamples = Math.max(...points.map(p=>p.nSamples||0));
  text(bctx, '3D WIRING · CELL POSITIONS = SAMPLED PATHWAY-SYNAPSE CENTROIDS', 14, 61, 9, '#d7e6d3');
  text(bctx, `${retainedPairs} OF ${selectedRows} PARTNER ROWS RETAINED · ${minSamples}-${maxSamples} SITE COORDINATES/CELL · X/Y/Z=NATIVE VOXEL AXES`, 14, 75, 7, '#8ea99a');
  text(bctx, 'EDGE WIDTH = REAL SYNAPSE COUNT · LIME = CHRONOS MODEL RATE ACTIVE · DRAG TO ROTATE', 14, 88, 7, '#748978');
  text(bctx, `yaw ${(brain3d.yaw*180/Math.PI).toFixed(0)}°  pitch ${(brain3d.pitch*180/Math.PI).toFixed(0)}°`, W-14, H-14, 7, '#607065', 'right');
}


function renderPlaced(data){
  const placed=data.world.sources.filter(source=>source.user_created);
  $('#placedStimuli').innerHTML=placed.length?placed.map(source=>`<button class="remove-stimulus" data-source-id="${source.id}">REMOVE ${source.label.toUpperCase()} / Z ${source.z.toFixed(2)} ×</button>`).join(''):'No user stimuli in meadow.';
  $('#clearStimuli').disabled=!placed.length;
  document.querySelectorAll('.remove-stimulus').forEach(button=>button.addEventListener('click',()=>update('remove',{id:button.dataset.sourceId})));
}

function renderPathway(pathway){
  $('#pathwayDrive').textContent=`MODELED MOTOR DRIVE ${pathway.motor_drive.toFixed(2)}`;
  const checks=Object.values(pathway.validation.checks).every(Boolean)?'STRUCTURAL CHECKS PASS':'CHECK FAILED';
  const synapseRows=pathway.synapse_evidence?.selected_partner_rows;
  $('#pathwayStatus').textContent=`Read left to right: the DM1 odor receptor leads through ${pathway.nodes.length} real MaleCNS neurons to the i1 VNC motor neuron. Every arrow is a directed connection backed by ${synapseRows??'locally selected'} individual partner rows; numbers are aggregate synapse counts. ${checks}; biological behavior validation is still pending.`;
  $('#pathwayEvidence').textContent=`Teal highlights and “model rate” are a bounded CHRONOS calculation—not measured firing. The live edge list shows official primary ROI and per-presynapse transmitter evidence. ${pathway.roi_status}`;
  const steps={'olfactory receptor':'1 · SMELL','projection neuron':'2 · RELAY','higher-order':'3 · CONTEXT','central complex':'4 · COMPASS','descending neuron':'5 · DESCEND','VNC motor neuron':'6 · MOVE'};
  $('#pathwayRows').innerHTML=pathway.nodes.map(node=>`<div class="path-node ${node.rate>.002?'active':''}"><span class="path-step">${steps[node.stage]||'ROUTE'}</span><b>${node.type}</b><span>REAL CELL ${node.body}</span><span>${node.predicted_nt} prediction ${Math.round(node.nt_confidence*100)}%</span><em>MODEL RATE ${node.rate.toFixed(2)}</em></div>`).join('');
}


function drawBlock(data){
  const r=fit(worldCanvas,wctx),W=r.width,H=r.height; wctx.clearRect(0,0,W,H);
  const sky=wctx.createLinearGradient(0,0,0,H); sky.addColorStop(0,'#0a1013'); sky.addColorStop(.6,'#152521'); sky.addColorStop(1,'#1f3828'); wctx.fillStyle=sky; wctx.fillRect(0,0,W,H);
  // Faint ground plane and biome plates for context (not actual-tick state).
  const corners=[[0,0],[WORLD_SPAN,0],[WORLD_SPAN,WORLD_SPAN],[0,WORLD_SPAN]].map(p=>project(W,H,p[0],p[1],0));
  wctx.fillStyle='#1b2d20'; wctx.beginPath(); corners.forEach(([x,y],i)=>i?wctx.lineTo(x,y):wctx.moveTo(x,y)); wctx.closePath(); wctx.fill();
  wctx.strokeStyle='rgba(212,241,107,.14)'; wctx.lineWidth=1; wctx.stroke();
  data.world.biomes.forEach(b=>{ const zone=[[b.x,b.y],[b.x+b.w,b.y],[b.x+b.w,b.y+b.h],[b.x,b.y+b.h]].map(p=>project(W,H,p[0],p[1],0)); wctx.fillStyle=b.color+'33'; wctx.beginPath(); zone.forEach(([x,y],i)=>i?wctx.lineTo(x,y):wctx.moveTo(x,y)); wctx.closePath(); wctx.fill(); });
  for(let q=1;q<WORLD_SPAN;q++){ wctx.strokeStyle='rgba(212,241,107,.07)'; wctx.lineWidth=1; [[q,0,q,WORLD_SPAN],[0,q,WORLD_SPAN,q]].forEach(([a,b,c,d])=>{ const p=project(W,H,a,b),e=project(W,H,c,d); wctx.beginPath(); wctx.moveTo(...p); wctx.lineTo(...e); wctx.stroke(); }); }
  const home=data.world.home, homeP=project(W,H,home[0],home[1],0);
  wctx.strokeStyle='rgba(218,244,126,.3)'; wctx.setLineDash([4,5]); wctx.beginPath(); wctx.ellipse(homeP[0],homeP[1],23,9,0,0,Math.PI*2); wctx.stroke(); wctx.setLineDash([]);
  if(!worldlineData||!worldlineData.history||!worldlineData.history.length){
    text(wctx,'RECORDING WORLDLINE…',W*.5,H*.5-10,16,'#d4f16b','center');
    text(wctx,'BLOCK-FRAME SHOWS THE FLY ACROSS ALL RECORDED TICKS AT ONCE',W*.5,H*.5+14,9,'#8ea99a','center');
    text(wctx,'SWITCH TO WORLD, WAIT 10-20 SECONDS, THEN COME BACK HERE',W*.5,H*.5+30,9,'#8ea99a','center');
    text(wctx,'TRY: TOGGLE  SILENCE COMPASS  WHILE RUNNING — LESIONED SEGMENTS WILL TURN RED HERE',W*.5,H*.5+50,8,'#d4f16b','center');
    text(wctx,'HHMI JANELIA MALECNS DRIVES THE SIMULATION · THE WORLDLINE IS A CHRONOS RECORDING',18,H-39,8,'#8ea99a');
    return;
  }
  const hist=worldlineData.history;
  const cursorIdx=Math.max(0,Math.min(hist.length-1,Math.floor(timeCursor*(hist.length-1))));
  // Worldline polyline, colored by time (dim-old to bright-new); lesion segments use red.
  for(let i=1;i<hist.length;i++){
    const prev=hist[i-1],cur=hist[i];
    const p=project(W,H,prev.x,prev.y,prev.z), q=project(W,H,cur.x,cur.y,cur.z);
    const t=i/(hist.length-1), past=i<=cursorIdx;
    const alpha=past?(0.22+0.70*t):0.10;
    const base=cur.compass?'212,241,107':'255,113,102';
    wctx.strokeStyle=`rgba(${base},${alpha.toFixed(2)})`;
    wctx.lineWidth=past?Math.max(1.5,1+cur.speed*4):1;
    wctx.beginPath(); wctx.moveTo(...p); wctx.lineTo(...q); wctx.stroke();
    // Vertical altitude "shadow" to ground every few ticks to make Z visible.
    if((cur.z||0)>.07 && i%5===0 && past){
      const g=project(W,H,cur.x,cur.y,0);
      wctx.strokeStyle=`rgba(${base},${(alpha*0.35).toFixed(2)})`; wctx.lineWidth=1;
      wctx.beginPath(); wctx.moveTo(...q); wctx.lineTo(...g); wctx.stroke();
    }
  }
  // Pivot markers.
  (worldlineData.pivots||[]).forEach(piv=>{
    const match=hist.find(h=>h.tick===piv.tick)||hist[0];
    if(!match) return;
    const [px,py]=project(W,H,match.x,match.y,match.z);
    const colors={lesion:'#ff7166',stimulus:'#ffbe58',move_fly:'#b28af4',remove:'#8ea99a',clear:'#8ea99a'};
    const c=colors[piv.kind]||'#d4f16b';
    wctx.strokeStyle=c; wctx.lineWidth=1.5;
    wctx.beginPath(); wctx.arc(px,py,6,0,Math.PI*2); wctx.stroke();
    text(wctx,piv.kind.toUpperCase().replace('_',' '),px,py+17,7,c,'center');
  });
  // Counterfactual branches overlay (seeds 1..N → distinct hues).
  if(branchData && branchData.branches){
    const palette=['#64ddc2','#b28af4','#ffbe58','#ff79c6'];  // teal / violet / amber / pink (null wiring)
    branchData.branches.forEach((br,idx)=>{
      const col=palette[idx]||'#8ea99a';
      const traj=br.trajectory;
      wctx.strokeStyle=col+'cc'; wctx.lineWidth=1.6;
      wctx.beginPath();
      traj.forEach((pt,i)=>{ const [px,py]=project(W,H,pt.x,pt.y,pt.z); if(i===0) wctx.moveTo(px,py); else wctx.lineTo(px,py); });
      wctx.stroke();
      if(traj.length){
        const last=traj[traj.length-1], [ex,ey]=project(W,H,last.x,last.y,last.z);
        wctx.fillStyle=col; wctx.beginPath(); wctx.arc(ex,ey,4,0,Math.PI*2); wctx.fill();
        const label=(br.scenario||('seed '+br.seed)).toUpperCase().replace('_',' ');
        text(wctx,label,ex+8,ey+3,7,col);
      }
    });
  }
  // Cursor ghost fly at the selected tick.
  const cur=hist[cursorIdx];
  const [cx,cy]=project(W,H,cur.x,cur.y,cur.z);
  wctx.save(); wctx.translate(cx,cy); wctx.rotate(cur.heading+Math.PI/2);
  wctx.fillStyle='rgba(240,255,242,.9)'; wctx.beginPath(); wctx.ellipse(0,2,6,12,0,0,Math.PI*2); wctx.fill();
  wctx.restore();
  wctx.strokeStyle='#d4f16b'; wctx.lineWidth=2; wctx.beginPath(); wctx.arc(cx,cy,16,0,Math.PI*2); wctx.stroke();
  text(wctx,`TICK ${cur.tick} · Z ${cur.z.toFixed(2)} · ${cur.mode.toUpperCase()}`,cx,cy-24,8,'#d4f16b','center');
  text(wctx,`BLOCK-FRAME · ${hist.length} TICKS · ${(worldlineData.pivots||[]).length} PIVOTS · CURSOR @ ${Math.round(timeCursor*100)}%`,18,H-55,9,'#d4f16b');
  text(wctx,'WORLDLINE RECORDED FROM A REAL BOUNDED MALECNS CIRCUIT · BEHAVIOR DYNAMICS ARE A CHRONOS MODEL',18,H-39,8,'#8ea99a');
}

function drawFly(data){
  const r=fit(worldCanvas,wctx),W=r.width,H=r.height; wctx.clearRect(0,0,W,H);
  wctx.fillStyle='#060a08'; wctx.fillRect(0,0,W,H);
  const f=data.fly, [fx,fy]=project(W,H,f.x,f.y,f.z);
  const horizonPx=FLY_HORIZON/WORLD_SPAN*W*0.566*camera.zoom;
  // Faded ghost of source positions BEYOND the fly's reach — makes the darkness read as "hidden from the fly" instead of "empty canvas". Dots are intentionally tiny and dim.
  (data.world.sources||[]).forEach(s=>{
    const [sx,sy]=project(W,H,s.x,s.y,s.z||0);
    const dx=sx-fx, dy=sy-fy, d=Math.hypot(dx,dy);
    if(d>horizonPx){
      wctx.fillStyle='rgba(142,169,154,.22)';
      wctx.beginPath(); wctx.arc(sx,sy,2,0,Math.PI*2); wctx.fill();
    }
  });
  // Everything inside the horizon.
  wctx.save(); wctx.beginPath(); wctx.arc(fx,fy,horizonPx,0,Math.PI*2); wctx.clip();
  const corners=[[0,0],[WORLD_SPAN,0],[WORLD_SPAN,WORLD_SPAN],[0,WORLD_SPAN]].map(p=>project(W,H,p[0],p[1],0));
  wctx.fillStyle='#1a2b1e'; wctx.beginPath(); corners.forEach(([x,y],i)=>i?wctx.lineTo(x,y):wctx.moveTo(x,y)); wctx.closePath(); wctx.fill();
  const dm1=data.senses.dm1||0, va2=data.senses.va2||0;
  // Opacity ramps from 0.22 at threshold to 0.65 at saturation so a modest 0.1 signal is actually visible.
  if(dm1>.015){ const op=Math.min(.65,.22+.9*dm1); for(let i=4;i>0;i--) ellipse(wctx,fx-horizonPx*.18,fy,26+i*18*dm1,13+i*11*dm1,`rgba(255,190,88,${(op/i*.75).toFixed(3)})`); }
  if(va2>.015){ const op=Math.min(.65,.22+.9*va2); for(let i=4;i>0;i--) ellipse(wctx,fx+horizonPx*.18,fy,26+i*18*va2,13+i*11*va2,`rgba(178,138,244,${(op/i*.75).toFixed(3)})`); }
  const [wx,wy]=data.senses.airflow||[0,0,0];
  for(let i=0;i<8;i++){
    const ang=(i/8)*Math.PI*2, r1=horizonPx*.45;
    const x0=fx+Math.cos(ang)*r1, y0=fy+Math.sin(ang)*r1;
    wctx.strokeStyle='rgba(231,251,229,.35)'; wctx.lineWidth=1;
    wctx.beginPath(); wctx.moveTo(x0,y0); wctx.lineTo(x0+wx*60,y0+wy*60); wctx.stroke();
  }
  if((data.needs.fear||0)>.3){
    const grd=wctx.createRadialGradient(fx,fy,horizonPx*.2,fx,fy,horizonPx);
    grd.addColorStop(0,'rgba(255,113,102,0)'); grd.addColorStop(1,`rgba(255,113,102,${(data.needs.fear*0.6).toFixed(2)})`);
    wctx.fillStyle=grd; wctx.beginPath(); wctx.arc(fx,fy,horizonPx,0,Math.PI*2); wctx.fill();
  }
  wctx.restore();
  // Horizon ring + fly marker with glow + heading line.
  wctx.strokeStyle='rgba(212,241,107,.45)'; wctx.setLineDash([4,4]);
  wctx.beginPath(); wctx.arc(fx,fy,horizonPx,0,Math.PI*2); wctx.stroke(); wctx.setLineDash([]);
  const glow=wctx.createRadialGradient(fx,fy,0,fx,fy,16);
  glow.addColorStop(0,'rgba(212,241,107,.75)'); glow.addColorStop(1,'rgba(212,241,107,0)');
  wctx.fillStyle=glow; wctx.beginPath(); wctx.arc(fx,fy,16,0,Math.PI*2); wctx.fill();
  wctx.save(); wctx.translate(fx,fy); wctx.rotate(f.heading+Math.PI/2);
  wctx.fillStyle='#d4f16b'; wctx.beginPath(); wctx.arc(0,-3,4,0,Math.PI*2); wctx.fill();
  wctx.strokeStyle='#d4f16b'; wctx.lineWidth=1.5;
  wctx.beginPath(); wctx.moveTo(0,-3); wctx.lineTo(0,-horizonPx*.4); wctx.stroke();
  wctx.restore();
  // Static ambient hints so the dark reads as INTENTIONAL, not broken.
  text(wctx,'EVERYTHING OUTSIDE THE CIRCLE IS HIDDEN FROM THE FLY',W*.5,70,10,'#8ea99a','center');
  text(wctx,'SWITCH TO WORLD VIEW TO PLACE A STIMULUS NEAR THE FLY — OR CLICK GUIDED DEMO',W*.5,86,8,'#607065','center');
  // Context-sensitive center hint — only when nothing is being sensed.
  const sensingAnything = dm1>.02 || va2>.02 || Math.abs(wx)>.08 || Math.abs(wy)>.08 || (data.needs.fear||0)>.1;
  if(!sensingAnything){
    text(wctx,'NO SIGNAL IN RANGE',fx,fy+horizonPx+22,10,'#d4f16b','center');
    text(wctx,'DRAG A NECTAR/YEAST/WATER CLOSER THAN 0.9 WORLD UNITS',fx,fy+horizonPx+36,8,'#8ea99a','center');
  }
  // Caption pinned to the bottom.
  text(wctx,`FLY-FRAME · SENSORY HORIZON ${FLY_HORIZON.toFixed(1)} WORLD UNITS · THE 12-CELL PATHWAY IS THE FLY'S SIGHT`,18,H-55,9,'#d4f16b');
  text(wctx,'FIRST-PERSON PROJECTION OF CHRONOS SENSORY MODEL · NO CLAIM OF SUBJECTIVE EXPERIENCE',18,H-39,8,'#8ea99a');
}

function render(data){
  latest=data;drawWorld(data);drawBrain(data);renderPlaced(data);renderPathway(data.pathway);
  const degrees=((camera.yaw*180/Math.PI)%360+360)%360;$('#viewReadout').textContent=`${Math.round(degrees)}° / ${camera.zoom.toFixed(1)}×`;$('#followView').classList.toggle('active',camera.follow);$('#followView').textContent=camera.follow?'FOLLOWING':'FOLLOW';
  $('#connection').textContent='LIVE LOCAL WORLD';$('#goal').textContent=data.goal.toUpperCase();$('#event').textContent=data.event;$('#circuitBadge').textContent=`${data.pathway.nodes.length} REAL CELLS / ${data.pathway.edges.length} EDGES`;
  ['hunger','thirst','fatigue','fear'].forEach(k=>{const v=data.needs[k];$('#'+k).textContent=`${Math.round(v*100)}%`;const bar=$(`[data-need="${k}"] em`);bar.style.width=`${v*100}%`;bar.style.background=k==='fear'?'#ff7166':k==='thirst'?'#66c9ff':'#789a4f'});
  $('#dm1').textContent=data.senses.dm1.toFixed(2);$('#va2').textContent=data.senses.va2.toFixed(2);$('#optic').textContent=data.senses.optic_flow.toFixed(2);$('#altitude').textContent=data.senses.altitude.toFixed(2);$('#airflow').textContent=data.senses.airflow.map(v=>v.toFixed(2)).join(', ');$('#home').textContent=data.senses.home_vector.join(', ');$('#flightmode').textContent=data.interaction.active?`${data.interaction.mode.toUpperCase()} ${Math.round(data.interaction.progress*100)}% • ${data.interaction.remaining.toFixed(1)}s`:`${data.flight.mode.toUpperCase()} → Z ${data.flight.target_z.toFixed(2)}`;
  $('#pause').textContent=data.running?'PAUSE WORLD':'RESUME WORLD';$('#lesion').textContent=data.compass_enabled?'SILENCE COMPASS':'RESTORE COMPASS';$('#modelNote').textContent=`${data.model_note} Current behavior: ${data.behavior}.`;$('#dataFoot').textContent=`${data.data.dataset.toUpperCase()} • ${data.data.synapse_table_count} SYNAPSE TABLES VERIFIED • ${data.data.selected_partner_rows} PATHWAY ROWS • ${data.data.gpu_vram_mb} MB VRAM`;
  const palette={olfactory:'#ffbe58',compass:'#b28af4',verified_pathway:'#64ddc2'};$('#edgeRows').innerHTML=[...data.active_edges].sort((a,b)=>b.activity-a.activity).slice(0,8).map(e=>`<div class="edge-row"><i class="kind" style="background:${palette[e.module]}"></i><div><b>${e.pre_type} → ${e.post_type}</b><span>${e.neuropil==='not included'?'MaleCNS flat weight':`${e.neuropil} / ${e.neurotransmitter}`} / actual weight ${e.synapses} synapses</span></div><strong>${e.activity.toFixed(1)}</strong></div>`).join('');
}
async function update(action='',params={}){if(busy)return;busy=true;try{const q=new URLSearchParams(params);if(action)q.set('action',action);const r=await fetch('/api/world'+(q.size?`?${q}`:''));const data=await r.json();if(currentFrame==='block'){try{const wl=await fetch('/api/worldline');worldlineData=await wl.json()}catch(_){}}render(data)}catch(e){$('#connection').textContent='LOCAL SERVER OFFLINE'}finally{busy=false}}
['pause','lesion','reset'].forEach(id=>$('#'+id).addEventListener('click',()=>update(id)));
document.querySelectorAll('[data-need]').forEach(b=>b.addEventListener('click',()=>update(b.dataset.need)));
$('#clearStimuli').addEventListener('click',()=>update('clear_stimuli'));
document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{const action=button.dataset.view;if(action==='orbit-left')camera.yaw-=Math.PI/12;else if(action==='orbit-right')camera.yaw+=Math.PI/12;else if(action==='tilt-up')camera.pitch=Math.min(1.14,camera.pitch+.09);else if(action==='tilt-down')camera.pitch=Math.max(.38,camera.pitch-.09);else if(action==='zoom-in')camera.zoom=Math.min(1.8,camera.zoom+.12);else if(action==='zoom-out')camera.zoom=Math.max(.62,camera.zoom-.12);else if(action==='follow')camera.follow=!camera.follow;else if(action==='reset'){camera.yaw=Math.PI/4;camera.pitch=.78;camera.zoom=1;camera.follow=false}refreshView()}));
document.querySelectorAll('[data-stimulus]').forEach(button=>button.addEventListener('dragstart',event=>{event.dataTransfer.setData('text/plain',button.dataset.stimulus);event.dataTransfer.effectAllowed='copy'}));
const dropHeight=$('#dropHeight'),dropHeightReadout=$('#dropHeightReadout');
function renderDropHeight(){const z=Number(dropHeight.value),layer=z<.08?'GROUND':z<.32?'LOW FLIGHT':'CANOPY / HIGH';dropHeightReadout.textContent=`${layer} / Z ${z.toFixed(2)}`}
dropHeight.addEventListener('input',renderDropHeight);renderDropHeight();
worldCanvas.addEventListener('dragover',event=>{event.preventDefault();event.dataTransfer.dropEffect='copy';worldCanvas.closest('.world-card').classList.add('dragging')});
worldCanvas.addEventListener('dragleave',()=>worldCanvas.closest('.world-card').classList.remove('dragging'));
let orbitDrag=null;
worldCanvas.addEventListener('pointerdown',event=>{if(event.button!==0)return;orbitDrag={x:event.clientX,y:event.clientY};worldCanvas.setPointerCapture(event.pointerId)});
worldCanvas.addEventListener('pointermove',event=>{if(!orbitDrag)return;camera.yaw+=(event.clientX-orbitDrag.x)*.008;camera.pitch=Math.max(.38,Math.min(1.14,camera.pitch-(event.clientY-orbitDrag.y)*.003));orbitDrag={x:event.clientX,y:event.clientY};refreshView()});
worldCanvas.addEventListener('pointerup',()=>{orbitDrag=null});
worldCanvas.addEventListener('drop',event=>{event.preventDefault();worldCanvas.closest('.world-card').classList.remove('dragging');const kind=event.dataTransfer.getData('text/plain'),rect=worldCanvas.getBoundingClientRect(),point=groundPoint(rect,event.clientX,event.clientY),z=Number(dropHeight.value).toFixed(3);if(kind==='fly')update('move_fly',{x:point.x.toFixed(3),y:point.y.toFixed(3),z});else if(kind)update('stimulus',{kind,x:point.x.toFixed(3),y:point.y.toFixed(3),z})});
setInterval(()=>update(),120);update();

document.querySelectorAll('[data-frame]').forEach(button=>button.addEventListener('click',()=>{
  currentFrame=button.dataset.frame;
  document.querySelectorAll('[data-frame]').forEach(b=>b.classList.toggle('active',b===button));
  const scrubber=document.querySelector('.block-scrubber'); if(scrubber) scrubber.hidden=currentFrame!=='block';
  if(currentFrame==='block'){ fetch('/api/worldline').then(r=>r.json()).then(d=>{worldlineData=d;if(latest)drawWorld(latest)}).catch(()=>{}); }
  else if(latest) drawWorld(latest);
}));
const timeCursorEl=$('#timeCursor');
if(timeCursorEl){
  timeCursorEl.addEventListener('input',()=>{
    timeCursor=Number(timeCursorEl.value);
    $('#timeCursorReadout').textContent=timeCursor>=.999?'LIVE EDGE':`T ${Math.round(timeCursor*100)}%`;
    if(latest&&currentFrame==='block') drawBlock(latest);
  });
}

const branchBtn=$('#branchBtn'), clearBranchBtn=$('#clearBranchBtn');
if(branchBtn){
  branchBtn.addEventListener('click',()=>{
    if(branchBtn.disabled)return;
    branchBtn.disabled=true; branchBtn.textContent='BRANCHING…';
    fetch('/api/branches?seeds=1,2,3,4&steps=120').then(r=>r.json()).then(d=>{
      branchData=d; branchBtn.textContent='BRANCH ×4'; branchBtn.disabled=false;
      if(clearBranchBtn) clearBranchBtn.hidden=false;
      if(latest&&currentFrame==='block') drawBlock(latest);
    }).catch(()=>{ branchBtn.textContent='BRANCH FAILED'; branchBtn.disabled=false; setTimeout(()=>branchBtn.textContent='BRANCH ×4',1500); });
  });
}
if(clearBranchBtn){
  clearBranchBtn.addEventListener('click',()=>{
    branchData=null; clearBranchBtn.hidden=true;
    if(latest&&currentFrame==='block') drawBlock(latest);
  });
}

// Guided demo: one click runs every feature in order so the viewer doesn't have to remember steps.
let demoRunning = false;
async function runGuidedDemo(){
  if(demoRunning) return;
  demoRunning = true;
  const btn = $('#guidedDemo'); if(!btn) { demoRunning=false; return; }
  const originalText = btn.textContent;
  btn.classList.add('running'); btn.disabled = true;
  const setMsg = (m)=>{ btn.textContent = m; };
  const switchTo = (name)=>{ const b=document.querySelector(`[data-frame="${name}"]`); if(b) b.click(); };
  const sleep = (ms)=>new Promise(r=>setTimeout(r,ms));
  const safeUpdate = async(a,p)=>{ for(let i=0;i<20;i++){ if(!busy){ await update(a,p); return; } await sleep(80); } };
  try{
    setMsg('STEP 1/6 · RESETTING WORLD');
    switchTo('world'); await safeUpdate('reset'); await sleep(1400);
    if(latest){
      const nx = Math.max(.5, Math.min(9.5, latest.fly.x + 0.5));
      const ny = latest.fly.y;
      setMsg('STEP 2/6 · NECTAR BESIDE THE FLY');
      await safeUpdate('stimulus',{kind:'dm1', x:nx.toFixed(3), y:ny.toFixed(3), z:'0.000'});
      await sleep(2200);
    }
    setMsg('STEP 3/6 · FLY VIEW · ORANGE PLUME IN THE CIRCLE');
    switchTo('fly'); await sleep(6000);
    setMsg('STEP 4/6 · BLOCK VIEW · WORLDLINE SO FAR');
    switchTo('block'); await sleep(3500);
    setMsg('STEP 5/6 · LESION · NEW SEGMENTS TURN RED');
    await safeUpdate('lesion'); await sleep(6000);
    setMsg('STEP 6/6 · FOUR COUNTERFACTUAL FUTURES');
    $('#branchBtn')?.click(); await sleep(6000);
    setMsg('DEMO COMPLETE · EXPLORE FREELY');
    await sleep(2500);
  } finally {
    btn.textContent = originalText;
    btn.classList.remove('running');
    btn.disabled = false;
    demoRunning = false;
  }
}
$('#guidedDemo')?.addEventListener('click', runGuidedDemo);

// Welcome overlay — shown on first load only, dismissible, re-openable with ? or the help button.
const welcomeEl = $('#welcome');
function showWelcome(){ if(welcomeEl){ welcomeEl.hidden = false; } }
function hideWelcome(){ if(welcomeEl){ welcomeEl.hidden = true; } }
function persistDismissIfChecked(){ try{ if($('#welcomeDismiss')?.checked) localStorage.setItem('chronos.welcome.dismissed','1'); }catch(_){} }
if(welcomeEl){
  let dismissed = false;
  try { dismissed = localStorage.getItem('chronos.welcome.dismissed') === '1'; } catch(_){}
  if(!dismissed) setTimeout(showWelcome, 450);
}
$('#welcomeDemo')?.addEventListener('click', ()=>{ hideWelcome(); persistDismissIfChecked(); runGuidedDemo(); });
$('#welcomeExplore')?.addEventListener('click', ()=>{ hideWelcome(); persistDismissIfChecked(); });
$('#helpBtn')?.addEventListener('click', showWelcome);

// Keyboard shortcuts — safe (ignored while typing in an input/textarea).
document.addEventListener('keydown', (e)=>{
  const tag = (e.target && e.target.tagName) || '';
  if(tag === 'INPUT' || tag === 'TEXTAREA') return;
  const k = e.key.toLowerCase();
  if(k === 'escape'){ hideWelcome(); return; }
  if(k === '?' || (e.shiftKey && e.key === '/')) { showWelcome(); return; }
  if(welcomeEl && !welcomeEl.hidden) return; // don't trigger shortcuts under the modal
  if(k === 'w') document.querySelector('[data-frame="world"]')?.click();
  else if(k === 'f') document.querySelector('[data-frame="fly"]')?.click();
  else if(k === 'b') document.querySelector('[data-frame="block"]')?.click();
  else if(k === 'g') $('#guidedDemo')?.click();
  else if(k === 'l') $('#lesion')?.click();
  else if(k === 'p') $('#pause')?.click();
  else if(k === 'r') $('#reset')?.click();
});

// Click-any-neuron inspection — turn each brain group card into a MaleCNS lookup.
const neuronModal = $('#neuronModal'), neuronContent = $('#neuronContent');
function showNeuronModal(group, path){
  const cells = group.nodes.map(i => path.nodes[i]);
  const touchingEdges = path.edges.filter(e => group.nodes.some(i => path.nodes[i].body === e.pre || path.nodes[i].body === e.post));
  const edgeRows = touchingEdges.map(e => `<li><b>${e.pre_type}</b> → <b>${e.post_type}</b> · ${e.synapses} synapses · ${e.roi_status||'ROI n/a'}${e.tbar_dominant_prediction ? ' · '+e.tbar_dominant_prediction : ''}</li>`).join('');
  const cellRows = cells.map(c => `<li>
    <b>${c.type}</b>
    <span>MaleCNS body ID · ${c.body}</span>
    <span>Predicted neurotransmitter · ${c.predicted_nt||'n/a'}${c.nt_confidence!=null ? ' ('+Math.round(c.nt_confidence*100)+'% conf.)' : ''}</span>
    <span>Live rate · ${(c.rate||0).toFixed(3)}</span>
    <span>Functional stage · ${c.stage||'n/a'}</span>
  </li>`).join('');
  neuronContent.innerHTML = `
    <h3>${group.label} · ${group.meaning}</h3>
    <p class="neuron-meaning">MaleCNS supplies the cell IDs, types, weights, ROIs, coordinates, and transmitter predictions. Functional stage and Live rate are CHRONOS model values.</p>
    <h4>CELLS IN THIS GROUP (${cells.length})</h4>
    <ul class="neuron-list">${cellRows}</ul>
    <h4>EDGES TOUCHING THIS GROUP (${touchingEdges.length})</h4>
    <ul class="neuron-edges">${edgeRows || '<li>No edges in the verified pathway touch this group.</li>'}</ul>
    <p class="neuron-hint">Click outside this card or press Esc to close.</p>
  `;
  neuronModal.hidden = false;
}
function hideNeuronModal(){ if(neuronModal) neuronModal.hidden = true; }
$('#neuronClose')?.addEventListener('click', hideNeuronModal);
neuronModal?.addEventListener('click', (e)=>{ if(e.target === neuronModal) hideNeuronModal(); });
let brainPointer = null;
brainCanvas?.addEventListener('pointerdown', (e)=>{
  brainPointer = { x:e.clientX, y:e.clientY, startX:e.clientX, startY:e.clientY, moved:false };
  try{ brainCanvas.setPointerCapture(e.pointerId); }catch(_){}
});
brainCanvas?.addEventListener('pointermove', (e)=>{
  if(!brainPointer) return;
  const dx = e.clientX - brainPointer.x, dy = e.clientY - brainPointer.y;
  if(Math.hypot(e.clientX-brainPointer.startX, e.clientY-brainPointer.startY) > 4) brainPointer.moved = true;
  if(brainMode === 'wiring3d' && brainPointer.moved){
    brain3d.yaw += dx * 0.01;
    brain3d.pitch = Math.max(-1.2, Math.min(1.2, brain3d.pitch + dy * 0.01));
    if(latest) drawBrain(latest);
  }
  brainPointer.x = e.clientX; brainPointer.y = e.clientY;
});
brainCanvas?.addEventListener('pointerup', (e)=>{
  const wasDrag = brainPointer && brainPointer.moved;
  brainPointer = null;
  if(wasDrag) return;
  // Click (no drag) in schematic mode → open the clicked group card
  if(brainMode !== 'schematic' || !latest || !brainGroupsHit.length) return;
  const r = brainCanvas.getBoundingClientRect();
  const scaleY = brainCanvas.height / (devicePixelRatio||1) / r.height;
  const yCss = e.clientY - r.top;
  const yCanvas = yCss * scaleY;
  const hit = brainGroupsHit.find(h => yCanvas >= h.y && yCanvas <= h.y + h.cardH);
  if(hit) showNeuronModal(hit.group, latest.pathway);
});
document.querySelectorAll('[data-brain-mode]').forEach(btn => btn.addEventListener('click', ()=>{
  brainMode = btn.dataset.brainMode;
  document.querySelectorAll('[data-brain-mode]').forEach(b => b.classList.toggle('active', b===btn));
  brainCanvas?.closest('.brain-card')?.classList.toggle('wiring3d', brainMode === 'wiring3d');
  if(latest) drawBrain(latest);
}));
// Esc closes neuron modal too
document.addEventListener('keydown',(e)=>{ if(e.key==='Escape' && neuronModal && !neuronModal.hidden) hideNeuronModal(); });
