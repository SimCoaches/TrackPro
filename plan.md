# 🏁 TrackPro: Advanced Sim Racing AI Coach

## 🔧 Project Summary
You are tasked with building an advanced sim racing AI coach, called TrackPro, that will outperform existing systems like Trophi.ai (Mansell AI). The entire system must be written in 100% Python.

## ⚙️ Build Process Rules
- Build one task at a time.
- **DO NOT combine multiple tasks.**
- Fully test each task before moving to the next.
- Build modular, loosely coupled code.
- Inputs, outputs, and interfaces between modules must be extremely clear.
- No cloud dependencies — all functions fully offline.
- Final product must be fully local on the user's machine.

## 🏗 Full Sequential Build Tasks

### 🚦 Phase 1 — Telemetry Data Engine

#### Task 1.1 — Telemetry Interface
- Use pyirsdk to connect to iRacing's live telemetry stream.
- Collect these fields at 60 Hz:
  - Speed
  - Throttle position
  - Brake pressure
  - Gear
  - Steering angle
  - Lateral G-force
  - Longitudinal G-force
  - Track position (track distance)
  - Lap number
  - Sector number
  - Yaw rate
  - Suspension travel (all 4 corners)
  - Wheel speed (all 4 wheels)
  - Tire temperatures (all 4 tires)
- Build a TelemetryProvider class.
- Store live data in a circular buffer (FIFO queue) to hold ~60 seconds of rolling telemetry.

**✅ Test:**
- Print live telemetry values while driving.
- Verify all fields update correctly.

#### Task 1.2 — Telemetry Storage Module
- Write telemetry to a persistent log file.
- Format: CSV or SQLite.
- Each driving session saved as separate file.
- Ensure timestamped data for every telemetry frame.

**✅ Test:**
- After driving, verify data logs exist.
- Load log and validate full data integrity.

#### Task 1.3 — Telemetry Playback
- Build a replay engine to feed saved telemetry files into the analysis system.
- Simulate real-time stream from stored data.

**✅ Test:**
- Load previously recorded session.
- Confirm playback can feed downstream modules identically to live data.

### 🏁 Phase 2 — Track Map & Corner Segmentation

#### Task 2.1 — Track Map Generator
- Use position data to generate full track map.
- Identify lap start/end automatically.
- Store distance-based position reference.

**✅ Test:**
- Plot map.
- Visually confirm shape matches known track layout.

#### Task 2.2 — Corner Segmentation
- Build auto-segmentation module to identify corners.
- Use drop in speed + steering angle increase to identify corner entry and exit.
- Label corners (e.g. Turn 1, Turn 2…).

**✅ Test:**
- Output corner list with entry/exit distance markers.
- Manually verify accuracy.

### 🧠 Phase 3 — Real-Time Coach Loop

#### Task 3.1 — Real-Time Analyzer Loop
- Constantly analyze live telemetry.
- For each corner, detect:
  - Brake point accuracy
  - Apex speed
  - Throttle timing
- Build CoachEngine class that outputs "Coaching Events" when mistakes are detected.

**✅ Test:**
- Trigger "Brake too early" or "Throttle too soon" events while driving.
- Print events to console.

#### Task 3.2 — Voice Feedback Engine
- Use pyttsx3 (offline TTS library).
- When a coaching event fires, speak corresponding feedback message.
- Example: "Brake earlier next time for Turn 5."

**✅ Test:**
- Verify live voice feedback works while driving.

### 👁 Phase 4 — Visual HUD Overlay

#### Task 4.1 — Overlay Renderer
- Create on-screen overlay:
  - Current lap time
  - Corner name
  - Real-time coaching alerts
  - Delta vs best lap
- Use PyQt6, Pyglet, or Pygame for GUI rendering.

**✅ Test:**
- Confirm overlays are synchronized with driving.
- Correct corner names display in real-time.

### 📊 Phase 5 — Post-Session Analysis Engine

#### Task 5.1 — Lap Comparison Engine
- Compare laps to calculate:
  - Best sectors
  - Optimal lap from sector bests
  - Time loss per sector

**✅ Test:**
- Verify correct sector delta calculations.
- Output ranked list of corner losses.

#### Task 5.2 — Mistake Classifier
- Build rule-based mistake classifier for each corner:
  - Late brake
  - Early brake
  - Early throttle
  - Late throttle
  - Entry speed errors
  - Exit speed errors

**✅ Test:**
- Simulate mistakes to verify classifications are correct.

#### Task 5.3 — Post-Session Report Generator
- Build full session report:
  - Laps summary
  - Corner-by-corner time loss
  - Mistakes identified
  - Suggested training focus

**✅ Test:**
- Drive full session.
- Verify report contents make sense and are complete.

### 🔧 Phase 6 — Handling Analyzer & Setup Advisor

