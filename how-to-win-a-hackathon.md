# How to win a hackathon?

**Dawid Perdek** — mentor · judge · never a winner
HACKYEAH 2026 · Day 1

---

## 00 / Intro

### I've never won a hackathon.
*// true story*

### Why listen to me anyway?

**10+ hackathons · 300+ teams mentored · 100+ projects judged**

| A winner sees | A mentor & judge sees |
|---|---|
| 1 team: their own | all of them |

### You're spending 45 minutes of your 24 hours here.

**3%** of your hackathon, right now.

Let's make it the best-invested 3% of your weekend.

`T+0 · hacking starts 11:00` → `this talk` → `T+24h · judging`

---

## 01 / Judging

### What a judge actually sees

- **50+** — projects to evaluate
- **<5 min** — per project (more time for top ones only)
- **1 + 1** — one demo and one pitch. That is your project.

**Everything else is invisible.**

### The criteria

*Example from HackYeah 2025, category: Biohacking*

| Criterion | Question | Weight |
|---|---|---|
| Idea & Innovation | Is this new, or at least new here? | 30% |
| Relation to category | Does it match the task description? | 20% |
| Practical usability | Is this actually applicable? | 20% |
| Design | How is it in terms of UI and UX? | 20% |
| Completeness | How close is it to launching MVP? | 10% |

Count how many of these are decided in the demo and the pitch.

### Don't memorize the last slide.

**Read YOUR task's criteria.**
With understanding.

### Read YOUR task's criteria.

**TWICE.**
Three times even.
**READ. Not "paste in claude".**

### Seen vs. unseen

**What the judge sees**

- The submission
- The pitch
- Your slides
- How clearly you state the problem
- Whether it breaks on stage
- Your team vibes
- Potential future of the product

**What the judge never sees**

- ~~Your clean architecture~~
- ~~Your test coverage~~
- ~~The 3 AM refactor~~
- ~~The features you almost finished~~
- ~~Your CI pipeline~~

### Your repo is not your product.
**Your demo is.**

### Team A vs. Team B

| Team A | Team B (WINNER) |
|---|---|
| Event-sourced backend · 12 microservices · 94% test coverage | Mocked backend · hardcoded data · one happy path |
| Demo: `500 Internal Server Error` | Demo: works. Tells a story. |

Who wins? **Team B. Every single time.**

### Optimize for evaluation,
**not for completion.**

*// the whole talk in one line*

---

## 02 / Formalities

### The cheapest points you'll ever get

Formal requirements cost you minutes. Missing one costs you everything.

### Deliverables checklist

*Of course, remember to check the actual exact deliverables in your task description!*

- Repository: can the judges actually open it?
- Presentation / pitch deck
- Demo video / unique value proposition
- Submission form, filled in completely
- Team data & task selection correct

**Deadlines**

- **Sat 20:00** — first version in the system. Hard.
- **Final: Sun 11:00** — Submit one hour earlier. Seriously.

**Create it early. Update it as you go. Submit early.**

### Read the full task. Twice.

Once for the problem. Once for the criteria.

- **The task's own criteria** — Read them with understanding, not just once. They are your scoring sheet.
- **Their definition of done** — What would make them say: we'd actually use that?
- **Hidden hints** — More like "hidden in plain sight". Look at the criteria!

### Hall of shame

*Some projects of really good quality failed because of stupid mistakes…*

- **Start / Submission time** — Start was at 12pm. Commits from 11:30am. The deadline was 12:00pm. Submitted at 12:04pm.
- **"It was working before a pitch"** — Record a demo earlier just in case, attach it to the submission.
- **Great solution, wrong task** — Brilliant work, judged against a task it didn't solve.
- **Private repo** — Judges locked out. Score: 0. Disqualified.

---

## 03 / Strategy

### Pick your battle

**Open tasks**

- Often the most crowded
- Full freedom of idea
- You're compared with everyone

**Partner tasks**

- Often fewer teams per task
- Clear expectations and data
- Partner mentors on site

**Count your competitors before you pick.**

*Open categories 2026: Defence · Sport & Healthcare · Smart City · AI + SheHacks: ImpactHer*

### What does the partner actually want?

**Ask their mentors. They're here.**

Three questions worth asking:

1. "What would you actually use after this weekend?"
2. "What have others tried that didn't work?"
3. "What would impress your boss?"

### Demo-driven development

One happy path. End to end. Working early.

**Build:** User opens it → Gives input → Your core magic → Result shown → Wow moment

**Later. Or never:** Login · Settings · Admin panel · Edge cases

