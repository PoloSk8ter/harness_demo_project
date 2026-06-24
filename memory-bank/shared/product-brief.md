---
status: ready
product_verdict: BUILD NOW
clarity_score: 8.4
date: 2026-06-25
owner_role: po
---
<!-- PRODUCT BRIEF — the Product Owner's ONE handoff artifact: the curated ROLLUP of the validated
features. Cross-cutting locked calls live in memory-bank/shared/decision-log.md. The SA reviews this
before designing. Frontmatter stays at the very top. Headers match .claude/harness/po_brief.py. -->

# Product Brief — A guardrail-fronted, multi-specialist conversational banking assistant (reference architecture)

**Review posture: HOLD SCOPE** — the idea is clear and singular; this brief bulletproofs it as stated rather than expanding or shrinking it.

## Idea
A conversational banking assistant that takes a single user message, decides which one area of banking
it concerns, hands it to the specialist for that area, and returns one finalized reply. Four
specialist competencies are in scope: account & balance, transaction history, card actions (lock /
unlock), and suspected-fraud escalation to a human. A guardrail layer sits in front of everything and
refuses anything out of scope or unsafe before any specialist is involved. This is a **reference /
demo** build: banking data is simulated, the user's identity is assumed (sign-in is out of scope), and
the deliverable is the working multi-specialist composition itself, not a production deployment.

## Who It's For
The primary user is a **bank customer with a single, specific need right now** — "what's my balance,"
"did my rent clear," "freeze my card, it's lost," "I see a charge I didn't make." Today that person
either hunts through a banking app's menus or waits in a phone queue; both cost minutes and frustration
for what should be a one-sentence answer or a one-tap action. The secondary user is the **team building
or studying this assistant** — for them the pain is that wiring several focused agents safely behind one
front door (with refusals, confirmations, and human handoff) is fiddly to get right, and a correct,
legible reference is scarce. This brief serves both: the demo proves the pattern for the builders while
modelling the customer's one-shot journey.

## What It Must Do
- Accept a free-text user message and, **before anything else**, screen it through a guardrail that
  refuses out-of-scope or unsafe requests with a clear, polite decline (and refuses rather than guesses
  when intent is ambiguous or risky).
- For an in-scope message, **classify it to exactly one** of the four areas and route it to that single
  specialist (account & balance, transactions, card actions, fraud escalation).
- Answer **account & balance** and **transaction history** questions from the (simulated) account data.
- For **card actions**, never change state on intent alone: **draft the action, require an explicit user
  confirmation, then execute** the lock/unlock and report the result.
- For **suspected fraud**, produce a **structured escalation record** (the flagged item plus enough
  context for a human to act) **and** tell the user a human will follow up — no live-human dependency.
- Return **one** coherent, finalized reply per message — formatted for the user and re-checked against
  the guardrail's safety boundary before it is sent.
- Behave correctly on the unhappy paths: an out-of-scope ask, an unsafe ask, an ambiguous ask, and a
  card action the user declines to confirm.

## How It Should Work
From the user's side it is one chat box. They type one thing; they get one answer (or one safe refusal,
or one confirmation prompt). The smallest observable proof that it works is a short scripted
conversation that exercises every path once: a balance question returns the balance; a transaction
question returns the right transactions; "lock my card" returns a confirmation prompt and only locks
**after** the user says yes; "I didn't make this charge" returns a structured escalation plus a
"a specialist will follow up" acknowledgement; an out-of-scope request ("what's the weather") and an
unsafe request are both politely refused without ever reaching a specialist; and an ambiguous message is
clarified or refused rather than mis-routed.

## Evidence
- [confirmed] A front-door router that classifies each message and dispatches it to one of several
  focused specialists is the established, well-documented shape for assembling multi-competency
  assistants; routing as its own dedicated decision improves accuracy and keeps the system legible and
  extensible (add a competency = add a specialist + teach the router about it). (LangGraph supervisor
  reference docs; Focused.io "supervisor vs swarm" architecture write-up.)
- [confirmed] The four chosen competencies are exactly what mainstream production banking assistants do:
  Bank of America's "Erica" has handled ~2.5B interactions for ~20M users, and Wells Fargo's "Fargo"
  handles card controls and transaction search with privacy safeguards; the banking-assistant market was
  ~$2.1B in 2025 (~24% CAGR) with ~54% of financial institutions implementing this class of assistant.
  The idea targets a real, proven need surface. (CoinLaw banking-chatbot statistics 2025; Neontri
  banking-chatbots round-up.)
- [confirmed] A refusing guardrail and a human-escalation path are not optional polish in this domain:
  the U.S. CFPB holds such assistants to the same consumer-protection standard as a human agent, and an
  independent audit found all 24 banking assistants it tested were exploitable — making an explicit
  refusal boundary and human handoff core requirements, which this idea already includes.
  (CFPB "Chatbots in consumer finance" report; Corporate Compliance Insights audit.)
- [estimated] As a reference build on simulated data with sign-in out of scope, effort is moderate and
  risk is low: there is no real money, no real personal data, and no external integration surface to
  secure; the orchestration shape is well-trodden, so the work concentrates in the four specialists, the
  guardrail boundary, and the confirm-then-execute and escalation behaviours.