#### Task 6.1 — Handling Issue Detector
- Use telemetry to detect:
  - Understeer (high steering angle, low yaw rate)
  - Oversteer (countersteer spikes, high yaw rate)
  - Tire slip (if available)
- Label issues per corner.

**✅ Test:**
- Simulate handling imbalances.
- Verify correct issue labels output.

#### Task 6.2 — Setup Recommendation Engine
- Build rule-based setup advisor:
  - Soft/hard ARBs
  - Ride height
  - Springs
  - Wing
  - Brake bias
  - Differential
- Map handling issues to setup changes.

**✅ Test:**
- Feed handling issues.
- Confirm proper setup change suggestions.

### 👻 Phase 7 — Ghost Lap Engine

#### Task 7.1 — Ghost Lap Generator
- Stitch best sector times into "Optimal Lap".
- Output predicted lap time.

**✅ Test:**
- Verify optimal lap always beats any real lap.

#### Task 7.2 — Ghost Overlay
- Build overlay to show user inputs vs ghost inputs (brake, throttle, speed traces).

**✅ Test:**
- Confirm real-time ghost overlays align accurately.

### 🎯 Phase 8 — Driver Style Classifier

#### Task 8.1 — Driving Style ML Classifier
- Use Scikit-Learn clustering (KMeans).
- Group drivers into:
  - Aggressive
  - Conservative
  - Smooth
  - Inconsistent
- Input features:
  - Brake variance
  - Steering variance
  - Entry speeds

**✅ Test:**
- Cluster sample data.
- Verify logical grouping.

### 🔬 Phase 9 — Setup Optimization ML

#### Task 9.1 — Setup Regression Model
- Use XGBoost regression model.
- Predict lap time delta from setup changes.
- Train on historical telemetry + setup datasets.

**✅ Test:**
- Feed example setup data.
- Verify lap time predictions behave logically.

#### Task 9.2 — Setup Auto-Tuner
- Build optimizer that suggests best setup adjustments to minimize predicted lap time.

**✅ Test:**
- Feed current setup.
- Generate next-step optimal setup.

### 🚗 Phase 10 — Racecraft Coaching

#### Task 10.1 — Overtaking Advisor
- Monitor closing speeds.
- Predict safe overtaking zones.
- Voice suggest "Pass possible at Turn 7."

**✅ Test:**
- Verify overtaking suggestions trigger correctly.

#### Task 10.2 — Defensive Advisor
- Detect cars approaching from behind.
- Suggest defensive lines before corner.

**✅ Test:**
- Simulate chase scenario.
- Verify defense guidance is timely.

#### Task 10.3 — Pit Strategy Optimizer
- Build pit stop advisor:
  - Calculate fuel consumption rate.
  - Predict tire wear rates.
  - Calculate optimal pit windows.

**✅ Test:**
- Simulate full race.
- Verify optimal pit lap suggestions make sense.

### 🗣 Phase 11 — AI Voice Q&A Coach

#### Task 11.1 — Voice Command Module
- Use VOSK for offline speech recognition.
- Allow questions like:
  - "How was Turn 5?"
  - "Where did I lose most time?"

**✅ Test:**
- Test recognition quality.
- Verify correct answers returned.

#### Task 11.2 — Explainable AI Engine
- Use SHAP to explain model predictions.
- Generate explanations like:
  - "You lost 0.3s by braking 10m too early."

**✅ Test:**
- Validate output explanations are clear, accurate.

### 📈 Phase 12 — Full Analysis Dashboard

#### Task 12.1 — Full GUI Build
- Create desktop analysis UI using Dash (Plotly) or PyQt6.
- Show:
  - Lap comparison
  - Corner analysis
  - Ghost data overlay
  - Setup advice
  - Racecraft review

**✅ Test:**
- Load full session.
- Verify all panels populate correctly.

### 🔬 Phase 13 — Testing & Performance Validation

#### Task 13.1 — Full System Testing
- Run complete end-to-end tests after every phase.
- Validate accuracy, speed, correctness.

#### Task 13.2 — Performance Optimization
- Measure system latency.
- Optimize for real-time coaching speed.

### 🚀 Phase 14 — Stretch Goals (Post Launch)
- Conversational AI with LLM (Local GPT4All or LLaMA)
- Cloud-based Ghost Sharing
- Haptic Feedback Hardware Integration
- Real-World Telemetry Support (MoTeC, AIM)
- VR/AR Coaching Overlays

## 🔐 Final Reminders for Development
- Build **ONE TASK AT A TIME**.
- **DO NOT skip ahead**.
- **DO NOT try to combine tasks**.
- **DO NOT attempt "end-to-end" builds early**.
- Fully test and verify after each deliverable.
- Build fully modular classes that can be independently tested. 