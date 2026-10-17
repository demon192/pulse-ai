# Three-minute demo script

**Setup before recording**

```bash
cd frontend && npm run build
cd ../backend && SERVE_FRONTEND=true uvicorn app.main:app --port 8000
curl -X POST -H "X-Dev-User-Id: mgr-001" http://localhost:8000/api/admin/seed
```

Open <http://localhost:8000> as **Priya Raman**. Set the Gemini key first if you
want the briefing to come from the model rather than the fallback — the UI
labels which one produced it either way.

---

## 0:00–0:25 — The problem

> *On the Overview page.*

"An engineering manager runs three projects and ten engineers. The information
they need is spread across tickets, pull requests, chat and meetings — so an
approval request gets lost in a thread, an engineer stays blocked, and a
dependency quietly puts a release at risk.

This is TeamPulse AI. It is not employee monitoring. It is the coordination
layer: what needs the manager's attention, what is at risk and why, and what
happens to the work when someone becomes unavailable."

---

## 0:25–0:55 — The manager dashboard and a pending approval

> *Point at the four tiles, then the top inbox item.*

"Today: one pending approval, four open support requests, three tasks needing
attention, one coverage gap.

Top of the inbox — Arjun asked for a decision on the settlement API contract
three days ago. TeamPulse does not just say it is old. It says *what it costs*:
two dependent tasks cannot proceed, both high or critical priority, and the
Settlement API GA milestone is three days away."

> *Open the item. Point at "Why this is ranked here".*

"That ranking is deterministic — explicit urgency, deadline, blocked downstream
work, milestone proximity, time waiting. Gemini explains it; it never sets it."

---

## 0:55–1:25 — An engineer reports a blocker, and the manager responds

> *Switch persona to Diego Alvarez. Overview.*

"Diego's checkout work is blocked on an ambiguous requirement. He raised it in
TeamPulse, so it is a tracked item with an owner — not a message that can be
missed."

> *Switch to Priya. Action Inbox → "Declined-card messaging requirement is
> ambiguous". Type a response, send it.*

"The manager answers in the same place."

> *Switch back to Diego. Support Requests.*

"And Diego sees the response and the status change on his own request,
immediately. It stays visible until it is resolved — marking the notification
read does not close it."

---

## 1:25–2:20 — Emergency leave

> *Switch to Rhea Kapoor. Handovers → Record unavailability.*

"Rhea is suddenly unavailable, mid-release. She records dates and nothing else —
TeamPulse never asks for a reason. She has not written handover notes."

> *Submit, then click "Analyse impact and generate brief".*

"TeamPulse now does the work a manager would otherwise do by hand."

> *Walk down the page.*

"Her two active tasks. The two tasks downstream of them. The upstream approval
that is the actual blocker. Two milestones that could slip. Three relevant
documents.

Then backup candidates. Arjun scores 84 — and you can see exactly why: three of
three required skills, ninety per cent project familiarity, available, but
almost no spare capacity. Lena scores 72 with four times the headroom. That
trade-off is the manager's to make, not the model's.

Six people are shown as *not assignable*, each with its reason. Mei has no
authorisation on payments. Victor is already on leave. A manager cannot pick
them — the eligibility gate runs before scoring and again at approval.

And the handover brief: eleven sections, each labelled with how it was derived —
verified fact, rule-derived, or hypothesis. Rhea wrote no notes, so TeamPulse
says so, and lists every gap the incoming engineer must confirm with a human."

> *Switch to Priya. Select Arjun. Approve.*

"The manager approves. Ownership has **not** moved."

> *Switch to Arjun. Handovers → Accept the assignment.*

"Only when Arjun accepts do the tasks transfer. Two human decisions, both
recorded in the audit trail."

---

## 2:20–2:45 — Notifications and tracking

> *Notifications page.*

"One notification per concern. An item that stays unresolved is escalated, not
repeated — at most once a day, and only when it actually gets worse. Each one
carries its reason and a suggested action. Reading it never closes the work
behind it."

> *Back to Overview.*

"And the manager's view has updated: the approval is resolved, the decision is
recorded against the task, and coverage is in place."

---

## 2:45–3:00 — Gemini, safeguards and impact

> *On the Overview page, with the briefing visible.*

"Gemini does four things here: it summarises a project, reads an engineer's
free-text request, synthesises the handover brief, and explains risk in plain
language. Everything that has to be *correct* — deadlines, dependencies,
permissions, eligibility, priority — is deterministic code.

Every AI statement is labelled with how it was derived, and any record it cites
that was not in the data it was given is dropped before a manager sees it. It
cannot change an assignment, a status or a priority.

The point is simple: a lost approval stops being losable, and an engineer's
sudden absence stops being a scramble."

---

## Fallback notes

- **Gemini not configured** — the app still works; badges read "Generated
  without the model". This is a feature worth showing if a key is unavailable.
- **Reset mid-demo** — re-run the seed `curl` and reload.
- **Shorter cut** — Scenario 3 alone (1:25–2:20) is the most distinctive part;
  keep it and compress the rest.
