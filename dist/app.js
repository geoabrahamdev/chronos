const canvas = document.querySelector('#world');
const ctx = canvas.getContext('2d');
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const state = {
  running: true,
  scenario: 'forage',
  amber: 78,
  violet: 41,
  wind: 12,
  compass: true,
  time: 0,
  fly: { x: .48, y: .72, heading: -1.45, trail: [], phase: 0 },
  home: { x: .48, y: .75 },
  connectome: null,
};

function resize() {
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = rect.width * ratio;
  canvas.height = rect.height * ratio;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
}
window.addEventListener('resize', resize);
resize();

function sourcePositions(w, h) {
  if (state.scenario === 'compass') return {
    amber: { x: .51 * w, y: .18 * h, color: '#ffbe5b', name: 'HOME' },
    violet: { x: .78 * w, y: .42 * h, color: '#8978e6', name: 'DISTRACTOR' },
  };
  return {
    amber: { x: .27 * w, y: .18 * h, color: '#ffbe5b', name: 'NECTAR' },
    violet: { x: .75 * w, y: .20 * h, color: '#8978e6', name: 'YEAST' },
  };
}

function plume(x, y, strength, color, w, h, seed) {
  const g = ctx.createRadialGradient(x, y, 0, x, y + h * .24, Math.max(w, h) * .48);
  g.addColorStop(0, `#${color}${Math.round(80 * strength).toString(16).padStart(2, '0')}`);
  g.addColorStop(.18, `#${color}${Math.round(35 * strength).toString(16).padStart(2, '0')}`);
  g.addColorStop(1, `#${color}00`);
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.ellipse(x + Math.sin(state.time * .7 + seed) * 5, y + h * .11, w * .30, h * .38, -.2, 0, Math.PI * 2);
  ctx.fill();
  for (let i = 0; i < 24; i++) {
    const px = x + Math.sin(i * 12.9 + seed) * (i * 9) + Math.sin(state.time + i) * 10;
    const py = y + i * (h * .018) + Math.cos(state.time * 1.5 + i) * 7;
    const alpha = Math.max(0, 0.42 - i / 70) * strength;
    ctx.fillStyle = `#${color}${Math.round(alpha * 255).toString(16).padStart(2, '0')}`;
    ctx.beginPath(); ctx.arc(px, py, 1.3 + (i % 3), 0, Math.PI * 2); ctx.fill();
  }
}

function drawSource(source, value) {
  ctx.save();
  ctx.shadowColor = source.color; ctx.shadowBlur = 18;
  ctx.fillStyle = source.color;
  ctx.beginPath(); ctx.arc(source.x, source.y, 8 + value * 6, 0, Math.PI * 2); ctx.fill();
  ctx.shadowBlur = 0;
  ctx.fillStyle = '#e8e3d9'; ctx.font = '10px DM Mono'; ctx.textAlign = 'center';
  ctx.fillText(source.name, source.x, source.y - 19);
  ctx.restore();
}

function drawWind(w, h) {
  ctx.save(); ctx.strokeStyle = 'rgba(193,209,214,.22)'; ctx.lineWidth = 1;
  const drift = (state.time * state.wind * 3) % 45;
  for (let y = 110; y < h - 25; y += 46) {
    for (let x = -30 + drift; x < w; x += 85) {
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + 28, y); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(x + 28, y); ctx.lineTo(x + 23, y - 3); ctx.lineTo(x + 23, y + 3); ctx.closePath(); ctx.fillStyle = 'rgba(193,209,214,.22)'; ctx.fill();
    }
  }
  ctx.restore();
}

function drawTrail(fly) {
  if (fly.trail.length < 2) return;
  ctx.save(); ctx.lineWidth = 1.4; ctx.strokeStyle = state.compass ? 'rgba(203,239,107,.32)' : 'rgba(255,117,99,.42)';
  ctx.beginPath(); fly.trail.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)); ctx.stroke(); ctx.restore();
}