- [assumption] The audience values a faithful demonstration of the *composition* (refuse → route →
  specialise → confirm/escalate → finalize) over production realism. If the real need were a deployable
  bank assistant, the simulated-data / assumed-identity scope would teach the easy half and skip the
  hard half — this is the brief's headline falsifier, below.

## Strategic Fit
- **Jobs-to-be-Done.** The customer hires this to "resolve one banking need in one message, safely,
  without menus or hold music." The whole design serves that job: the router gets them to the right
  competence in one hop, the guardrail keeps the job safe, confirm-then-execute keeps an action from
  firing by accident, and escalation keeps a fraud worry from dead-ending. Every part maps to the job.
- **Lean MVP / Build-Measure-Learn.** The smallest learnable unit is the end-to-end path exercised once
  per competency plus one refusal, one confirmation, and one escalation — precisely the Acceptance
  script below. We learn whether the composition holds together before investing in breadth or realism.
- **Build-vs-buy / commoditization (Wardley).** The orchestration shell is a commodity — reusing the
  well-known router-and-specialists shape is the right call, not reinventing it. The differentiated,
  worth-building value is the *safety composition*: the refusal boundary, the write-safety
  (confirm-then-execute) pattern, and the structured human handoff. Effort should pool there.
- **Opportunity cost.** Building this now is cheap as a reference artifact, but it is not free: a
  several-specialist assistant carries more latency, cost, and coordination failure modes than a single
  capable assistant with tools. The case-against weighs exactly that trade.

## Cost / Effort Tier
**Effort: Medium. Risk: Low.** Medium effort because there are several distinct behaviours to build and
prove (four specialists, a refusing guardrail, confirm-then-execute, structured escalation, a
finalizing pass) even though each is individually small and the orchestration pattern is well-trodden.
Low risk because the demo scope removes the dangerous surfaces by construction: simulated data (no real
money, no real personal data), assumed identity (no sign-in/credential surface), and no external
integrations to secure. Guards that hold the risk down: the guardrail front door (refuses before any
specialist runs) and a final safety re-check; confirm-then-execute on the only state-changing action;
structured escalation that needs no live human; and a fixed acceptance script that adversarially probes
the refusal, ambiguity, and decline-to-confirm paths, not just the happy paths.

## Dual Verdict
### Case-for
The shape is a proven pattern, the four competencies mirror what real banking assistants already do at
scale, and the two domain non-negotiables (a refusing guardrail and a human-escalation path) are already
in the idea. The demo scope strips out the genuinely risky parts (real money, real personal data,
sign-in, integrations) while keeping the parts worth demonstrating (safe routing, write-safety, human
handoff). It has a small, concrete, fully observable acceptance script. Low risk, clear payoff, builds
on solid ground.

### Case-against
The independent skeptical case: a front-door guardrail, a router, four specialists, and a finalizer is a
lot of moving parts for what one capable assistant with a handful of tools and a strong safety prompt
might do — and multi-part assistants add latency, cost, and new failure modes (mis-routing, dropped
context between hops, a finalizer that softens a refusal). Worse, for a *demo*, the multi-part
orchestration is the commodity, easy half; the parts that make a banking assistant actually hard — real
account integration, regulatory compliance, and adversarial robustness against the exploits that broke
24/24 audited bots — are exactly what the simulated-data scope omits. So the build risks validating the
easy half convincingly while leaving the hard half untouched, and a reader could mistake "the pattern
runs" for "this is safe to ship."

**Confidence:** medium
**Falsifiers (what would flip this):** (1) If a single capable assistant with tools and a safety prompt
matches the routing accuracy and refusal behaviour at lower latency and cost on the acceptance script,
the multi-specialist shape is not justified — flip toward the single-agent baseline. (2) If the
audience actually needs production realism (real integration / compliance / adversarial hardening), the
simulated-data, assumed-identity scope teaches the wrong half — flip toward narrowing to the one
competency that can be made real rather than four that are simulated.

## Product Judgment
**BUILD NOW.** It is a low-risk, well-scoped reference artifact: a singular, now-clear idea (clarity
8.4) built on a proven pattern, mirroring real production capabilities, with the domain's two
non-negotiable safety behaviours already inside the scope and a small fully observable acceptance
script. The case-against is real and is respected two ways rather than dismissed: the brief is framed
explicitly as a *reference/demo* (so no one reads "the pattern runs" as "safe to ship"), and the headline
falsifier — that a single tool-using assistant might match it more cheaply — is named so the SA can
weigh the multi-specialist shape against a simpler baseline rather than assuming it. Build it now,
keep it honest about what it does and does not prove.

## Acceptance
A single scripted conversation, run end to end, in which **every** path fires once and is observed:
1. A balance question returns the correct (simulated) balance.
2. A transaction question returns the correct (simulated) transactions.
3. "Lock my card" returns a confirmation prompt and the card is locked **only after** the user confirms;
   declining the confirmation leaves the card unchanged.
4. "I didn't make this charge" produces a structured escalation record (flagged item + context) **and** a
   "a specialist will follow up" acknowledgement to the user.
5. An out-of-scope message (e.g. "what's the weather") and an unsafe message are each politely refused by
   the guardrail **without** reaching any specialist.
6. An ambiguous message is clarified or refused rather than silently mis-routed.
Each numbered line is a pass/fail check; all six passing is the proof the product does what this brief says.