### Fake it responsibly

**OK to mock**

- Login & auth
- Payments
- Seed data & integrations
- Admin panels
- Scale

**Must be real**

- The core feature
- The 'wow' moment
- Anything the task explicitly requires

**Mock it but know how it will work for real. Judges will ask.**

And if they ask what's mocked, say so. Honesty scores. Getting caught doesn't.

### Someone owns the pitch from hour one

- **Builders** — Make the demo path work.
- **Integrator** — Keeps it running end to end.
- **Designer** — Makes it clear at a glance.
- **Pitch owner** — Writes the story at hour one. Updates it at every checkpoint.

Small team? Think roles, not headcount. Someone can wear two hats, but every hat must be worn.

### Why story first?

Story is not the last step. It's a planning tool.

- **See it through your user's eyes** — The story pulls you out of the codebase and into their day.
- **Judge your own value** — If the story is weak, the feature list won't save it.
- **Better input for planning** — It tells you what to build first, and what not to build at all.

### Anti-patterns from the mentor's desk

- **The cathedral** — Perfect architecture, no demo.
- **"We'll glue it at 4 AM"** — Integration is not a final step.
- **The midnight pivot** — New idea at T+12h. Old problems plus new ones.
- **The untested demo** — It worked once, on one laptop.

---

## 04 / Timeline

### The 24h map

Hacking: Saturday 11:00 → Sunday 11:00

| Marker | Time |
|---|---|
| Start | 11:00 |
| T+4h | 15:00 |
| T+9h (hard deadline) | 20:00 |
| T+19h | 06:00 |
| T+22h | 09:00 |
| End | 11:00 |

- **BUILD:** Scope & skeleton → Build the demo path → Freeze & harden
- **STORY & PITCH:** Story draft → Pitch prep (the story grows with the build) → Rehearse
- **SUBMISSION:** Update as you go → Polish → create first version at 20:00 (HARD) → submit + triple-check
- **CI:** Set up CI → Runs on every push

Pitch prep starts at T+4h, together with the build.

### 01 — Scope & skeleton (T+0 → 4h)

*You're near the end of this phase right now.*

- Pick the task. Draft the story: whose problem, what changes for them.
- Define the demo path: 3–5 steps.
- Repo, CI, deploy target, hello world: live.
- Split roles. Name the pitch owner.

**AI makes code nearly free. Thinking isn't. Spend the time here.**

### 02 — Build the demo path (T+4 → 19h)

*The longest phase and the easiest one to lose.*

- End to end first. Pretty later.
- CI from the start: AI writes fast, CI catches it.
- Create your submission early.
- Pitch prep starts now. The story grows with the build.
- Sleep in shifts, not never.

**HARD DEADLINE · 20:00 (T+9h): first version in the system.**

### 03 — Freeze & harden (T+19 → 22h)

*Feature freeze is a decision, not a feeling.*

- No new features. Period.
- Fix only what breaks the demo.
- Record a backup demo video.
- Test on the setup you'll present on.
- Polish the submission. Keep it in sync with the project.

### 04 — Pitch, rehearse, triple-check (T+22 → 24h)

*The pitch has been growing since T+4h. This is rehearsal, not writing.*

- Rehearse with a timer. At least three times.
- Final submission by T+23h, not T+23:59.
- Last hour: triple-check every artifact, from the judges' side.
- Prep Q&A: what's real, what's mocked, how mocks become real. Anticipate questions.

---

## 05 / Checkpoints

*// take a photo of this slide*

| When | Question |
|---|---|
| **T+4h** | Can you say what you're building, and for whom, in one sentence? |
| **T+9h** | 20:00: first version in the system? Demo path working end to end? |
| **T+19h** | Is it demo-able right now? Then: feature freeze. |
| **T+22h** | Can someone who didn't build it run the demo? |
| **T+23h** | Is everything submitted? Now check it three times. |

### If the answer is "no":

**cut scope.**
…or sleep.

*// it's a hackathon, you're allowed*

---

## 06 / Outro

### Questions?

*I have one more thought before you go. But first:*

**I'm mentoring here all weekend. Come find me.**

- LinkedIn: linkedin.com/in/perdekdawid
- Discord: @superdyzio

*Ping me on Discord anytime, I'll do my best to help!*

### Luck favors the prepared.
**So be prepared.**

— after Louis Pasteur: "chance favors only the prepared mind"

### …and then I'll wish you luck.

*// stay hydrated*

---

**Thank you!** — Dawid Perdek, see you guys