function drawFly(fly) {
  const x = fly.x * canvas.clientWidth, y = fly.y * canvas.clientHeight;
  ctx.save(); ctx.translate(x, y); ctx.rotate(fly.heading + Math.PI / 2);
  ctx.shadowColor = '#c9ef6b'; ctx.shadowBlur = 14;
  ctx.fillStyle = '#c9ef6b';
  ctx.beginPath(); ctx.ellipse(0, 1, 5, 10, 0, 0, Math.PI * 2); ctx.fill();
  ctx.shadowBlur = 0; ctx.fillStyle = 'rgba(220,239,218,.65)';
  ctx.beginPath(); ctx.ellipse(-7, 0, 8, 3, -.5, 0, Math.PI*2); ctx.ellipse(7, 0, 8, 3, .5, 0, Math.PI*2); ctx.fill();
  ctx.fillStyle = '#f8f5eb'; ctx.beginPath(); ctx.arc(0, -8, 3.2, 0, Math.PI*2); ctx.fill();
  ctx.restore();
}

function updateFly(dt) {
  const w = canvas.clientWidth, h = canvas.clientHeight, src = sourcePositions(w, h);
  const fly = state.fly; const p = { x: fly.x * w, y: fly.y * h };
  let target;
  if (state.scenario === 'compass' || state.scenario === 'lesion') target = src.amber;
  else target = state.amber >= state.violet ? src.amber : src.violet;
  const dx = target.x - p.x, dy = target.y - p.y;
  const desired = Math.atan2(dy, dx);
  const casting = Math.sin(state.time * 2.1) * .58;
  const broken = !state.compass || state.scenario === 'lesion';
  const chaos = broken ? Math.sin(state.time * 2.7) * 1.5 + Math.cos(state.time * 1.1) * .8 : casting;
  const goal = desired + chaos;
  let difference = Math.atan2(Math.sin(goal - fly.heading), Math.cos(goal - fly.heading));
  fly.heading += difference * dt * (broken ? 0.58 : 1.7);
  const distance = Math.hypot(dx, dy);
  const velocity = distance < 30 ? 0 : (broken ? .072 : .095) * dt * (state.wind / 12);
  fly.x += Math.cos(fly.heading) * velocity;
  fly.y += Math.sin(fly.heading) * velocity;
  fly.x = Math.max(.05, Math.min(.95, fly.x)); fly.y = Math.max(.18, Math.min(.92, fly.y));
  fly.phase += dt;
  if (fly.trail.length === 0 || Math.hypot(fly.trail.at(-1).x - fly.x*w, fly.trail.at(-1).y - fly.y*h) > 2.4) fly.trail.push({x:fly.x*w,y:fly.y*h});
  if (fly.trail.length > 140) fly.trail.shift();
}

function renderConnectome(data) {
  state.connectome = data;
  $('#datasetStatus').textContent = data.dataset.toUpperCase();
  $('#datasetCount').textContent = `${data.member_count} CELLS`;
  $('#statusText').textContent = 'LOCAL FLYWIRE DATA READY';
  $('#edgeList').innerHTML = data.edges.slice(0, 4).map((edge) => `<div class="edge-row"><div><b>${edge.pre_type} → ${edge.post_type}</b><span>${edge.neuropil} / ${edge.neurotransmitter}</span></div><strong>${edge.synapses} SYN</strong></div>`).join('');
  $('#circuitNote').textContent = data.limits;
}

async function loadConnectome(circuit) {
  $('#datasetStatus').textContent = 'EXTRACTING REAL EDGES';
  $('#datasetCount').textContent = '…';
  try {
    const response = await fetch(`/api/connectome?circuit=${circuit}`);
    if (!response.ok) throw new Error('connectome endpoint unavailable');
    renderConnectome(await response.json());
  } catch (error) {
    $('#datasetStatus').textContent = 'LOCAL DATA UNAVAILABLE';
    $('#datasetCount').textContent = '—';
    $('#circuitNote').textContent = 'Start the local CHRONOS server to read FlyWire connections.';
  }
}

