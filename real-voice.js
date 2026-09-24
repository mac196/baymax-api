function speakCanto(text){
  const u = new SpeechSynthesisUtterance(text);
  u.lang = 'zh-HK'; // Cantonese on Chrome Android
  u.rate = 0.95;
  window.speechSynthesis.speak(u);
}

function startCantoListen(){
  const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if(!Rec){ alert('请用Chrome'); return; }
  const rec = new Rec();
  rec.lang = 'yue-HK';
  rec.continuous = false;
  rec.onresult = e => {
    const t = e.results[0][0].transcript;
    document.getElementById('user-said').innerText = t;
    if(t.includes('头晕') || t.includes('唔舒服') || t.includes('晕')){
      speakCanto('收到，你头晕，我帮你检测心率同通知屋企人');
      startRealPulse();
    } else if(t.includes('求助')){
      triggerSOS(heartRate || 0);
    } else {
      speakCanto('明白，' + t);
    }
  };
  rec.start();
}