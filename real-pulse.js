let heartRate = 0;
let measuring = false;

async function startRealPulse() {
  measuring = true;
  const video = document.createElement('video');
  video.style.display = 'none';
  document.body.appendChild(video);

  const stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: "environment", torch: true }
  });
  video.srcObject = stream;
  await video.play();

  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  let redValues = [];
  let lastPeak = 0;
  let bpmHistory = [];

  function analyze() {
    if(!measuring) return;
    canvas.width = 100; canvas.height = 100;
    ctx.drawImage(video, 0, 0, 100, 100);
    const data = ctx.getImageData(0,0,100,100).data;
    let redAvg = 0;
    for(let i=0;i<data.length;i+=4) redAvg += data[i];
    redAvg /= (data.length/4);
    redValues.push(redAvg);
    if(redValues.length > 200) redValues.shift();

    // Simple peak detection for BPM
    if(redValues.length > 50){
      const recent = redValues.slice(-30);
      const avg = recent.reduce((a,b)=>a+b)/recent.length;
      if(redAvg > avg + 2 && Date.now() - lastPeak > 300){
        const interval = Date.now() - lastPeak;
        if(lastPeak!= 0 && interval > 400 && interval < 1500){
          const bpm = Math.round(60000 / interval);
          if(bpm > 50 && bpm < 130){
            bpmHistory.push(bpm);
            if(bpmHistory.length > 5) bpmHistory.shift();
            heartRate = Math.round(bpmHistory.reduce((a,b)=>a+b)/bpmHistory.length);
            onRealBPM(heartRate);
          }
        }
        lastPeak = Date.now();
      }
    }
    requestAnimationFrame(analyze);
  }
  analyze();
}

function onRealBPM(bpm){
  document.getElementById('bpm-value').innerText = bpm;
  document.getElementById('bpm-status').innerText = bpm > 100? '偏高' : bpm < 60? '偏低' : '正常';
  document.getElementById('bpm-status').style.color = (bpm > 100 || bpm < 60)? 'red' : 'green';
  if(bpm > 110 || bpm < 50){
    triggerSOS(bpm);
  }
}

function triggerSOS(bpm){
  navigator.geolocation.getCurrentPosition(p => {
    const msg = `【Baymax求助】心率异常${bpm} bpm 位置 https://www.google.com/maps?q=${p.coords.latitude},${p.coords.longitude} 时间 ${new Date().toLocaleTimeString()}`;
    // Vibrate + Cantonese alert
    navigator.vibrate && navigator.vibrate([500,200,500]);
    speakCanto(`心率${bpm}，不正常，已准备求助`);
    // Open share - user just clicks send
    document.getElementById('sos-link').href = `https://wa.me/?text=${encodeURIComponent(msg)}`;
    document.getElementById('sos-box').style.display = 'block';
  });
}

function stopRealPulse(){ measuring = false; }