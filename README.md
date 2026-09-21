\# BAYMAX Auto OS v2 🤖🚗

\### Your Personal Healthcare Companion, Inside Your Car.



> Cantonese-first. Health + Mobility. Built in Guangzhou.



Baymax Auto OS is not a chatbot. It's a real-time in-car operating system that monitors \*\*14 car systems + your pulse\*\*, speaks fluent \*\*Cantonese (粤语)\*\*, and uses Vision AI to analyze your surroundings.



\*\*Live Demo:\*\* https://baymax-api-bii6.onrender.com/

\*\*Video Demo:\*\* (add your Loom/YouTube link here after you record)



!\[Baymax OS](https://img.shields.io/badge/status-live-success)!\[Python](https://img.shields.io/badge/Python-3.11-blue)!\[FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)!\[Cantonese](https://img.shields.io/badge/Lang-粤语-red)



\### ✨ What It Does



\*\*1. 14 Car Systems Control Center\*\*

Battery, Engine, AC, Tire Pressure, Doors, Lights, Navigation, Security, Entertainment, Diagnostics... all in `operations/` modules.



\*\*2. Healthcare Inside The Car\*\*

\- Real-time Pulse Scanner (`/operations/pulse.html`) - stores to `pulse\_history.json`

\- Analyzes stress/fatigue and suggests breaks

\- Baymax persona: "I cannot let you drive while your vitals are low"



\*\*3. Cantonese-First AI (Our Moat)\*\*

Most AI speaks Mandarin or English. Baymax speaks native Guangzhou Cantonese. Built for HK / Guangdong drivers.

\- Auto-translate: `en <-> yue <-> zh-CN <-> fr`

\- Powered by Groq Llama 3.3 70B for <1s latency



\*\*4. Vision AI\*\*

Upload a dashboard warning light or your face -> Baymax analyzes it (`/api/screen-analyze`).



\### 🛠️ Tech Stack



\- \*\*Backend:\*\* FastAPI, Python 3.11, Uvicorn

\- \*\*Brain:\*\* `llama\_brain.py` - Groq API + custom Cantonese prompting

\- \*\*Frontend:\*\* Vanilla JS (no framework - fast for in-car), `JS/api.js` shared API client

\- \*\*Deployment:\*\* Render (Auto-deploy from GitHub)

\- \*\*Data:\*\* JSON file storage (ready to migrate to SQLite/Postgres)



\### 📁 Project Structure (DO NOT MOVE FILES)