function updateReadouts() {
  const heading = ((state.fly.heading * 180 / Math.PI + 450) % 360).toFixed(0).padStart(3,'0');
  const d = Math.hypot(state.fly.x - state.home.x, state.fly.y - state.home.y) * 12;
  const preferred = state.scenario === 'compass' ? state.amber : Math.max(state.amber, state.violet);
  const odor = Math.min(.97, .16 + preferred / 125 + (Math.sin(state.time*3)+1)*.06);
  $('#headingValue').textContent = `${heading}°`;
  $('#vectorValue').textContent = `${d.toFixed(1)} m`;
  $('#odorValue').textContent = odor.toFixed(2);
  const actual = state.connectome?.edges?.[0];
  $('#signalValue').textContent = actual ? `${actual.synapses} SYN` : `${state.compass ? '+' : '±'} ${odor.toFixed(2)}`;
  $('#readoutDetail').textContent = actual ? `${actual.pre_type} → ${actual.post_type}` : (state.compass ? 'upwind drive' : 'heading unstable');
  $('#readoutSignal').textContent = actual ? `TOP ${state.connectome.dataset.toUpperCase()} EDGE` : (state.compass ? 'OLFACTORY SIGNAL' : 'COMPASS DISRUPTED');
  $('#compassNeuron').classList.toggle('off', !state.compass);
  $$('.olfactory').forEach((el) => el.classList.toggle('active', true));
  $$('.motor').forEach((el) => el.classList.toggle('active', state.running));
  $('.central').classList.toggle('active', state.compass);
  $('.home').classList.toggle('active', state.scenario !== 'forage');
  $('.olfactory.alt').classList.toggle('alt-active', state.violet > state.amber);
}

let previous = performance.now();
function frame(now) {
  const dt = Math.min(.04, (now - previous) / 1000); previous = now;
  if (state.running) { state.time += dt; updateFly(dt); }
  const w = canvas.clientWidth, h = canvas.clientHeight;
  ctx.clearRect(0,0,w,h);
  const bg = ctx.createLinearGradient(0,0,0,h); bg.addColorStop(0,'#292e34'); bg.addColorStop(1,'#171a20'); ctx.fillStyle=bg;ctx.fillRect(0,0,w,h);
  const src = sourcePositions(w,h);
  plume(src.amber.x,src.amber.y,state.amber/100,'ffae4f',w,h,0);
  plume(src.violet.x,src.violet.y,state.violet/100,'8978e6',w,h,2);
  drawWind(w,h); drawTrail(state.fly); drawSource(src.amber,state.amber/100); drawSource(src.violet,state.violet/100); drawFly(state.fly); updateReadouts();
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

function resetFly() { state.fly = {x:.48,y:.72,heading:-1.45,trail:[],phase:0}; }
function activateScenario(name) {
  state.scenario = name; resetFly();
  $$('.scenario').forEach((button) => button.classList.toggle('active', button.dataset.scenario === name));
  const labels = { forage: ['01','ODOR PLUME ARENA'], compass: ['02','PATH INTEGRATION FIELD'], lesion: ['03','COMPASS LESION TEST'] };
  $('#scenarioId').textContent = labels[name][0]; $('#worldLabel').textContent = labels[name][1];
  if (name === 'lesion') { state.compass = false; $('#compassToggle').classList.remove('on'); $('#compassToggle').setAttribute('aria-pressed','false'); }
  if (name === 'compass') { state.compass = true; $('#compassToggle').classList.add('on'); $('#compassToggle').setAttribute('aria-pressed','true'); }
  $('#compassCaption').textContent = state.compass ? 'heading is stabilized' : 'heading drifts without ring cells';
  loadConnectome(name === 'forage' ? 'odor' : 'compass');
}

$$('.scenario').forEach((button) => button.addEventListener('click', () => activateScenario(button.dataset.scenario)));
$('#runButton').addEventListener('click', () => { state.running = !state.running; $('#runButton').classList.toggle('paused', !state.running); $('#runText').textContent = state.running ? 'PAUSE' : 'RUN'; $('#statusText').textContent = state.running ? 'LIVE SIMULATION' : 'PAUSED'; });
$('#compassToggle').addEventListener('click', () => { state.compass = !state.compass; $('#compassToggle').classList.toggle('on',state.compass); $('#compassToggle').setAttribute('aria-pressed',String(state.compass)); $('#compassCaption').textContent=state.compass?'heading is stabilized':'heading drifts without ring cells'; });
[['amber','amberSlider','amberOut','%'],['violet','violetSlider','violetOut','%'],['wind','windSlider','windOut','×']].forEach(([key,id,out,suffix]) => { $("#"+id).addEventListener('input', e => { state[key]=Number(e.target.value); $('#'+out).textContent=state[key]+suffix; }); });
loadConnectome('odor');
