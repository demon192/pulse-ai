# TeamPulse AI — three-minute demo

Team leader: Riya Bisht. Team member: Ishu Mehra.
Theme: Future of Work & Enterprise Productivity.

## Start and reset

Open `http://127.0.0.1:8000` while the backend is running. To start it again from the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\deliverables\Start-Demo.ps1
```

Use a separate terminal to reset synthetic records before rehearsing:

```powershell
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/admin/seed' -Headers @{'X-Dev-User-Id'='mgr-001'}
```

The reset applies only to the local demo workspace. Reload the browser after resetting. Persona switching is at the bottom of the desktop sidebar. The demo starter intentionally disables Gemini so it needs no paid API or internet connection. Say that it uses the labelled fallback; do not call a fallback response live Gemini output.

## Narration and actions

### 0:00–0:35 — manager overview

Select Priya Raman. Open Overview, then Action Inbox and the settlement API approval.

“We are Riya Bisht and Ishu Mehra, presenting TeamPulse AI for the Future of Work and Enterprise Productivity theme. Engineering work often waits on decisions buried in messages. TeamPulse gives the manager one place to see what needs attention and why. This settlement approval blocks two dependent tasks. Its rank comes from recorded deadlines and dependencies, with evidence attached.”

### 0:35–1:15 — a blocker becomes tracked work

Select Diego Alvarez. Support Requests → New request. Choose Payments Platform v2, related task Checkout error states, category Blocker. Enter a short request asking to confirm declined-card retry messaging. Submit.

Select Priya. Action Inbox → open the new request → send a response. Enter resolution notes and select Resolve action. Select Diego → Support Requests → Closed → open the request.

“An engineer can raise a blocker with its project and affected task. It creates a tracked manager action, rather than another chat message. The manager answers and records the outcome. Diego sees the response and resolution on his own request. Reading a notification alone does not close the underlying work.”

### 1:15–2:30 — coverage after an absence

Select Rhea Kapoor → Handovers → Record unavailability → Record and continue → Analyse impact and generate brief.

Select Priya → Handovers → Open. Show affected tasks, backup ranking, brief and missing information. Select Arjun and approve. Select Arjun → Handovers → Open → accept the assignment.

“When Rhea becomes unavailable, TeamPulse maps her active tasks, downstream dependencies, milestones and pending decisions. It ranks eligible backups and explains the scoring factors. Arjun knows the work, while Lena has more spare capacity. People without project authorization or availability cannot be selected. The handover brief gathers context and marks missing information. The manager approves a backup, but the tasks still belong to Rhea. Only when Arjun accepts does ownership transfer. That keeps the assignment under human control.”

### 2:30–3:00 — provenance and evidence

Select Priya → Notifications, then Overview. Show the labelled fallback if generating a briefing.

“Gemini is integrated for project summaries, request interpretation, handover briefs and risk explanations. This local demo uses the labelled deterministic fallback. Rules determine risk, eligibility and priority. Our existing suites pass 138 backend tests and 47 frontend tests. Those results use synthetic data; a real-team pilot and cloud sign-in validation remain future work.”

## Recording and submission checklist

- Rehearse once after a fresh reset, then record the browser with your own narration.
- Record at 1920×1080 if possible. Keep text readable and close unrelated tabs.
- Upload your three-minute recording to your chosen host and replace the pending video link in slide 14.
- Replace the localhost product link with a hosted URL only after deployment works.
- TeamPulse AI is used as the working team/project name; change it if your registered team name differs.
- Keep the recording within three minutes. If you run short of time, show the existing Diego blocker instead of creating another one, while retaining the full approve-then-accept handover flow.
