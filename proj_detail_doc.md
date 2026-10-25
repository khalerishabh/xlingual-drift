# Project Detail Document
 
## Cross-Lingual State Drift and Error Recovery in Long-Horizon LLM Agents: Characterisation and Mitigation for Indic and Code-Mixed Tasks
 
| Field | Value |
|---|---|
| Student | Rishabh Shailendra Khale |
| Registration No. | 25MAI0046 |
| Programme | M.Tech CSE (AI & ML), VIT Vellore |
| Course | MACSE698 – Dissertation I |
| Faculty guide | Dr. Vijayasherly V |
| Goal | A peer-reviewed research paper built on original experiments (not a thesis-only artefact) |
| Status (28 Sep 2026) | Review-I completed. Topic locked. **Phase 1 (design lock) in progress:** travel domain built and tested, spec drafted (Section 15.9), real-model policy built, first capability gate run (Section 15.10), **late-binding redesign built; gate v2 ready** (Section 15.11) |
| Code | github.com/khalerishabh/xlingual-drift (spec: `docs/PHASE1_SPEC.md`) |
| Document purpose | Complete hand-off of everything decided so far, so work can continue in a new chat without loss of context |
 
---
 
## How to use this document in a new chat
 
1. Attach this file and say: "This is my project detail document. Continue from Section 17 (Next actions)."
2. The 22 reference PDFs are in the Project files. Section 13 summarises each one, so a new chat only needs to open a PDF for specific details.
3. Sections 5–9 are the scientific core: problem, gaps, research questions, methodology. Treat them as the current agreed design. Section 15 lists things that **must be revisited** before building.
4. Anything marked **[UNVERIFIED]** has not been checked against a primary source and must not be cited as-is.
5. Implementation detail (tool schemas, gold format, injection catalogue, model serving) lives in the repo's `docs/PHASE1_SPEC.md`; this document records the decisions and why.
---
 
## Table of contents
 
1. Project identity and the one-paragraph summary
2. Plain-language explanation (what, why, how)
3. How we got here: decision log and rejected directions
4. Key concepts and glossary
5. Problem statement
6. Research gap (with evidence)
7. Research questions and hypotheses
8. Methodology (full design)
9. Failure taxonomy for multi-step execution
10. Expected outcomes, contributions, and publication target
11. Phase plan and timeline
12. Risks and mitigations
13. Literature: detailed notes on all 22 papers
14. Comparison matrix: what each prior work varies
15. Issues found in the final re-read (must address before building)
16. Review-I artefacts and panel preparation
17. Next actions
18. Novelty re-check keywords
19. References (IEEE) with verification status
20. Appendices: worked examples, templates, data formats
---
 
## 1. Project identity and one-paragraph summary
 
### Titles
 
- **Full title (deck and paper):** Cross-Lingual State Drift and Error Recovery in Long-Horizon LLM Agents: Characterisation and Mitigation for Indic and Code-Mixed Tasks
- **Form title (96 characters, used in VTOP/forms):** Cross-Lingual State Drift and Error Recovery in LLM Agents for Indic and Code-Mixed Tasks
- **Simple title (if a plain version is needed):** Understanding and Reducing Cross-Lingual Failures in Multi-Step AI Agents for Indic and Code-Mixed Tasks
Note: the form title drops "Long-Horizon" for length. If VTOP is cross-checked against the deck, tell the guide in advance.
 
### Aim (as on the Review-I deck)
 
> To determine whether cross-lingual degradation in multi-step LLM agents arises from progressive corruption of task state during execution — rather than from input comprehension or plan generation alone — and to develop mitigation strategies that preserve execution accuracy without sacrificing native-language output quality.
 
### One-paragraph summary
 
LLM agents work worse when users interact in languages other than English. Prior work locates this failure at two points: when the agent writes tool arguments (it writes them in the user's language instead of the English the tool expects), and when it writes its plan (the plan drops or distorts a constraint). Both findings come from single-turn tests or from the request-to-plan boundary, so neither can see what happens **while the agent executes across many steps**. This project tests whether a third failure source exists: the agent's task state (constraints, entities, intermediate values) degrades progressively as it crosses language boundaries step after step. If it does, the English-vs-non-English gap should **widen with the number of steps**. The project also studies **error recovery**, because tool error messages are always in English regardless of user language. Experiments run in a controlled tool environment we build ourselves, so correctness is checked by script with no human annotation. Languages: English, Chinese (high-resource control), Hindi, Tamil, and code-mixed Hinglish. Models: open-weight models served on Colab Pro, with hosted APIs optional.
 
---
 
## 2. Plain-language explanation
 
### What an agent does
 
A user asks: *"Mujhe kal Chennai se Delhi ki morning flight chahiye, budget 8000 ke andar."*
 
The agent works in steps:
 
1. `search_flights(origin="Chennai", destination="Delhi", date="2026-08-22")` returns 14 flights
2. `filter(time_before="12:00")` leaves 6
3. `filter(max_price=8000)` leaves 2
4. `get_seat_availability(flight_id="AI440")` shows 3 seats left
5. `book(flight_id="AI440", ...)` returns a confirmation
6. Reply to the user in Hinglish
At every step the agent carries its **state**: origin, destination, date, "morning", budget 8000.
 
### The known problem
 
Agents perform worse in non-English settings. That is established (MAPS, PolyWorkBench, MASSIVE-Agents) and is **not** our contribution.
 
### The existing explanations
 
1. **It breaks at the tool call** (Lost in Execution / MLCL). The model writes `origin="चेन्नई"` instead of `"Chennai"`. It understood the request but wrote the value in the wrong language for the machine. This is called *parameter value language mismatch*.
2. **It breaks when the plan is written** (Actionable Diagnosis / TART). The plan quietly drops the budget or the time, or swaps an entity. Executing that plan perfectly still gives the wrong answer.
### What both have in common
 
Both are about **the beginning** of the task. Neither can see what happens between step 3 and step 4.
 
### Our question
 
Suppose steps 1–3 go fine. Does the agent still remember the ₹8000 budget and "morning" at steps 5 and 6? In English, probably yes. In Hindi or Hinglish, maybe the constraint slowly fades. Nothing crashes; the agent books an afternoon flight at ₹9,200, and every individual step looks reasonable. We call this **state drift**.
 
### Why it is testable
 
- If the problem is **comprehension**, the damage happens once at the start. The English/non-English gap stays **flat** as tasks get longer.
- If the problem is **drift**, damage accumulates. The gap **widens** with length.
Run the same tasks at 2, 4, 6, 8 steps in each language and compare the slopes. A flat gap means the existing explanations are complete. A widening gap means a third failure source exists. Both outcomes are results.
 
### The second axis: recovery
 
Tool errors are always English: `KeyError: 'destination'`, `HTTP 429: Rate limit exceeded`, `ValidationError: date must be ISO 8601`. An agent working in Tamil must read an English diagnostic, map it onto a Tamil task context, and repair itself, at the moment it is already off track. Nobody has studied this; every self-correction paper we found is monolingual. Hypothesis: **recovery degrades more across languages than first-pass accuracy does.**
 
### How we test without annotators
 
We write the tools ourselves (a fake flight search, booking system, and so on). Because we authored them, we know for each task the correct tool sequence, arguments, and final state. Grading is a script diff. No human labels, no inter-annotator agreement to defend.
 
### One-line answer for the panel
 
> "Existing work looks at what is lost when the request is read and when the plan is written. We look at what is lost while the plan is being executed, and whether the agent can recover once something breaks."
 
---
 
## 3. How we got here: decision log and rejected directions
 
This section exists so a new chat does not re-propose ideas that were already evaluated and dropped.
 
### 3.1 First topic: LLM-judge reliability under language shift (dropped)
 
- **Original idea:** "Does the Judge Speak Your Language? Rubric-verification reliability for agent trajectories in non-English and code-mixed settings." Measure judge–human agreement per language on agent trajectories.
- **Tier-0 clearance** over 10 papers (the judge cluster in Section 13.5) found:
  - *Multilingual Prompt Localization for Agent-as-a-Judge* (arXiv 2604.04532) already localised the Agent-as-a-Judge prompt stack to 5 languages including Hindi over 4,950 judge runs, found backbone rankings invert across languages, and inter-backbone Fleiss' κ ≤ 0.231. It also ran the English-vs-translated judge-instruction ablation (Hindi 42.8% → 23.2%). Its limitations say a human validation study is "in progress", which meant a footrace.
  - The surviving gap was human-validated judge correctness. That required 300–500 human labels with multiple annotators.
- **Decision:** Rishabh explicitly does not want annotation-based work. He wants experimentation and training. Without human labels, the judge topic's remaining novelty was gone. **Pivoted.**
### 3.2 Several citations from the earliest chat were never verified
 
The first chat's literature list included RuVerBench (2606.29920), AgentProp-Bench (κ≈0.049), AJ-Bench (2604.18240), AdaRubric (2603.21362), Judge-LS (2606.14278), INCLUDE (2608.18131), and "Towards Reliable Multilingual LLMs-as-a-Judge" (2605.28710). None of these were in the files and several did not resolve. **[UNVERIFIED] — do not cite any of them without pulling the paper.** The verified agentic-rubric paper is *Agentic Rubrics as Contextual Verifiers for SWE Agents* (ACL 2026).
 
### 3.3 Second direction: agent execution in Indic and code-mixed settings (adopted)
 
- Moving from judging to **execution** fixed the annotation problem: agent correctness is checkable by script, judge quality is not.
- First framing: "cross-lingual state drift", with characterisation plus mitigation. The user chose **balanced**: both halves are contributions.
- The recovery axis was added from the gap analysis ("error messages are always English") and promoted from a metric to a research axis.
### 3.4 Second clearance pass (12 more papers)
 
- **Lost in Execution (MLCL)** partly overlaps the mitigation half: it already tests "pass parameters in English" prompting and pre/post-translation. None fully recover English performance. **It is single-turn by explicit design**, which is our opening.
- **Actionable Diagnosis (TART)** already did "characterise multilingual agent failure, then mitigate", but at the **request-to-plan boundary**. Our generic "characterise + mitigate" framing is taken; our **execution-time** framing is not.
- **Surviving gaps:** horizon as a controlled variable, cross-lingual recovery, code-mixed input.
### 3.5 Other gaps that were considered and parked
 
| Gap | Why parked |
|---|---|
| Code-mixed prompt injection / security (from MAPS ASB) | High impact, but red-teaming raises supervisor and ethics questions. Possible future paper |
| MAPS "answerability predicts solvability, adequacy/fluency do not" | Good methodology paper, smaller impact |
| Trajectory-level vs deliverable-level judging (PolyWorkBench judge r≈0.02) | Brings back judge work |
| Multi-agent handoff drift | Low feasibility for one student |
| Capability-gate measurement trap | Low impact alone; we account for it in model selection |
| Token/cost asymmetry for non-Latin scripts | Low novelty; easy side analysis |
 
### 3.6 Constraints fixed by the user
 
- **No human annotation.** All evaluation is programmatic or simulation-based.
- Prefers real experimentation and training over surveys.
- **Compute: Google Colab Pro (A100 GPU, 80GB VRAM; ~150GB system RAM).** No institutional lab GPU access. Earlier drafts of this document referred to a "lab GPU" — read every such reference as Colab Pro. (Corrected 28 Sep 2026.)
- **Models: open-source primary, hosted APIs optional** (decided 28 Sep 2026; Section 8.7).
- Languages: fluent in Hindi, Hinglish, and Tamil, so can author and sanity-check those directly. Does not read Chinese; Chinese text is checked by translator back-translation (Section 8.3).
- The work must be verified against literature before any gap is claimed.
---
 
## 4. Key concepts and glossary
 
| Term | Meaning in this project |
|---|---|
| **Agent** | An LLM in a loop that reasons, calls tools, reads results, and decides the next action (ReAct-style) |
| **Trajectory** | The full sequence: request → (thought, tool call, tool output)* → final answer |
| **Horizon** | Number of tool calls required to solve a task correctly. Our main experimental variable |
| **Task state** | What the agent must carry across steps: constraints (budget, time), entities (cities, IDs), intermediate values (prices, counts) |
| **State drift** | Progressive loss or distortion of task state across steps, without an obvious single error |
| **Tool schema** | Function name and parameter keys, e.g. `book_flight(origin, destination)`. Kept English, as in real systems |
| **Tool output** | What the tool returns. We control whether it is English or localised |
| **Parameter value language mismatch** | Writing a semantically correct argument in the user's language, which the English-only interface rejects (MLCL's dominant failure) |
| **Planning-grounding failure** | The plan loses or distorts entity, source, temporal, operation, or answer-format commitments (TART's taxonomy) |
| **Seam** | A language boundary inside one trajectory, e.g. a Tamil request meets an English tool output |
| **Code-mixing** | Switching languages **within a sentence**: "Mujhe kal Delhi ki flight chahiye" |
| **Transliteration** | Writing a language in another script: Hindi words in Roman letters, "Mujhe kal Delhi jaana hai" |
| **Hinglish / Tanglish** | Code-mixed Hindi–English / Tamil–English, usually typed in Roman script |
| **Gold trajectory** | The correct tool sequence, arguments, and terminal state for a task, known by construction |
| **Deterministic verifier** | Script comparing an agent trajectory to the gold trajectory |
| **Drift slope** | How fast the non-English gap grows per extra step. The key quantity for RQ1 |
| **Constraint survival** | Whether a constraint from the original request is still satisfied at the final step |
| **Decoy** | A data row that is the correct answer only if one specific constraint is lost. Lets a wrong outcome be traced to the constraint that drifted (Section 15.9) |
| **First-error step** | The step index where the trajectory first deviates from gold |
| **Recovery rate** | Share of injected-failure runs where the agent reaches the correct final state, computed only on tasks it solves without injection |
| **Lenient interface** | Tools accept multilingual aliases, removing MLCL's argument failure |
| **Oracle plan** | The agent is given the correct plan, removing TART's plan failure |
| **Language pinning** | Keeping the agent's internal state/reasoning in a fixed language while replying in the user's language |
| **Thinking mode** | A model setting in which it writes out reasoning before acting. A study-wide constant here, fixed from the capability gate (Section 8.7) |
| **Capability gate** | The entry test for a model: it must solve horizon-2 tasks in every language, or there is no room for a slope to show |
| **Reliability vs validity** | Reliability = consistent results. Validity = correct results. Judge papers mostly measured reliability. We avoid this by using deterministic ground truth |
| **Cohen's κ / Fleiss' κ** | Chance-corrected agreement for two raters / many raters. Relevant to the judge literature, not to our main design |
| **SDG 10** | UN Sustainable Development Goal: Reduced Inequalities |
| **TRL 3** | Technology Readiness Level 3: experimental proof of concept |
 
### Code-mixing vs other variants
 
| Variant | Example |
|---|---|
| Pure Hindi (Devanagari) | मुझे कल दिल्ली की उड़ान चाहिए |
| Transliterated Hindi (Roman script, no English words) | Mujhe kal Delhi ki udaan chahiye |
| Code-mixed Hinglish | Mujhe kal Delhi ki flight chahiye |
| Machine-translated English | I need a flight to Delhi tomorrow → clean Hindi |
 
Transliteration is a **script** change. Code-mixing is a **language** change inside a sentence. Our design can treat them as separate variables.
 
### Why code-mixing breaks agents
 
1. **Script ambiguity in arguments.** "Chennai" may arrive as *Chennai*, *chennai*, or *சென்னை*. The tool has one canonical form.
2. **No clean language signal.** Language-ID routing has nothing stable to key on.
3. **Ambiguous output expectation.** Should the reply be Hinglish, English, or Hindi? Models differ, which itself is measurable.
### Why code-mixing is a defensible novelty claim
 
Every multilingual agent benchmark we found is built by **translating** an English one (MAPS translates GAIA/SWE-Bench/MATH/ASB; MLCL translates BFCL; MASSIVE-Agents reformats MASSIVE; TART uses Google-translated GAIA-MAPS; OmnilingualGAIA2 machine-translates GAIA2; BabelArena machine-translates four benchmark families including VitaBench and DeepPlanning). Translation cannot produce code-mixing; it has to be authored by someone who speaks that way. This is a structural gap, not an oversight, and it holds across every multilingual agent benchmark found to date (last checked 28 Sep 2026, Section 15.7).
 
---
 
## 5. Problem statement
 
### Formal version
 
> Multi-step LLM agents degrade substantially when operating in non-English and code-mixed settings. Existing work attributes this degradation to two sources — parameter realisation errors at the tool-call interface, and grounding losses during plan generation — but both are established under single-turn evaluation or at the request-to-plan boundary. Neither setting can observe what happens across successive execution steps. Consequently, it is unknown whether cross-lingual agent failure is a fixed penalty incurred at input, or a penalty that compounds as task state is carried across language boundaries during execution. It is further unknown whether agents can recover from execution errors in non-English settings, given that tool diagnostics are emitted in English regardless of user language.
 
### Plain version
 
> We know agents get worse in Indic languages. We don't know whether they misunderstand you at the start or slowly lose the thread while working. Those are different problems with different fixes, and nobody has separated them. We also don't know whether an agent working in Tamil can fix itself after an error, when the error message is in English.
 
### One line
 
> Is cross-lingual agent failure a comprehension problem or an accumulation problem, and what happens when the agent has to recover?
 
### Purpose
 
To make multi-step agents reliable for people who don't operate in English. As agents take real actions (booking, filing, transacting), a systematic gap for Hindi or Tamil speakers becomes an infrastructure-level inequality. You can't fix what you haven't located, so the project first locates it.
 
---
 
## 6. Research gap (with evidence)
 
1. **Failure is localised at input and at planning, not during execution.** MLCL (Luo et al., 2026) is single-turn by design: "our evaluation is based on the vanilla subset of the Berkeley Function Call Leaderboard to focus on single-turn tool-calling scenarios". TART (Pahuja et al., 2026) studies the planner "as the request-to-action interface". Neither contains multi-step state to corrupt. OmnilingualGAIA2 (Caciolai et al., 2026) does evaluate full multi-tool trajectories and finds the gap concentrated in tool-orchestration, but does not vary the number of required steps as a controlled variable, so it cannot say whether the gap is fixed or compounding (Section 15.7).
2. **No study controls trajectory length as a variable.** MAPS reports that degradation correlates with the proportion of translated input tokens; PolyWorkBench observes "cross-lingual coordination errors" where content drifts across a trajectory; step count is uncontrolled in both. DeepPlanning has parallel ZH/EN tasks with 2–7 day complexity levels but **averages results across languages** and never reports a language × complexity interaction (see Section 15). BabelArena (Kuang et al., 2026) reports that low-resource-language trajectories on the same tasks have "similar numbers of turns" to English ones — i.e. horizon is observed, not manipulated, so it cannot test accumulation either (Section 15.7).
3. **Cross-lingual error recovery is unexamined.** QueryAgent/ERASER and MASC do step-level self-correction, both monolingual, both assuming feedback in the agent's operating language. ToolBench-X (Tian et al., 2026) runs controlled fault injection with defined recovery paths, but entirely in English (Section 15.7).
4. **Existing mitigations leave an unexplained residual.** MLCL: prompting, pre- and post-translation "reduce certain error types but fail to consistently recover English-level performance". MAPS: deterministic translation to English recovers roughly 5 points but a gap remains (GAIA 12%, ASB 14%). Single-turn settings cannot attribute this residual.
5. **Code-mixed input is absent from multilingual agent evaluation.** All benchmarks are translation-built, which normalises code-mixing away — including the two most recent additions, OmnilingualGAIA2 and BabelArena (Section 15.7).
6. **Independent behavioural evidence consistent with execution-time degradation.** OmnilingualGAIA2 finds that, off English, agents shift toward exploratory reads and away from state-changing writes (write-action share of tool calls falls ~1–2.5 pp across three agents) — a behavioural signature consistent with the state-drift hypothesis, though not itself a horizon-controlled test of it.
---
 
## 7. Research questions and hypotheses
 
Each RQ maps to one results section, so the RQs define the methodology.
 
| RQ | Question | Hypothesis | What would falsify it |
|---|---|---|---|
| **RQ1 Accumulation** | Does the English/non-English gap widen as required steps increase? | Yes: the language × horizon interaction is significant and positive for Hindi, Tamil, and Hinglish | Parallel success curves (no interaction) |
| **RQ2 Independence** | Does the widening persist after the two known sources are removed (lenient interface + oracle plan)? | Yes: drift remains | Interaction disappears under both controls, meaning drift was just MLCL/TART failures repeating |
| **RQ3 Localisation** | At which execution stage and which seam does the excess failure occur? | State carryover and entity handling, not intent parsing; tool-output seam more costly than request seam | Excess concentrated in intent parsing (a comprehension story) |
| **RQ4 Recovery** | Does recovery from injected errors degrade more across languages than first-pass accuracy? | Yes, especially when the error message is English and the task is not | Recovery gap ≤ first-pass gap |
| **RQ5 Mitigation** | Does a dynamic, language-neutral state representation close the gap, and at what cost? | Partly, with some loss in native-output quality | No gain beyond TART-style static contracts or pre-translation |
 
**RQ2 is what makes this a paper rather than a benchmark.** Without it a reviewer says "your drift is just MLCL's failure happening at every step".
 
**Priority if time runs short:** RQ1 + RQ2 + RQ4 form a complete paper. RQ3 comes almost free from the same runs. RQ5 is the part to shrink.
 
---
 
## 8. Methodology (full design)
 
### 8.1 The environment
 
- A mock tool world written by us: **19 tools across 3 domains** — travel booking (11, built), shop/orders (5, specified), records/support (3, optional). Tool inventory in `docs/PHASE1_SPEC.md` §4.
- Tools are **deterministic**: the same input always gives the same output. Backed by small in-code tables (SQLite only if joins become necessary).
- Tool schemas mirror real API shapes (BFCL-style JSON schemas) to blunt the "toy environment" critique. Unknown or missing arguments are rejected, as a strict real API would.
- For every task we store the **gold trajectory**: tool sequence, arguments, terminal state, constraint set, a recovery fallback, and one **decoy per constraint** (Section 15.9).
- Two interface modes:
  - **Strict:** exact canonical values required, as in BFCL/MLCL.
  - **Lenient:** spelling and script variants resolve to the form a parameter already expects (`Chennai`, `chennai`, `चेन्नई`, `சென்னை`, `钦奈` → Chennai). Lenient **never** lets a name stand in where a code is required, so it removes MLCL's failure without shortening the chain.
- Built-in hooks: failure injection targeted at a named tool (preferred) or a step index, and tool-output language switching (English vs localised).
Precedents to borrow from: DeepPlanning (isolated sandbox per task, 7 sub-databases and 9 APIs for travel; 3 sub-databases and 15 APIs for shopping); WebArena (self-hosted reproducible environment); MLCL (language-invariant execution interface); ToolBench-X (structured hazard taxonomy and defined recovery paths, English-only — see Section 15.7).
 
### 8.2 Controlling horizon without confounding it (the most important design choice)
 
If longer tasks also have longer requests, more non-English text goes in, which is exactly MAPS's "more translated input, more degradation" effect. We could not separate drift from that.
 
**Fix:** keep the user request **identical** across horizons and let the **environment** determine how many steps are needed.
 
**How the environment sets the horizon (built 28 Sep 2026).** Three things are held constant across horizons: the request text, the set of tool names the agent sees, and the **final decision set** (the candidates visible when the agent chooses). Only the values each tool *requires* change. A value that only another tool can produce (a city code, a hold token, a fare class, a passenger id) forces that tool into the chain. The agent learns requirements from the schemas, never from error messages, so horizon stays separate from recovery.
 
Example (travel_017): "Book the latest morning flight from Chennai to Delhi tomorrow, under ₹8000, with an aisle seat and a Jain meal."
 
| Horizon | What changes | Gold chain |
|---|---|---|
| 2 | search accepts city names and inline filters; booking takes seat type and meal by name | search → book |
| 4 | search requires city **codes** | resolve city ×2 → search → book |
| 6 | no inline filters; booking requires a **hold token** | resolve ×2 → search → filter → check seats (hold) → book |
| 8 | seat check requires **fare class**; booking requires **passenger id** | h6 + fare-class lookup + passenger-profile fetch |
| 10 | booking requires a **seat id** and **meal code** | h8 + seat map + meal options |
| 12 | booking also requires a **document id** and **payment id** | h10 + travel documents + payment methods |
 
**Early vs late constraints (added 28 Sep 2026 after gate v1, Section 15.11).** Early constraints (time window, budget, objective) are applied when the flight is chosen, around step 1–6. Late constraints (seat type, meal) are committed only in the final booking call, at step *h*, so the distance they must be carried grows with horizon. If drift exists, late-constraint survival should fall with horizon faster in non-English conditions than early-constraint survival does; the early constraints are a within-episode control for comprehension.
 
All horizons are replay-tested, and a test checks that the decision set is identical at every horizon, so longer horizons are longer chains, not harder choices. **Residual confound:** schema text grows slightly with horizon (more required parameters). Log schema token counts per horizon and add them as a covariate if they vary materially.
 
**Scale:** ~40 task templates × 6 horizons (2–12) = 240 tasks per language. Horizons were extended from 2–8 to 2–12 after gate v1 showed a ceiling at h8 (Section 15.10). Gold for every template and horizon is generated by `tasks/build_gold.py`, which refuses any file that breaks the design rules.
 
### 8.3 Language conditions
 
| Condition | Purpose |
|---|---|
| English | Baseline |
| **Chinese (Simplified)** — high-resource control, chosen 28 Sep 2026 | Separates "non-English" effects from "low-resource" effects |
| Hindi (Devanagari) | Indic, Indo-Aryan |
| Tamil (Tamil script) | Indic, Dravidian; different script and agglutinative morphology |
| Hinglish (Roman script, code-mixed) | The condition translation cannot produce |
| Optional: Romanised Hindi without English words | Isolates script from code-mixing |
| Optional: Tanglish | Second code-mixed language |
 
**Why Chinese:** DeepPlanning provides ZH/EN parallel tasks with complexity levels, giving a cheap external check on RQ1 (Section 8.12). Spanish was the alternative (easier to verify, no external check). Rishabh does not read Chinese, so zh text is verified by **translator back-translation plus the answerability check** instead of author review, and the template records that method in its `verification` field.
 
**Equivalence:** templates have slots. Each template is written once per language (40 × 5 = 200 short texts); entities fill slots. Rishabh verifies Hindi, Tamil, and Hinglish himself (authoring, not an annotation study). Automatic checks: back-translation similarity, an **answerability** check (MAPS found answerability, not adequacy or fluency, predicts whether a translated task stays solvable), and a **script-hygiene test** (each non-Latin request contains only its own script; Section 15.9). The gold trajectory is language-independent by construction. **Freeze all templates before running any model.**
 
### 8.4 The two neutralising controls (RQ2)
 
| Control | Removes | How |
|---|---|---|
| **Lenient interface** | MLCL's parameter value language mismatch | Tools accept multilingual aliases of the expected form (never a shortcut past a required step) |
| **Oracle plan** | TART's plan-grounding failures | The agent receives the correct step list and only has to execute it |
 
Full factorial: {strict, lenient} × {own plan, oracle plan}. If the language × horizon interaction survives under lenient + oracle, accumulation is a separate failure source. That single cell carries the novelty claim.
 
### 8.5 Seam placement (RQ3)
 
Vary which trajectory parts are non-English. Tool schemas stay English (realistic).
 
| Seam condition | Request | Tool outputs | Error messages |
|---|---|---|---|
| S0 | EN | EN | EN |
| S1 | L | EN | EN |
| S2 | L | L | EN |
| S3 | L | L | L |
 
S1 is the realistic deployment case. Comparing S1 vs S2 shows whether the English tool-output crossing costs more than the request crossing.
 
### 8.6 Failure injection (RQ4)
 
A named tool fails deliberately at an early, middle, or late position in the chain (position table in `docs/PHASE1_SPEC.md` §7). Targeting a tool rather than a step index means the injection hits the same logical point even if a model takes extra steps.
 
| Error type | Example message | Correct recovery | Status |
|---|---|---|---|
| Transient | `HTTP 429: Rate limit exceeded. Retry after 2s.` | Retry the same call | Built |
| Not found / exhausted | `NotFound: flight 6E212 has 0 seats available` | Take the next-best option (gold `recovery_fallback`); the flight stays sold out for the rest of the episode | Built |
| Validation (specification drift) | `ValidationError: 'date' must be ISO 8601 (YYYY-MM-DD)` | Reformat the argument; the new format persists | **Placeholder**: currently one-shot, so it behaves like transient. Do not report as a separate condition until built |
 
Each message comes in two versions: English (realistic) and localised into the task language (catalogue built for en, zh, hi, ta, hinglish). That 2 × language design directly tests whether the English diagnostic is the bottleneck.
 
**Key rule:** recovery rate is computed only on (task, model, language) cells the agent solves **without** injection. This separates "can't recover" from "couldn't do the task anyway". "Recovered" means reaching the correct answer *given the episode state* (the best remaining option), not merely booking something.
 
Borrow from QueryAgent/ERASER: the environment "speaks out" and error types are distinguished. Borrow from MASC: controlled fault injection, and the observation that many errors occur early (first 20% of steps in Who&When's algorithm-generated subset). Borrow from ToolBench-X: the structured hazard taxonomy (Specification Drift, Invocation Error, Execution Failure, Output Drift, Cross-source Conflict) and the discipline of pairing every injected failure with at least one valid recovery path — cite explicitly as the closest methodological precedent, extended here to the cross-lingual axis (Section 15.7).
 
### 8.7 Models
 
**Open-source models are the primary setup; hosted APIs are optional (decided 28 Sep 2026).**
 
Why open-source is sufficient here:
- The research question needs models **above the capability gate**, not the strongest models available. What is measured is whether the gap *widens with horizon*.
- Recent open models already run as multi-step multilingual agents: OmnilingualGAIA2 ran Gemma 4 31B and Qwen 3.6 27B / 35B-A3B across 10 languages including Hindi. Its same-family Qwen scale ladder found the gap **widening** with size, which pre-empts the "it vanishes in bigger models" objection.
- Open weights are reproducible (fixed seeds, no silent API updates or retirement), free on Colab, required for the optional SFT ablation, and allow a possible follow-up: probing whether a constraint is still represented in the model's hidden state at step *k*.
- A frontier API model on a stratified subset stays available as an **optional robustness check** through the same code. It is not a blocker.
**Setup:**
- **A backbone is a model plus its exact weights, precision and serving stack** (decided 28 Sep 2026). Every condition a backbone is compared on (languages, horizons, controls) must run on the identical backbone; different backbones are expected, and model is a random effect in the analysis. Precision is part of the backbone because **quantization degrades non-Latin-script languages most** [23], so mixing BF16 and FP8 episodes of the same model would manufacture a language effect. Colab assigns L4 24GB, A100 40GB or A100 80GB by session, so each backbone's precision is chosen to fit every GPU it will run on and is never changed mid-study. **Gate v2 onward uses the official Qwen/Qwen3.6-27B-FP8** (fits 40GB and 80GB A100s); gate v1 (BF16, 80GB) was a design pilot and is not pooled. Enforced in code: the run config pins model, revision, parsers and minimum GPU memory; the notebook serves exactly that and stops on an undersized GPU; the runner stamps every episode with the serving fingerprint and refuses to extend a log produced under a different model, revision or vLLM version.
- **3–4 backbones**, all ≤32B, served with **vLLM** on Colab Pro. First candidates: **Qwen/Qwen3.6-27B** (`--tool-call-parser qwen3_coder --reasoning-parser qwen3`) and **google/gemma-4-31B-it** (`--tool-call-parser gemma4 --reasoning-parser gemma4` plus the Gemma 4 tool chat template). Both parser settings were checked against the vLLM recipes (Sep 2026). Add a smaller model for a size contrast, and an Indic-tuned model only if one passes the gate.
- **Capability gate:** a model must solve horizon-2 tasks in **every** language, not only English. A model that fails h2 in Tamil leaves no room for a Tamil slope. Weak models fail everywhere, which hides the language effect (Prompt Localization found near-zero cross-language variation for weak backbones).
- **Thinking mode is a study-wide constant: ON** (decided from the first gate, Section 15.10). Thinking solved more Tamil and Hinglish episodes (11/24 vs 2/24), took fewer unnecessary steps, and its reasoning traces are what located the failures; the cost (~1,400 vs ~400 completion tokens per episode) is negligible on vLLM.
- **One policy for every model** (`agent/policies/openai_compat_policy.py`), talking to any OpenAI-compatible endpoint: vLLM for real runs, Ollama on a laptop for debugging only, or a hosted API. Same versioned English system prompt (`agent/prompts/system_v1.txt`, includes the session date) and the same loop for all conditions (MASSIVE-Agents showed prompt format alone can move AST accuracy by more than 20 points, e.g., Claude 3 Opus 13.03% → 35.90%).
- Temperature fixed per study (0.6 in the gate); **3 seeds** per cell. Endpoint failures are logged but never scored.
- **Dropped from the shortlist (28 Sep 2026):** Llama 3.1 70B, Qwen3-Next-80B-A3B, Qwen3-VL-235B-A22B, DeepSeek V3.2 — they don't comfortably fit a single 80GB A100, even quantized, and there is no institutional lab GPU behind them.
### 8.8 Metrics
 
| Metric | Definition | Answers |
|---|---|---|
| Task success | Booked the correct answer given the episode state (the gold answer when nothing was injected) | RQ1, RQ2 |
| Success × horizon per language | Curve per language | RQ1 |
| **Drift slope** | Interaction coefficient: extra per-step penalty for language L vs English | RQ1, RQ2 |
| First-error step | Index of first deviation from gold | RQ1 (early = comprehension, spread = drift) |
| **Constraint survival** | Each request constraint (route, date, time, budget, objective) checked on the final booking. Readable from the outcome because every constraint has a decoy | RQ3, the most direct drift measure |
| Per-stage error rate | Share of failures by taxonomy stage (Section 9) | RQ3 |
| Fact displacement | An argument value (flight id, hold token, fare class, passenger id) that never appeared in any earlier tool output | RQ3 |
| Extra steps | Steps taken beyond gold length | RQ1 side |
| Recovery rate | Correct terminal state after injection, conditioned on no-injection success | RQ4 |
| Retry count / recovery latency | Steps between error and correct continuation | RQ4 |
| Propagation depth | Steps corrupted downstream of one error | RQ4 |
| Output language fidelity | Language-ID of final answer matches the user's language | RQ5 cost |
| Grounded-value accuracy | Values in the final answer appear in tool outputs | RQ5 cost |
| Tokens / cost per run | Completion and reasoning tokens per episode; also a side analysis of script cost | Side |
 
### 8.9 Statistical analysis
 
**Primary model (logistic mixed-effects):**
 
```
success ~ language * horizon * control + (1 | template) + (1 | model) + (1 | seed)
```
 
- The **language × horizon** coefficient is the drift. Longer tasks are harder in English too; we compare **slopes**, not raw scores.
- Test the interaction within the lenient + oracle cell for RQ2.
- Report effect sizes with bootstrap 95% CIs (resample templates). Holm–Bonferroni across languages.
**Secondary (survival analysis):** discrete-time hazard of the first error by step. Does the per-step hazard rise faster for Tamil than English? This is sharper than end-task success and uncommon in agent papers.
 
**Recovery:** compare recovery gap vs first-pass gap per language with a paired test over templates.
 
### 8.10 Mitigation (RQ5)
 
| Method | Idea | Source |
|---|---|---|
| **M1 Dynamic state ledger** | A language-neutral JSON of constraints, canonical entities, and **values learned from tool outputs**, updated after every tool call and re-injected each step | Ours |
| **M2 Re-anchoring** | Every *k* steps, the agent re-checks accumulated state against the original request | Ours |
| **M3 Error localisation** | Error messages translated into the task language before the agent sees them | Ours |
| Baseline: unpinned agent | Plain ReAct loop, no mitigation | ReAct [6] |
| Baseline: PT and PRE | PT: "pass all parameter values in English". PRE: translate the request to English before the agent sees it | MLCL [3]; PRE also in MAPS [1] |
| **Baseline: TART-style static representation** | Request converted **once** into fixed JSON, injected every step, never updated. The baseline M1 must beat | TART [4] |
 
**Differentiation from TART is essential.** TART converts the query once into a structured representation (entities, sources, time, operations, answer format) and injects that fixed representation into all agents. M1 differs in two ways: it is **updated during execution** with values from tool outputs, and it targets the carryover of **intermediate state**, which TART does not model. If M1 does not beat a TART-style baseline at long horizons, the mitigation claim must shrink. TART's converter system prompt and output schema are published in its Appendix B, so the baseline uses them verbatim (Section 15.1).
 
**Measuring the cost without annotators:** output language fidelity (language ID), grounded-value accuracy, and whether the reply matches the user's language/register. If an LLM judge is used at all, it is secondary and labelled (the judge papers in Section 13.5 show why). Collecting a final user-facing reply requires one more model turn after the booking; the loop does not do this yet (spec §9 open items).
 
**Optional GPU ablation:** SFT one small open model (≤8–14B, to fit comfortably alongside everything else on a single 80GB A100) on synthetic trajectories that use M1, to test whether the behaviour can be learned rather than prompted, run on Colab Pro. Do not build the paper on multi-step agentic RL (unstable; infrastructure-heavy). If SFT fails, the paper still stands.
 
### 8.11 Run budget (approximate)
 
- Full core grid: 160 tasks × 5 languages × 4 models × 3 seeds ≈ **9,600 runs**. Controls, seams, recovery, and mitigation add roughly 2–3× on top of that, all scripted.
- **Temporarily descoped (28 Sep 2026):** the full 9,600-run grid is deferred. Given current compute (Colab Pro, single A100) and time budget, Phase 5 starts with a **reduced pilot-scale grid** — fewer templates and/or 1 seed instead of 3 — sized after the Phase 4 pilot shows where the effect is visible, rather than committing to the full grid up front. The full grid is a stretch goal if compute/time allow later, not a blocking requirement for a first paper draft.
- Open models run one at a time on the single GPU. Episodes are short (at most ~12 tool calls), so throughput is limited mainly by thinking-mode token counts, which the capability gate measures. Runs are resumable across Colab disconnects.
### 8.12 External validation (answers the "toy environment" critique)
 
1. **DeepPlanning Travel (ZH/EN parallel, 2–7 day complexity):** compute a ZH vs EN × day-length interaction on its released data/sandbox. A cheap, external check of RQ1 on a real benchmark, from a paper that averaged across languages. Enabled by choosing Chinese as the control language.
2. **MAPS GAIA subset bucketed by required step count:** a descriptive check on naturally long tasks.
---
 
## 9. Failure taxonomy for multi-step execution
 
Our stage taxonomy extends MLCL (single-turn argument errors) and TART (plan-time grounding) into execution.
 
| Stage | Failure | Detection (scripted) | Relation to prior taxonomies |
|---|---|---|---|
| Intent parse | Wrong goal pursued | Gold tool sequence never attempted | Comprehension errors (PolyWorkBench) |
| Tool selection | Right intent, wrong tool | Called tool ≠ gold at step *k* | MLCL function-level error; MASSIVE "wrong function" |
| Argument construction | Wrong value | Argument diff vs gold | MLCL wrong/related value |
| Entity handling | Entity mutated, transliterated, or dropped | Canonical entity absent in args | MLCL language mismatch; TART entity grounding |
| Schema handling | Parameter **keys** translated; arguments not valid JSON | Call rejected by schema or unparseable | New for multilingual execution |
| Result interpretation | Next step inconsistent with previous output | Step *k+1* contradicts output *k* | — |
| **State carryover** | Constraint satisfied early, violated later | Constraint survival check; booked flight matches a decoy | **Our core category** |
| **Fact displacement** | Retrieved value misstated later | Argument value absent from all earlier tool outputs | DeepPlanning A3 |
| Language control | Wrong output language, reasoning leak | Language ID | — |
| Termination | Early stop, text reply instead of acting, or loop | Step count vs gold; step-limit flag; repeated calls | — |
| Final grounding | Answer contains a value no tool returned | Value not in any tool output | TART answer-format (partly) |
| **Recovery** | No repair after injected error | Terminal state after injection | **Our second axis** |
 
---
 
## 10. Expected outcomes, contributions, and publication target
 
### Contributions
 
1. **Finding:** the first horizon-resolved account of cross-lingual agent failure, showing whether it compounds even with the two known causes controlled.
2. **Finding:** the first measurement of cross-lingual error recovery.
3. **Method:** a dynamic state-ledger mitigation with its accuracy/quality trade-off quantified, compared against TART-style and translation baselines.
4. **Artefact:** an open environment and benchmark with deterministic grading and **authored code-mixed Hinglish tasks**, which translation-built benchmarks structurally cannot produce. Fully reproducible with open-weight models.
### The result if the hypothesis holds
 
> Agents understand Indic requests about as well as English ones. They lose track faster while executing them, and are much worse at recovering when something breaks. The excess failure concentrates in state carryover and post-error repair, not comprehension. A dynamic language-neutral state recovers part of the gap, at some cost to output quality.
 
### If the hypothesis fails
 
A flat gap means the field's input/plan explanations are complete, which is still publishable ("multilingual agent failure is front-loaded; fix the interface and the plan"). The recovery result and the code-mixed benchmark stand independently.
 
### Venue
 
- Primary: ACL/EMNLP Findings via ARR.
- Fast first hit: a multilingual or agents workshop (the Finno-Ugric paper appeared at the Workshop on Multilingual Multicultural Evaluation; IndicMMLU-Pro at GEM).
- Review-I stated outcome: Conference / Journal (Scopus) publication.
### SDG and TRL
 
- **SDG 10 (Reduced Inequalities):** unreliable agents for non-English speakers are an equity failure in AI infrastructure. Secondary: SDG 9.
- **TRL 3:** experimental proof of concept. Path to TRL 4 if the environment and audit protocol are packaged as a reusable harness validated on external task sets.
---
 
## 11. Phase plan and timeline
 
| Phase | Work | Duration | Deliverable / gate |
|---|---|---|---|
| 0 | Novelty re-check (Section 18) | 1–2 days | No collision on horizon × language, recovery, dynamic state |
| 1 | Design lock: tool specs, 40 templates, horizon scheme, gold format, error types, seam conditions | 2 wk | Frozen spec document (`docs/PHASE1_SPEC.md`; draft exists, travel built) |
| 2 | Environment: tools, strict/lenient modes, verifier, injection and language hooks | 2–3 wk | Env passes unit tests; gold trajectories replay correctly |
| 3 | Language authoring: 200 template texts, equivalence and answerability checks | 2 wk | Frozen multilingual task set |
| 4 | **Pilot:** 1 model, 10 templates, all conditions | 1 wk | **Go/no-go:** is a language × horizon interaction visible at all? |
| 5 | Core runs (RQ1–RQ3), reduced grid (Section 8.11) | 3 wk | Mixed-effects results, drift slopes |
| 6 | Recovery runs (RQ4) | 2 wk | Recovery vs first-pass gap |
| 7 | Mitigation (RQ5) + optional SFT | 3 wk | M1–M3 vs baselines |
| 8 | External validation (DeepPlanning ZH/EN) | 1 wk | Replication on a real benchmark |
| 9 | Analysis and writing | 3–4 wk | Paper draft + artefact release |
 
Phases 1 and 2 are overlapping in practice: the travel domain was built while the spec was being written, which is how the load-bearing-constraint problem was found (Section 15.9). The capability gate is run early, on one template, before authoring the remaining 39: if task difficulty is wrong for the chosen models, it is cheaper to learn that now.
 
**The pilot is the safety valve.** If no model shows an interaction, you learn it in about week 8. Pivot options already in hand: make recovery the headline, or the seam-placement result.
 
---
 
## 12. Risks and mitigations
 
| Risk | Mitigation |
|---|---|
| Effect too small or absent | Pilot early; extend horizon to 10–12; pick models above the capability gate |
| Ceiling (frontier models barely fail) / floor (weak models fail everywhere) | Choose horizons and models from pilot data |
| "Toy environment" critique | Real API-shaped schemas; DeepPlanning ZH/EN validation; MAPS GAIA step-bucket check |
| Reviewers question an open-models-only study ("does it hold for GPT/Claude?") | OmnilingualGAIA2's scale ladder shows the gap widening with size; optional frontier-API subset through the same code; stated in limitations |
| Open models below the gate in Tamil | Gate checks every language, not just English; pick models that pass all five; a Tamil gap above the floor is itself a result |
| Thinking mode changes results | Fixed study-wide from gate data; reasoning tokens logged per episode |
| Colab assigns different GPUs per session (L4 24GB / A100 40GB / A100 80GB), tempting a mix of precisions for one model | Each backbone's weights and precision pinned in config; notebook refuses undersized GPUs; runner refuses to mix setups in one log. Quantization hurts non-Latin scripts most [23], so this is a validity issue, not just reproducibility |
| Hinglish authoring bias (single author) | Freeze templates before any model run; release them; automatic answerability checks |
| Control language (Chinese) not readable by the author | Translator back-translation + answerability check; zh templates frozen only after both pass; method recorded per template |
| A constraint that never changes the answer, making drift on it invisible | Authoring rule "every constraint changes the answer", with one decoy per constraint, enforced by a test on every gold file (Section 15.9) |
| Silent script corruption in authored text | Script-hygiene test on every non-Latin request (Section 15.9) |
| Overlap with TART on mitigation | Dynamic ledger vs static contract; TART-style baseline required, built from TART's published prompt (Section 15.1) |
| Scooping by the MAPS/TART group (Fujitsu/Cohere), who published MAPS then TART within months | Re-run novelty checks now and monthly; move fast to a workshop version |
| DeepPlanning authors publish a language × complexity breakdown | Our controls (RQ2), recovery axis, and Indic/code-mixed languages still differentiate |
| Translation noise read as drift | Equivalence + answerability checks before any run |
| Prompt-format confound | One policy, one versioned system prompt, identical across all conditions |
| Schema length grows with horizon | Log schema token counts per horizon; covariate if material (Section 8.2) |
| Colab disconnects mid-run; flaky server read as agent failure | Resumable runner; endpoint failures logged as `infra_error` and never scored |
| Well-resourced labs (Meta, Alibaba) publishing adjacent multilingual agent benchmarks faster than a solo student can react | Monthly novelty re-checks (Section 18); each new entrant checked specifically against horizon-control, recovery, and code-mixing — the three axes no entrant has covered as of 28 Sep 2026 (Section 15.7) |
| Full 9,600-run grid not feasible on current compute/time budget | Start with a reduced pilot-scale grid (Section 8.11); scale up only if compute or time allow later; the core RQ1/RQ2/RQ4 claims do not require the full grid |
 
---
 
## 13. Literature: detailed notes on all 22 papers
 
Grouped by role. For each: citation, verified venue, what they did, key numbers, limitations, relevance, and what we borrow.
 
### 13.1 Core papers (the ones reviewers will compare us to)
 
#### [1] MAPS: A Multilingual Benchmark for Agent Performance and Security
 
- **Authors / venue:** Hofman, Brokman, Rachmil, Bose, Pahuja, Shimizu, Starostina, Marchisio, Goldfarb-Tarrant, Vainshtein (Fujitsu Research of Europe, Fujitsu, Cohere). *Findings of ACL: EACL 2026*, pp. 821–845. **Verified.** Data: huggingface.co/datasets/Fujitsu-FRE/MAPS
- **What:** Translates four agentic benchmarks into 11 languages: GAIA (165 tasks), SWE-Bench (100), MATH (140 hard problems), Agent Security Benchmark (400 prompts) = 805 tasks, 9,660 language instances.
- **Languages:** German, Spanish, Portuguese (BR), Japanese, Russian, Chinese, Italian, Arabic, Hebrew, Korean, Hindi (+ English). No Tamil, no code-mixing.
- **Translation pipeline:** hybrid NMT (Google Translate) + LLM enhancement + integrity checks; native-speaker verification of a quarter of the data. Answerability 94.2% (95% CI 92.0–96.4%). Key finding: **answerability, not adequacy/fluency, predicts whether a translated task stays solvable.**
- **Agents:** one per benchmark, native configs: OpenDeepResearch (GPT-o1) for GAIA, MathChat (GPT-4) for MATH, SWE-agent (GPT-4.1) for SWE-Bench, ASB infrastructure (GPT-5-mini). 3 runs per language.
- **Metric:** *Multilingual Effect* = English score minus mean of the 11 non-English scores (sign inverted for ASB).
- **Results:** GAIA drops up to 16%; ASB attack success rises up to 27%; SWE-Bench and MATH barely move. Degradation correlates with the **proportion of translated natural-language tokens** in the input.
- **Translation ablation:** GAIA EN 47.4% vs non-English mean 35.8%; deterministic pre-translation 42.0%; agent-decides translation 40.9%. ASB ASR EN 32.7% vs 47.3%; 40.4%; 43.3%. Translation recovers ~5 points; a gap remains (GAIA 12%, ASB 14%), so translation bias alone cannot explain it.
- **Cross-model / unified backbone:** same pattern with GPT-4o, Qwen-2, and a GPT-5-mini unified backbone.
- **Planning analysis:** for tasks solved in English but failed in all other languages, ODR's English planning step is more faithful to the instruction in 85.7% of cases (SWE-agent: 25%).
- **Limitations for us:** inherited fixed tasks; step count uncontrolled; one agent per benchmark; no recovery analysis.
- **Relevance:** establishes the problem and the dose-response on input volume. Our horizon design must hold input volume fixed to avoid simply re-measuring this.
- **Borrow:** answerability check, Multilingual Effect as a summary metric, deterministic-translation baseline.
#### [2] PolyWorkBench: Benchmarking LLM Agents for Cross-Lingual Long-Horizon Workflows
 
- **Authors / venue:** H. Li, Y. Liu, Z. Zhang, Z. Liu, X. Lou, J. Xu, F. Meng, K. Huang (Beijing Jiaotong University; Weixin AI, Tencent). arXiv 2607.06008v3 (17 Aug 2026). **Verified.**
- **What:** 67 authored tasks across 5 domains (commerce, knowledge work, legal analysis, localisation, manufacturing), 10 languages (EN, ZH, JA, KO, FR, DE, ES, RU, VI, AR; Arabic n=1). Tasks mix instruction, resource, and output languages within one workflow.
- **Evaluation:** Grade (deterministic weighted rubric, primary), Pytest (executable state checks), and an LLM judge (Claude Opus 4.7) as a diagnostic. **The judge sees only the deliverable, never the transcript.**
- **Harnesses:** ClaudeCode, OpenClaw, Hermes, Codex; 32 model × harness pairs.
- **Results:** best Claude Opus 4.8 + ClaudeCode 0.923 Pass@1; harness choice matters (Opus spans 0.225 across harnesses). Best–worst language gap for a fixed model can exceed 30 Grade points. Mid-tier entries degrade most on RU, ES, DE.
- **Two failure modes:** *comprehension errors* (misread figures/entities, never recover) and *cross-lingual coordination errors* ("comprehension is correct but source-language content and target-language output drift apart across a multi-step trajectory even though every intermediate step looked plausible"). **This is the qualitative observation our RQ1 turns into a controlled measurement.**
- **Judge finding:** Grade–Judge r ≈ 0.23 overall, **r ≈ 0.02** when Grade ≥ 0.5; judge scores bimodal (49.4% ≥ 0.8, 33.2% exactly 0).
- **Limitations for us:** trajectory length uncontrolled; no Indic languages; no controlled recovery.
- **Borrow:** deterministic Grade-style scoring; the two failure-mode definitions.
#### [3] Lost in Execution: On the Multilingual Robustness of Tool Calling in Large Language Models (MLCL)
 
- **Authors / venue:** Z. Luo, T. P. Kutralingam, O. N. Okoani, W. Xu, H. Wei, X. Hu (USC; Arizona State). *Proceedings of the 64th Annual Meeting of the ACL (Volume 1: Long Papers)*, 2026, pp. 44059–44077. **Verified in this re-read** (was flagged as unverified on the Review-I deck).
- **What:** Diagnostic benchmark from BFCL v4 `multiple` subset (**single-turn** queries with multiple candidate functions). Execution interface English-only and fixed.
- **Design axes:** query language composition — NT (not translated), PAR (parameter values kept English, context translated), FT (fully translated); semantic perturbation — none, paraphrase, synonym. Translations by GPT-5, manually verified.
- **Languages:** Chinese, Hindi, Igbo.
- **Models:** GPT-5 / mini / nano, DeepSeek V3.2, Llama 3.1 8B/70B, Qwen3 8B/14B/30B-A3B/32B/Next-80B-A3B, Granite 4 tiny/small.
- **Error taxonomy (by severity):** syntax error → function-level error → language mismatch (wrong value / related but incorrect / same meaning) → English wrong value / related / same meaning.
- **Findings:** FT sharply increases execution errors, **dominated by parameter value language mismatch** (e.g., `location="纽约市"`). Values are usually semantically correct: intent and tool selection succeeded. PAR removes most of this; for GPT-5 and Llama 3.1-70B PAR can match English. Mismatch is most frequent for Chinese, then Hindi, least for Igbo; Igbo shows more semantic errors instead.
- **Mitigations:** PT (instruct "pass all parameters in English"), PRE (pre-translate query), POST (post-translate parameters). All reduce mismatch; **none recover English performance**. PRE > POST; PT has inconsistent compliance.
- **Their limitation (quote):** "our evaluation is based on the vanilla subset of the Berkeley Function Call Leaderboard to focus on single-turn tool-calling scenarios".
- **Relevance:** the input-level explanation. Our lenient interface neutralises exactly this failure (RQ2). Their unexplained residual motivates us. Their high Chinese mismatch rate is also a reason Chinese is an informative control, not just a convenient one.
- **Borrow:** NT/PAR/FT design (PAR is close to our lenient interface idea), severity taxonomy, PT/PRE baselines, model list (noting Llama 3.1 70B and Qwen3-Next-80B-A3B from their model list are dropped from our own shortlist — Section 8.7).
#### [4] An Actionable Diagnosis of Multilingual, Multi-Agent Planning Failures (TART)
 
- **Authors / venue:** V. Pahuja, J. Brokman, O. Hofman, T. Nizri, D. Vishna, S. Goldfarb-Tarrant, K. Marchisio, H. Kojima, R. Vainshtein (Fujitsu Research of Europe, Cohere, Fujitsu). arXiv 2608.03735v1 (4 Aug 2026). **Verified.** Same group as MAPS.
- **What:** Studies the planner of a multi-agent system as the request-to-action interface. Taxonomy from 80 failed cases (English succeeds, non-English fails) across six low-resource languages (Igbo, Yoruba, Bengali, Swahili, Kyrgyz, Nyanja), using Qwen2.5-32B and Aya-Expanse-32B in Open Deep Research, until saturation.
- **Five planning-grounding failures:** (1) entity, (2) source, (3) temporal, (4) operation (unsound reasoning / changed objective), (5) answer-format.
- **TART:** an LLM converts the query into a structured representation with fields matching the taxonomy. **It is injected into the planner, coordinator, and worker agents' system prompts so constraints "remain in view at each stage" and workers are "less prone to drifting from the intended objective as reasoning proceeds".**
- **Published implementation detail:** Appendix B gives the full converter system prompt ("Semantic Normalization Module"; do not translate, do not answer, do not plan, English-valued JSON only) and the strict output schema: `entities`, `time_constraint`, `source_constraint`, `attachment_type` (closed set), `operations` (closed set: retrieve, extract, filter, compute, verify, format, compare, identify), `answer_type` (closed set), plus three few-shot examples. Appendix C shows the planner prompt receiving it as a "Semantic Representation" block.
- **Setup:** GAIA-MAPS (165 tasks/language), 11 languages (en, ru, de, hi, ar + Google-translated bn, sw, ky, ig, yo, ny); MULTITAT (10 languages). OWL system (coordinator fixed o3-mini). Models GPT-5-mini, Mistral-Large-3, Qwen3-VL-235B-A22B.
- **Results:** GPT-5-mini EM 0.249 → 0.305 (+5.6); Mistral-Large-3 0.196 → 0.255 (+5.9); Qwen3-VL 0.199 → 0.235 (+3.6). MULTITAT Mistral 0.210 → 0.310 (+10.0). Hindi +9.7 (GPT-5-mini). **By GAIA level: +9.0 (L1), +5.0 (L2), 0 (L3).**
- **Quantification:** LLM-judge categorisation (validated on 122 samples by 6 annotators, macro-F1 0.906). As resource availability falls, taxonomy-covered failures rise, especially operation and entity grounding.
- **Limitations:** machine-translated languages; taxonomy only from English-success/non-English-fail cases; plan-time focus.
- **Relevance:** the plan-level explanation; our oracle-plan control neutralises it. **TART also overlaps our mitigation idea (see Section 15.1).** The zero gain on Level 3 (hardest, longest tasks) is a useful hook: a static contract may not fix execution-time drift. Note Qwen3-VL-235B-A22B is one of the "too large for a single 80GB A100" models we've dropped from our own shortlist (Section 8.7); we can still cite TART's result on it without needing to reproduce it ourselves.
- **Borrow:** taxonomy categories for mapping; TART as a required baseline, implemented from the published prompt.
#### [5] MASSIVE-Agents: A Benchmark for Multilingual Function-Calling in 52 Languages
 
- **Authors / venue:** M. Kulkarni, V. Mazzia, J. Gaspers, C. Hench, J. FitzGerald (Amazon AGI). *Findings of ACL: EMNLP 2025*, pp. 20193–20215. **Verified.**
- **What:** MASSIVE (intent/slot NLU) reformatted into BFCL function calls: 47,020 samples, ~904 per language, 55 functions, 286 arguments, 52 languages; 21 models via Amazon Bedrock.
- **Results:** Nova Premier best, 34.05% average AST accuracy; 57.37% en-US vs 6.81% am-ET (zero-shot BFCL prompt). A custom one-shot prompt raises scores a lot (Claude 3 Opus 13.03% → 35.90%; Nova Micro 5.53% → 25.38%). Small models fail on syntax; medium/large on wrong function and missing/invalid parameters. Includes a prompt-translation ablation.
- **Limitations:** one function call per sample; no multi-step execution or state.
- **Relevance:** scale evidence for the multilingual function-calling gap; prompt format is a strong confound.
#### [5a] OmnilingualGAIA2: Evaluating the Multilingual Gap in Frontier AI Agents
 
*(Added 28 Sep 2026 novelty re-check — Section 15.7)*
 
- **Authors / venue:** A. Caciolai, P.-L. Huguet Cabot, C. Cheng, A. Ventayol-Boada, G. Mejia Gonzalez, C. Ropers, L. Bandarkar, S. Ruder, D. Sakakihara, E. Yun, P. Andrews, G. Mialon, R. Froger, M. R. Costa-jussà (Meta Superintelligence Labs). arXiv 2608.08775, v2 11 Aug 2026. **Verified.**
- **What:** Machine-translated (GEMMA-4-31B-INSTRUCT) expansion of GAIA2 into 10 target languages spanning 5 writing systems, with a localised, human-calibrated LLM-as-judge verifier. Covers four GAIA2 capabilities: Execution, Search, Adaptability, Ambiguity. Evaluates 7 frontier/open-weight agents (Claude 4.7 Opus, GPT-5.4, Gemini 3.1 Pro, Kimi 2.6, Gemma 4 31B, Qwen 3.6 27B/35B-A3B).
- **Languages:** Spanish, German, Portuguese, Italian, Japanese, Mandarin, French, Indonesian, Turkish, **Hindi**. No Tamil, no code-mixing.
- **Results:** universal cross-lingual gap of 8.8–18.4 pass@3 points, agent-asymmetric; gap concentrates on **tool-orchestration and final-response quality**, not quantitative/categorical reasoning; capability ordering (search > execution > adaptability > ambiguity) stable across languages; gap does **not close with model scale** — a same-family Qwen scale ladder shows the English-minus-target gap *widening* from +8.1 to +12.7 pp as active parameters grow.
- **Error attribution:** a 5-category verdict taxonomy (Infrastructure, Translation defect, Verifier artefact, Agent failure, Inconclusive) with automatic triage corrected for selection bias: 55.4% of the gap is genuine agent failure, 34.5% translation defect, 10.1% verifier artefact; only 6.4% of all scenario–language pairs are rendered unsolvable by translation. Human re-adjudication confirms 91.4% of automatic labels.
- **Behavioural signature:** off English, agents shift toward exploratory reads and away from state-changing writes (write-action share of tool calls falls 1.3–2.5 pp across three agents), described by the authors as "the behavioural counterpart" of execution-side failures.
- **Explicitly positions itself as extending MLCL "from isolated tool calls to full agent trajectories."**
- **Limitations for us:** does **not** vary horizon/step-count as a controlled independent variable — GAIA2 scenario lengths are fixed per scenario, not manipulated while holding the request constant; no injected-failure/recovery study; no Tamil; no code-mixed condition; error taxonomy is grading-provenance-oriented (translation vs verifier vs model fault), not stage-of-execution-oriented like ours (Section 9).
- **Relevance:** the closest sibling to MAPS/TART found to date, and the strongest existing evidence that the gap survives into full multi-tool trajectories — this narrows (but does not close) the "input/plan-only" framing of Section 6 point 1, updated above. Its exploratory-reads-vs-writes finding is independent motivating evidence for the state-drift hypothesis (Section 6 point 6), though not a horizon-controlled test of it. **Also our main justification for an open-models study** (Section 8.7): it shows Gemma 4 31B and Qwen 3.6 work as multilingual agents, and that the gap grows with scale.
- **Borrow:** none directly for methodology; note the stratified translation/verifier/model error-attribution approach as a template if a reviewer later challenges whether our own non-English text quality could be confounding results (our design sidesteps this by authoring, not translating, and by using deterministic gold trajectories rather than an LLM judge).
#### [5b] BabelArena: A Large-Scale Multilingual Benchmark for LLM Agents
 
*(Added 28 Sep 2026 novelty re-check — Section 15.7)*
 
- **Authors / venue:** P. Kuang, Y. Fan, J. Li, M. Wu, J. Tang, H.-R. Wei, W. Wang, J. Tu, B. Yang, T. Xiao (Alibaba). arXiv 2609.23490, submitted 20 Sep 2026. **Verified.**
- **What:** BabelFlow, a benchmark-general translation workflow (runtime-dependency analysis + structure-preserving translation + multi-layer verification + human review), used to build BabelArena: 16,146 instances from 702 canonical tasks across **four benchmark families (including VitaBench and DeepPlanning), 13 domains, and 23 languages**.
- **Languages:** 23 total, including **Tamil** and Thai among the low-resource group (full list not confirmed beyond these — check the paper directly before citing others).
- **Results:** five frontier models evaluated; no single model dominates across benchmark families; all five show lower task success and language consistency in the low-resource group than the high-resource group. Among sampled VitaBench failures, **Tamil and Thai show larger shares of tool-use and control-flow errors than English and Chinese** — cross-language disparities extend beyond answer quality to execution reliability. Low-resource trajectories consume ~2.06× the input tokens of English counterparts **with similar numbers of turns**; DeepPlanning shopping tasks incur more turns and tool calls off-English. Language consistency degrades further on structured-output tasks, with switches directed overwhelmingly toward English.
- **Limitations for us:** "similar numbers of turns" means horizon is **observed, not controlled** — no language × horizon interaction is tested, so accumulation is not addressed. No code-mixed condition. No failure-injection/recovery study.
- **Relevance:** **directly affects Section 16.5.** The panel-prep claim "Tamil... appears in none of the agent benchmarks" is no longer accurate as of 20 Sep 2026 and has been reworded there. The differentiators that survive are horizon-control, code-mixing, and recovery — not raw language coverage.
### 13.2 Agent foundations and benchmarks
 
#### [6] ReAct: Synergizing Reasoning and Acting in Language Models
 
- Yao et al. *ICLR 2023*. **Verified.**
- Interleaves thought, action, observation. Evaluated on HotpotQA and FEVER (with a Wikipedia API), ALFWorld and WebShop. Beats imitation and RL methods by **34% (ALFWorld) and 10% (WebShop) absolute success** with one or two in-context examples; reduces hallucination and error propagation versus chain-of-thought alone.
- Relevance: our agent loop and the unpinned baseline. English only.
#### [7] GAIA: A Benchmark for General AI Assistants
 
- Mialon et al. *ICLR 2024*. **Verified.**
- 466 real-world questions with unambiguous answers, 3 difficulty levels, requiring web browsing, tool use, and multimodal handling. Humans 92% vs GPT-4 with plugins 15%.
- Relevance: base of MAPS and TART's GAIA-MAPS, and of GAIA2 which underlies OmnilingualGAIA2 (Section 13.1); its levels loosely track horizon, which TART's Level-3 result uses.
#### [8] WebArena: A Realistic Web Environment for Building Autonomous Agents
 
- Zhou et al. *ICLR 2024*. **Verified.**
- Self-hosted, reproducible websites (e-commerce, forum, collaborative development, CMS) with 812 long-horizon tasks and functional-correctness checks. Best GPT-4 agent 14.41% vs human 78.24%.
- Relevance: precedent for a controlled, reproducible environment with programmatic evaluation. English only.
#### [9] DeepPlanning: Benchmarking Long-Horizon Agentic Planning with Verifiable Constraints
 
- Y. Zhang, S. Jiang, R. Li, J. Tu, et al. (Qwen Team, Alibaba). *Proceedings of the 64th Annual Meeting of the ACL (Volume 1: Long Papers)*, 2026, pp. 7377–7407. **Verified in this re-read.**
- **Travel Planning:** 120 tasks, **each in Chinese and English**, isolated sandbox with 7 sub-databases and 9 APIs; minute-level multi-day itineraries with itemised costs. **Shopping Planning:** 120 English tasks, 3 sub-databases, 15 APIs. Up to 400 tool calls per task.
- **Results:** best model fully correct in only 35.0% of Travel cases; Gemini-3-Flash-Preview 60.0% case accuracy on Shopping; more tool calls correlate with higher scores (GPT-5.2-high ~224 calls per task). **Performance drops as itinerary length grows from 2 to 7 days.** Travel results are **averaged over ZH and EN**.
- **Error taxonomy** (140 failed Claude-4.5-Opus trajectories): A Information acquisition (A1 insufficient search, A2 tool misuse, **A3 fact displacement**: retrieved ¥100 later written as ¥150); B Local reasoning (B1 explicit constraint, B2 implicit constraint); C Global optimisation (most common: 101 travel, 52 shopping).
- **Relevance:** strongest design precedent (sandbox, verifiable constraints, complexity levels) and the external validation set enabled by choosing Chinese. **Also a collision risk** (Section 15.2). Now also one of the four benchmark families absorbed into BabelArena (Section 13.1, [5b]) — its shopping-domain multilingual turn counts are reported there.
#### [10] In-the-Flow Agentic System Optimization for Effective Planning and Tool Use (AgentFlow)
 
- Z. Li, H. Zhang, S. Han, S. Liu, J. Xie, Y. Zhang, Y. Choi, J. Zou, P. Lu (Stanford et al.). *ICLR 2026*. **Verified.**
- Four modules (planner, executor, verifier, generator) coordinated through an evolving memory; planner trained on-policy inside the multi-turn loop with **Flow-GRPO**, which broadcasts one trajectory-level outcome to every turn. With a 7B backbone: +14.9% search, +14.0% agentic, +14.5% math, +4.1% science averaged across ten benchmarks; beats GPT-4o on some.
- Relevance: evolving memory is related to our state ledger; a possible training direction. Monolingual.
### 13.3 Self-correction and error recovery
 
#### [11] QueryAgent: A Reliable and Efficient Reasoning Framework with Environmental Feedback-based Self-Correction
 
- X. Huang, S. Cheng, S. Huang, J. Shen, Y. Xu, C. Zhang, Y. Qu (Nanjing University; Microsoft). *Proceedings of the 62nd Annual Meeting of the ACL (Volume 1: Long Papers)*, 2024, pp. 5014–5035. **Verified in this re-read.**
- Step-by-step KBQA with **ERASER**: the environment "speaks out" (knowledge-base empty results, Python interpreter error messages, reasoning memory); error types are distinguished and a targeted guideline is injected only when an error is detected.
- Results: with one example, beats few-shot methods on GrailQA (+5.7 F1), GraphQ (+15.0), WebQSP (+3.4), MetaQA (+2.0); ERASER improves AgentBench by up to 10.5 points.
- Relevance: environmental-feedback recovery design. Monolingual; feedback assumed to be in the agent's language.
#### [12] Metacognitive Self-Correction for Multi-Agent System via Prototype-Guided Next-Execution Reconstruction (MASC)
 
- X. Shen, Q. Zhang, S. Wang, Z. Tan, X. Zhao, L. Yao, et al., T. Chen (Michigan State, Temple, UCF, ASU, UNC, Honda Research Institute USA). **Venue [UNVERIFIED]:** page numbers (e.g., 23322) suggest an ACL Anthology volume, but no venue line is printed in the PDF.
- Unsupervised step-level anomaly detection via next-execution reconstruction plus a prototype prior; triggers a correction agent before errors propagate. Up to 8.47% AUC-ROC improvement on Who&When (without ground truth); evaluated also on AgentErrorBench.
- Useful observations: many errors appear within the first 20% of steps in the algorithm-generated subset of Who&When; controlled fault injection drops accuracy by up to 51.9 points on AQuA (random topology).
- Relevance: fault injection methodology; first-error position analysis. Monolingual.
#### [12a] Beyond Function Calling: Benchmarking Tool-Using Agents under Tool-Environment Unreliability (ToolBench-X)
 
*(Added 28 Sep 2026 novelty re-check — Section 15.7)*
 
- **Authors / venue:** Y. Tian et al. arXiv 2606.25819, v2 27 Jun 2026. **Verified.**
- **What:** ToolBench-X, a benchmark of executable multi-step tasks (sequential, parallel, mixed workflows) across diverse domains, each paired with deterministic tools and a canonical final answer for automatic evaluation. Starting from clean tool environments, injects **five structured hazard types**: Specification Drift, Invocation Error, Execution Failure, Output Drift, Cross-source Conflict. Every injected instance remains solvable through **at least one valid recovery path** (retry, fallback, verification, cross-checking).
- **Limitations for us:** English-only — no cross-lingual dimension at all.
- **Relevance:** the closest existing methodological precedent for our Section 8.6 failure-injection design (structured hazard taxonomy + guaranteed recovery path + deterministic grading). Cite explicitly and frame RQ4 as extending controlled fault-injection-with-recovery to the cross-lingual axis, so the injection methodology does not read as independently reinvented.
### 13.4 Cross-lingual reasoning and Indic evaluation
 
#### [13] Cross-lingual Prompting: Improving Zero-shot Chain-of-Thought Reasoning across Languages (CLP)
 
- L. Qin, Q. Chen, F. Wei, S. Huang, W. Che. *Proceedings of EMNLP 2023*, pp. 2695–2709. **Verified.**
- Two stages: cross-lingual alignment prompting (understand the request, reason in English), then task-specific solver prompting; CLSP ensembles reasoning paths across languages. Improves MGSM and related benchmarks.
- Relevance: evidence that pinning reasoning to English helps single-turn reasoning; motivates language pinning. No tools, no state.
#### [14] IndicMMLU-Pro: Benchmarking Indic Large Language Models on Multi-Task Language Understanding
 
- S. Jajee, A. Kumar, N. Kotecha, V. Jain, A. Chadha, S. Bhaduri. *Proceedings of the Fifth Workshop on Generation, Evaluation and Metrics (GEM)*, pp. 102–111. **Venue verified in this re-read** (year: check the GEM edition, likely 2025).
- MMLU-Pro extended to nine Indic languages (Hindi, Bengali, Gujarati, Marathi, Kannada, Punjabi, Tamil, Telugu, Urdu); validated by 13 experts. GPT-4o best at 38.46–44.80%; GPT-4o-mini 25.75–35.08%.
- Relevance: evidence of Indic gaps; static multiple-choice only.
### 13.5 The LLM-judge cluster (from the dropped first topic)
 
Still useful as background, and for justifying deterministic grading instead of LLM judges.
 
#### [15] Multilingual Prompt Localization for Agent-as-a-Judge
 
- A. Mahmood, S. Abdaljalil, H. Kurban (HBKU; Texas A&M). arXiv 2604.04532v2 (2 Jul 2026). **Verified.**
- Localises the Agent-as-a-Judge prompt stack to English, Arabic, Turkish, Chinese, Hindi; 55 DevAI tasks (365 requirements) × 3 developer-agent frameworks (MetaGPT, GPT-Pilot, OpenHands) × 6 judge backbones = 4,950 judge runs.
- Backbone rankings invert: GPT-4o best in English (44.7%), Gemini best in Arabic (51.7%) and Hindi (53.2%). Inter-backbone Fleiss' κ: EN 0.222, AR 0.184, TR 0.231, ZH 0.184, HI 0.169 (mean 0.198). Ablation: Hindi satisfaction 42.8% (full localisation) vs 23.2% (English judge instructions); Arabic unaffected. **Weak backbones show near-zero cross-language variation (capability gate).** Token-length confound tested, not significant.
- No human validation ("in progress"). Trajectories are English; only the judge prompt changes.
#### [16] How Reliable is Multilingual LLM-as-a-Judge?
 
- X. Fu, W. Liu (Heidelberg University; HITS). *Findings of ACL: EMNLP 2025*, pp. 11040–11053. **Verified.**
- 5 models, 5 tasks, 25 languages on parallel data; average Fleiss' κ ≈ 0.3 across languages; worse for low-resource languages; neither multilingual training nor scale reliably helps; proposes an ensemble strategy.
#### [17] Cross-Lingual Stability of LLM Judges Under Controlled Generation: Evidence from Finno-Ugric Languages
 
- I. Chung, L. Freienthal (Zendesk). *Proceedings of the First Workshop on Multilingual Multicultural Evaluation*, 2026, pp. 133–148. **Verified.**
- Synthetic customer-support dialogues with identical generation parameters in Estonian, Finnish, Hungarian. Surface metrics stay stable; pragmatic judgments (coherence, instruction-following) show rank inversions and near-zero correlations.
- **Borrow:** the two-stage control logic: verify content equivalence first, then attribute differences to the process under test. We apply this to task equivalence before measuring agents.
#### [18] Challenges and Recommendations for LLMs-as-a-Judge in Multilingual Settings and Low-Resource Languages
 
- A. S. Doğruöz, X. Liao, V. Blaschke, J. Prange, S. Li, D. I. Adelani. arXiv 2607.02235v1 (2 Jul 2026). **Verified.**
- Survey: of 650 ACL Anthology papers mentioning LLM-as-a-judge, only 33 focus on multilingual/low-resource settings; overtrust, single-judge reliance, English-only validation. No agentic tasks in the taxonomy. Recommends human validation and non-LLM metrics where possible.
- Use: justification for deterministic grading.
#### [19] BabelJudge: Measuring LLM-as-a-Judge Reliability Across Languages and Agent Trajectories
 
- S. KC (solo author). arXiv 2606.22329v1 (21 Jun 2026). **Verified.**
- Gold-labelling by degradation (perturb a reference response; the reference is correct by construction). One judge (Qwen2.5-7B-Instruct 4-bit), 10 references per language, 800 calls. Reliability: en 0.700, hi 0.714, ar 0.695, sw 0.550. Nine agentic trajectory perturbations defined (wrong arguments, swapped tools, hallucinated calls, missing steps, early termination, step padding) **but no agentic experiments reported**.
- Borrow: its trajectory perturbation list informs our failure-injection types.
#### [20] CalibJudge: Calibrated LLM-as-a-Judge for Multilingual RAG with Uncertainty-Aware Scoring
 
- C. Wen, A. Zhu, R. Long, H. Huang, J. Jiang, C. S. Lee. *CAIC 2026*, Sanya, China. DOI 10.1145/3807246.3807349. **Verified.**
- Language-specific temperature scaling, uncertainty scoring, and abstention on MEMERAG (en, de, es, fr, hi): up to 21.3% relative Kendall's τ gain; cross-lingual fairness gap reduced 42%; 88% balanced accuracy at 70% coverage; Hindi accounts for 42% of abstentions.
#### [21] Agentic Rubrics as Contextual Verifiers for SWE Agents
 
- M. Raghavendra, A. Gunjal, B. Liu, Y. He (Scale AI). *Proceedings of the 64th Annual Meeting of the ACL (Volume 1: Long Papers)*, 2026, pp. 15265–15290. **Verified.**
- A rubric agent explores the repository and writes a context-grounded checklist on four axes (File Change, Spec Alignment, Integrity, Runtime); an LLM grades candidate patches without execution. SWE-Bench Verified parallel test-time scaling: 54.2% (Qwen3-Coder-30B-A3B), 40.6% (Qwen3-32B), ≥ +3.5 points over the best baseline.
- English only. Useful precedent for structured verification axes.
#### [22] Verifying the Subjective: Structured Multilingual Rewards for Low-Resource Alignment
 
- J. Sha, M. Zhu (Minzu University of China; North China University of Technology). *Findings of ACL: ACL 2026*, pp. 23442–23474. **Verified.**
- Structured checklist schema + Structured Generative Critique Modelling + Adaptive Multilingual Reward Optimisation inside a bootstrapped GRPO pipeline; 7 subjective task categories across 50 low-resource languages.
- Relevance: precedent for checklist-based verification and for GRPO training in low-resource multilingual settings (a possible training direction later).
---
 
## 14. Comparison matrix: what each prior work varies
 
| Work | Multi-step execution | Horizon controlled | Indic | Code-mixed | Controls for input + plan errors | Recovery studied | Grading |
|---|---|---|---|---|---|---|---|
| MAPS | Yes | No | Hindi | No | No | No | Benchmark-native |
| PolyWorkBench | Yes | No | No | No | No | No | Deterministic + judge |
| MLCL (Lost in Execution) | **No (single-turn)** | — | Hindi | No | Input only (PAR) | No | Exact match |
| TART (Actionable Diagnosis) | Yes | No (GAIA levels only) | Hindi, Bengali | No | Plan only | No | Exact match + judge |
| MASSIVE-Agents | **No (one call)** | — | Yes (several) | No | No | No | AST match |
| DeepPlanning | Yes | Partly (2–7 days) | No | No | No | No | Verifiable constraints |
| QueryAgent / MASC | Yes | No | No | No | No | **Yes, monolingual** | Task metrics |
| ToolBench-X | Yes | No | No | No | No | **Yes, monolingual** | Deterministic |
| OmnilingualGAIA2 | Yes | No | Hindi | No | No | No | LLMaaJ (localised) |
| BabelArena | Yes | No (observed, not manipulated) | Tamil (+ others) | No | No | No | Benchmark-native |
| **This project** | **Yes** | **Yes (2/4/6/8+)** | **Hindi, Tamil** | **Hinglish** | **Both (lenient + oracle)** | **Yes, cross-lingual** | **Deterministic gold** |
 
---
 
## 15. Issues found in the final re-read (must address before building)
 
### 15.1 TART already uses a persistent structured representation
 
TART's structured representation is not used once and discarded. It is injected into the planner and every downstream agent so constraints "remain in view at each stage". That is close to our planned M1 ("language-neutral JSON of constraints and entities, re-injected every step").
 
**What to do:**
- Redefine M1 as a **dynamic state ledger**: updated after each tool call with canonical entities and values learned from tool outputs, not only constraints parsed from the request.
- Add a **TART-style static representation** as a required baseline.
- Use TART's own result as motivation: its gain is +9.0 at GAIA Level 1, +5.0 at Level 2, and **0 at Level 3** (hardest tasks). A static contract may not address execution-time drift. Our horizon design can test this directly.
- In the paper, cite TART as the plan-time mitigation and position M1 as its execution-time counterpart.
**Implementation note (28 Sep 2026):** TART's Appendix B publishes the full converter system prompt and output schema, so `agent/mitigations/tart_static.py` will use them verbatim, which pre-empts a "weak re-implementation of TART" criticism. One adaptation: TART was built for GAIA-style questions, so `attachment_type` is always `none` in our tasks; it is kept for fidelity. Our budget and time constraints land in `time_constraint` and `entities`. TART has no field for values learned from tool outputs (a resolved flight id, a hold token, a retrieved price). That missing field is exactly M1's contribution, and the comparison should be reported per horizon.
 
### 15.2 DeepPlanning has parallel Chinese/English tasks with complexity levels
 
DeepPlanning's Travel Planning has 120 tasks in both ZH and EN, and complexity from 2 to 7 days, but reports results averaged across the two languages.
 
**What it means:**
- **Opportunity:** a ready-made external validation set for RQ1 (ZH vs EN × day count), which answers the toy-environment critique cheaply. This is why Chinese was chosen as the control (Section 8.3).
- **Risk:** the authors or anyone else could publish the language × complexity breakdown. It would not cover our controls (RQ2), recovery (RQ4), or Indic and code-mixed languages, but it would weaken the "no one has controlled horizon" sentence. Re-word that gap to "no one has isolated a language × horizon interaction with input and plan failures controlled".
- **Borrow:** "fact displacement" (A3) as a taxonomy category.
### 15.3 The Review-I deck has four references to update
 
| Deck ref | Current | Verified |
|---|---|---|
| [3] Lost in Execution | "2026" | *Proc. 64th ACL (Vol. 1: Long Papers)*, 2026, pp. 44059–44077 |
| [9] DeepPlanning | "Qwen Team, Alibaba Group, 2026" | *Proc. 64th ACL (Vol. 1: Long Papers)*, 2026, pp. 7377–7407 |
| [11] QueryAgent | "2024" | *Proc. 62nd ACL (Vol. 1: Long Papers)*, 2024, pp. 5014–5035 |
| [12] MASC | "2026" | Still unverified; find the Anthology entry |
| [14] IndicMMLU-Pro | "2025" | *Proc. Fifth Workshop on Generation, Evaluation and Metrics (GEM)*, pp. 102–111 |
 
### 15.4 The final deck has no architecture slide
 
The submitted Review-I PDF has 9 slides (no Proposed Architecture slide). Review-II will likely ask for methodology. Bring the diagram back, updated with the two control conditions (lenient interface, oracle plan) and the TART-style baseline.
 
### 15.5 The Objectives slide lacks the causal-isolation step
 
The RQ2 controls were designed after Review-I. Add an objective for them in Review-II. They are the defence against "this is just MLCL's failure repeated".
 
### 15.6 Novelty check is two months old
 
The last kill-check was in August. Re-run Section 18 before Phase 2. **Update: re-run on 28 Sep 2026 — see Section 15.7.**
 
### 15.7 Novelty re-check run 28 Sep 2026 (per Section 18 protocol)
 
Three papers not in the original 22-paper review surfaced under the Section 18 kill queries:
 
- **OmnilingualGAIA2** (Meta Superintelligence Labs, arXiv 2608.08775, Aug 2026) — full-trajectory multilingual agent evaluation extending MLCL beyond isolated tool calls; includes Hindi. Full notes: Section 13.1 [5a].
- **BabelArena** (Alibaba, arXiv 2609.23490, submitted 20 Sep 2026 — eight days before this check) — 23-language agentic benchmark across four benchmark families including VitaBench and DeepPlanning; includes **Tamil**. Full notes: Section 13.1 [5b].
- **ToolBench-X** (arXiv 2606.25819, Jun 2026) — English-only controlled fault injection with guaranteed recovery paths; the closest methodological precedent to our Section 8.6 design. Full notes: Section 13.3 [12a].
**Verdict:** the core novelty survives. None of the three controls horizon/step-count as an independent variable while holding the request fixed (Kill A negative); none proposes a language-pinned or execution-updated dynamic state representation beyond TART (Kill B negative); none combines Indic and code-mixed conditions or produces authored code-mixing at all (Kill C negative); none studies cross-lingual error recovery from injected failures (Kill D negative); Indic coverage has grown (Hindi in OmnilingualGAIA2, Tamil in BabelArena) but neither isolates a language × horizon interaction for any Indic language (Kill E — partial, addressed below).
 
**Required updates made as a result (this pass):**
1. Added all three papers to Section 13 (as [5a], [5b], [12a]) and to the Section 14 comparison matrix.
2. Reworded the Section 16.5 panel answer on "why Tamil and Hinglish" — it previously claimed Tamil appears in no agent benchmark, which BabelArena (20 Sep 2026) makes inaccurate as literally stated. The answer now leads with horizon-control, code-mixing, and recovery as the surviving differentiators.
3. Added OmnilingualGAIA2's exploratory-reads-vs-writes finding to Section 6 as independent motivating evidence for the state-drift hypothesis (point 6).
4. Added a risk to Section 12: well-resourced labs (Meta, Alibaba) are now visibly active in exactly this space and publishing faster than a solo student can track; monthly re-checks are non-optional.
**Next re-check due:** before Phase 2 (environment build), and again before submitting the paper — per the existing Section 12 risk register, not a new schedule.
 
### 15.8 Compute environment settled 28 Sep 2026
 
Earlier drafts of this document assumed "API + strong GPU access via lab" (Section 3.6). That lab access does not exist for this project. The actual compute is **Google Colab Pro**: A100 GPU, 80GB VRAM, ~150GB system RAM. This has three consequences, all applied throughout this document:
 
1. **Model shortlist trimmed** (Section 8.7): Llama 3.1 70B, Qwen3-Next-80B-A3B, Qwen3-VL-235B-A22B, and DeepSeek V3.2 are dropped. Everything up to ~32B fits comfortably; larger open-weight models are cited from the literature (e.g. TART's Qwen3-VL result) rather than reproduced.
2. **Run budget descoped, temporarily** (Section 8.11, Section 11 Phase 5): the full ~9,600-run core grid plus 2–3× for controls/seams/recovery/mitigation is not attempted up front. Phase 5 starts with a reduced pilot-scale grid, sized after the Phase 4 pilot. The full grid is a stretch goal, not a blocker for RQ1/RQ2/RQ4.
3. **Open-source models primary, APIs optional** (Section 8.7), served with vLLM through one OpenAI-compatible policy.
Development workflow decided at the same time: GitHub is the source of truth for code; local (or this session) is used for anything not GPU-bound (environment, verifier, stats); Colab Pro is used for GPU-bound steps (serving open-weight models, the optional SFT ablation). See Appendix D for the repository layout and the Colab/GitHub/Drive workflow, and `notebooks/colab_runner.ipynb` for the Colab-side entrypoint.
 
### 15.9 Phase 1 findings from building the travel domain (28 Sep 2026)
 
Building the first domain end to end, before freezing the spec, surfaced three issues that would otherwise have reached the experiments. All three are now enforced by tests.
 
1. **A constraint that never changes the answer makes drift on it invisible.** The original example, "cheapest morning flight under ₹8000", has a budget that never binds: when minimising price, the cheapest morning flight is already under budget whenever any in-budget option exists. An agent that forgot the budget would still book the right flight, so constraint survival (our most direct drift measure) could not see it. **New authoring rule: every constraint must change the answer.** Dropping any single constraint must change the correct outcome, and each gold file records the resulting **decoy** per constraint. travel_017 now asks for the **latest** morning flight under ₹8000: losing the budget leads to SG118 (11:45, ₹8900), losing "morning" leads to AI552 (14:20), ignoring the objective leads to AI440. Each failure lands on a distinct, traceable flight. This rule is worth stating in the paper's method section; it is a validity property most agent benchmarks do not check.
2. **Silent script corruption.** The first Tamil draft contained three Gujarati vowel signs (U+0ABE) instead of Tamil ones (U+0BBE). It renders almost identically but tokenises as mixed-script text, which would have quietly degraded the whole Tamil condition. A script-hygiene test now checks every non-Latin request.
3. **Horizon mechanism and its invariants.** Horizon is set by required values, not by the request (Section 8.2). Tests enforce that tool names and the final decision set are identical across horizons, that every gold file replays exactly, and that lenient mode never shortens the chain.
Baseline mapping settled at the same time (Section 8.10): unpinned agent from ReAct [6], PT/PRE from MLCL [3] (PRE also in MAPS [1]), static representation from TART [4] using its published prompt.
 
### 15.10 First capability gate: Qwen 3.6 27B on travel_017 (28 Sep 2026)
 
**Run:** Qwen/Qwen3.6-27B (BF16, vLLM, Colab A100 80GB), travel_017, 5 languages × horizons 2/4/6/8 × thinking on/off × 3 seeds = 120 episodes. Zero infrastructure errors. Raw log: `runs/capability_gate_qwen36_27b.jsonl` (local; also on Drive).
 
**Clean success (both thinking settings pooled, 6 episodes per cell):**
 
| Language | h2 | h4 | h6 | h8 |
|---|---|---|---|---|
| English | 6/6 | 6/6 | 6/6 | 6/6 |
| Chinese | 6/6 | 6/6 | 6/6 | 6/6 |
| Hindi | 6/6 | 6/6 | 6/6 | 6/6 |
| Tamil | 2/6 | 0/6 | 1/6 | 0/6 |
| Hinglish | 1/6 | 3/6 | 4/6 | 2/6 |
 
**What the transcripts show (one template, so these are observations, not results):**
 
1. **Zero tool-interface errors in any language.** No parameter-language mismatch, no schema errors, no malformed calls. For this model, MLCL's dominant failure does not appear.
2. **Tamil fails at comprehension, and the decoy shows exactly where.** The model's own parse of the Tamil request lists date, morning and budget but never "latest" (கடைசி). It then books AI440, the objective decoy (14 episodes), or, seeing two equally valid flights, asks the user to choose (7). The failure is present at h2 and flat across horizons: the comprehension signature, not drift. **Phrasing checked by Rishabh (28 Sep 2026): "காலை நேரத்தின் கடைசி விமானத்தை" reads naturally as "the last flight of the morning", so this is the model's comprehension, not a template artefact.**
3. **Hinglish fails on "Kal".** "Kal" means both yesterday and tomorrow; the model resolved it to *today's* date in most Hinglish episodes, found no flights, and asked for another date (14 text replies, 0 wrong bookings). The same word in Devanagari (कल) in the Hindi request was resolved correctly in 24/24 episodes. A Roman-script-specific temporal-grounding failure: small n, but worth keeping as a code-mixing observation. Also comprehension, not drift.
4. **The model reasons in English for Indic inputs.** Share of Latin letters in the thinking traces: Hindi 0.96, Tamil 0.93, Hinglish 1.00, Chinese 0.53. It already "pins" its reasoning language to English for Indic requests, so a mitigation cannot be "make it reason in English". This strengthens the M1 framing (carry *state*, not change reasoning language).
5. **Ceiling in English, Chinese and Hindi, and a structural reason for it.** 100% at every horizon, so no gap can widen. Looking at where the decision is made: even at h8 the flight is chosen at step 4–6, right after filtering. Every constraint is consumed early; the steps that horizon adds come *after* the decision and only carry ids and tokens. **Horizon currently lengthens the chain but not the distance between when a constraint is stated and when it is needed.** That distance is what drift acts on.
6. At short horizons the model takes optional extra lookups (h2 runs took 2–7 steps), which compresses the effective horizon range. Analyses should report both required and actual steps.
**Decisions and consequences:**
- **Thinking mode: ON**, fixed for the study (Section 8.7).
- **Qwen 3.6 27B passes the gate in English, Chinese and Hindi; fails in Tamil and Hinglish on this template.** One template cannot decide a model; re-gate on the redesigned templates.
- **Proposed redesign (Section 15.11): late-binding constraints**, so that horizon increases *constraint distance*, not just chain length. Must be settled before authoring the remaining templates.
### 15.11 Proposed: late-binding constraints (constraint distance grows with horizon)
 
The gate showed that in the current design every constraint is used by step ~5 even at h8. To measure drift, some constraints must be *stated in the request but first needed late in the chain*, with the number of intervening steps growing with horizon.
 
Principle: split the task into stages, and bind each constraint to a stage. Example extension of travel_017: "Book the latest morning flight from Chennai to Delhi tomorrow under ₹8000, **window seat, vegetarian meal**." Flight choice uses time/budget/objective early; seat selection and meal selection come at the end of the chain. At h2 the seat and meal are set in the booking call; at h8 they are chosen after several intermediate steps. Each late constraint gets a decoy (the default aisle seat, the default non-veg meal), so its survival is read from the terminal state. The new primary drift measure becomes **constraint survival as a function of distance (steps between request and first use), per language**, which is sharper than end-task success and directly tests accumulation.
 
**Status: agreed and built 28 Sep 2026.**
- Late constraints: seat type and meal, committed only in the final booking call. Horizons extended to 2–12 (h10 adds seat map and meal options, so booking takes ids; h12 adds travel documents and payment method).
- Three templates: **travel_017** (latest morning flight under ₹8000; aisle seat, Jain meal), **travel_018** (cheapest flight after 17:00; window seat, vegetarian meal), **travel_019** (earliest flight under ₹6000; aisle seat, diabetic meal). Each early constraint has a distinct decoy flight.
- **New authoring rule found while building:** a requested late option must never be the first one listed. travel_018's window seat was listed first, so an agent that forgot the preference and took the first seat would have looked correct. Seat listing order is now route-dependent, and the gold builder refuses any template that breaks the rule.
- Gold for all 18 template × horizon pairs is generated by `tasks/build_gold.py`, which derives the answer and decoys from the constraints alone, replays each chain, and enforces every rule. The verifier reports early and late survival separately, with the step at which each was used. 106 tests.
- Gate v2 config ready: 3 templates × h2–12 × 5 languages × 3 seeds, thinking on (270 episodes, run concurrently).
### 15.12 Gate v2 results: Qwen3.6-27B-FP8, late-binding templates (28 Sep 2026)
 
Run: 270 episodes (3 templates × h2–12 × 5 languages × 3 seeds), thinking on, strict interface, 0 infrastructure errors. Every episode is stamped with the same backbone: `Qwen/Qwen3.6-27B-FP8` @ `e89b16eb`, vLLM 0.30.0, A100-80GB. Summary in `results/capability_gate_v2_qwen36_27b_fp8.json`. (First launch failed at kernel warm-up because `ninja` was not on PATH inside the vLLM venv; fixed in the notebook, backbone unchanged.)
 
**Full success by language × horizon (9 episodes per cell)**
 
| lang | h2 | h4 | h6 | h8 | h10 | h12 |
|---|---|---|---|---|---|---|
| en | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| zh | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| hi | 1.00 | 1.00 | 1.00 | 1.00 | **0.78** | **0.33** |
| ta | 0.67 | 0.67 | 0.78 | 0.67 | 0.67 | 0.67 |
| hinglish | 0.89 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
 
**Finding 1: first candidate drift signal (Hindi, late seat constraint, h10–12).** Early constraints (flight choice) are at 1.00 for hi at every horizon. The late seat constraint is at 1.00 for hi up to h8, then falls to 0.78 (h10) and 0.33 (h12). All 8 failures have the same shape: on the aisle templates (017, 019) the model reads the seat map and, in its reasoning, picks an aisle seat (14C). Three to five steps later, in the final `book_flight`, it writes **seat_id 14A (window) and still labels it "aisle seat as requested"** in its reasoning. The constraint word survives, but the value it was bound to is lost. The rate is 8/12 for hi on aisle templates at h10–12, against 0/48 for en, zh, ta and hinglish in the same cells. Meal survival is 1.00 everywhere. 14A is the first seat in that route's seat map, so this looks like the drifted value falling back to the first listed option, which the "never first" authoring rule was designed to catch.
 
**Confound (must fix before claiming drift):** h10 is also where booking switches from the `seat_type` enum to a `seat_id` picked from the seat map. So the Hindi drop could come from (a) more steps between choosing and committing, or (b) having to carry an opaque id rather than a word. Other languages do fine with ids at h10–12, so ids alone do not explain it, but Hindi × id and Hindi × distance cannot be separated yet. **Proposed control:** a 2×2 over interface (enum vs id) × distance (short vs long). This needs id-binding at a short horizon and enum at a long one, independent of the horizon profile.
 
**Finding 2: Tamil comprehension failure, flat across horizons.** travel_017 in Tamil books AI440 (the earliest flight) in 16/18 episodes. When the model paraphrases the request at step 0, it drops கடைசி ("last") and keeps only "morning". It is flat over h2–12 and the late constraints are intact (1.00 booked-only for h4–12), so this is a comprehension failure, not drift. It is the same failure as in gate v1 and is a separate category in the error taxonomy.
 
**Finding 3: Hinglish.** 1/90 failures: "Kal" read as today, the same as in gate v1.
 
**Cost:** mean completion tokens per episode are en 1264, zh 1328, hi 1422, hinglish 1636, ta 1848.
 
**Caveat:** one model, 9 episodes per cell, 3 templates. Finding 1 is a lead to test with the control and more templates, not a result.
 
### 15.13 Decision: a long-horizon trip domain with realistic agent load (28 Sep 2026)
 
**Why.** Gate v2 could not show whether the gap widens: English and Chinese were at 1.00 everywhere (ceiling), the longest carry was about 5 steps, only 2 values were carried, tool outputs were small, and the one drift lead (Hindi seat, 15.12) was confounded with the switch to seat ids at h10. We agreed to move the main experiment to a harder, longer task rather than tune the travel templates until a language fails, which would be p-hacking.
 
**What was built** (spec: `docs/TRIP_SPEC.md` in the repo; design fixed before any model run):
- **Task:** a family trip organiser. One request books Chennai to Jaipur and back for the user and both parents: two flights under a joint budget, a hotel with filters and two rooms, an airport cab timed to the landing, Amber Fort tickets, and per-traveller seats, meals and ticket categories. Everything is confirmed in one final checkout. Request length about 150 words and 35 scored constraints.
- **Horizon:** 22 tools with the same names at every horizon; the same request needs **11, 17, 24 or 28** calls (inline filters → codes and filter steps → fare rules and 5 holds → hotel location, documents, payment and price token). The correct trip is identical at every horizon.
- **Confound removed by design:** seat ids, meal codes, room ids, quote ids and slot ids are required at every horizon, so the checkout interface for late constraints never changes with horizon.
- **Four constraint classes**, each with the step it was committed at: **early** (flights), **mid** (hotel, rooms, cab, tickets), **carried** (cab pickup time and drop copied from tool outputs: the tool-output seam of RQ3), **late** (per-traveller seat × 2 legs, meal, ticket, room assignment, committed only at checkout: the request seam). Plus **binding swaps** (one traveller gets another's preference) and fact displacements.
- **Authoring rules** enforced by the gold builder: answer from constraints alone; every constraint selects a distinct decoy (13 in trip_001); no requested option listed first, and assigning options to travellers in listing order gets every traveller wrong; a recovery fallback; tool errors never mention preferences.
- **Realistic load:** 8–10 rows per flight search with near-identical ids (6E612 / 6E621), 10 hotels, 24-seat maps with occupied seats, about 7,000 tokens of tool traffic at h28. Context raised to 64k.
- Template trip_001 in en / zh / hi / ta / hinglish (hi, ta, hinglish pending Rishabh's check; zh pending back-translation). 162 tests; a 36-episode mock smoke test shows each fault caught only in its own class.
**Rule fixed in advance: difficulty is set on English only.** Pilot: trip_001, English, 4 horizons × 5 seeds. If English success at h11 is below 0.8, simplify and rerun the pilot before any other language runs. If it passes, the design is frozen and the gate (5 languages × 4 horizons × 3 seeds) runs unchanged. New templates are written under the same rules and never chosen by their results.
 
**Travel domain status:** kept as the short-horizon domain; its results (15.10, 15.12) stand. The planned word-vs-id × distance control (item 6e) is no longer needed for the main claim, because the trip domain holds the interface fixed across horizons.
 
### 15.14 Trip pilot 1: rule failed, two measurement fixes, rule amended (29 Sep 2026)
 
**Run:** trip_001, English only, 4 horizons × 5 seeds, Qwen3.6-27B-FP8 (commit cbe022c). As run: h11 0.40, h17 0.60, h24 0.80, h28 0.20. The pre-set rule (h11 ≥ 0.8) failed, so the gate correctly did not run. Mean 25.6 steps and ~14,400 completion tokens per episode.
 
**What the 10 failures were:**
- **5 were our scoring, not the model:** it booked the cab 15–45 min after landing "to allow for deplaning and baggage", with the correct arrival time. "Pick us up when we land" does not mean the exact minute → pickup now scored as 0–60 min after arrival.
- **2 are the phenomenon (both h11):** the pickup was set to 08:25, the arrival of **6E612**, the row next to the booked **6E621**, while the reasoning said "6E621 arrives at 08:25". A carried fact taken from the wrong row, in English, which the near-identical ids were designed to provoke.
- **1 harness glitch:** an empty model reply ended the episode → empty replies are now resampled (different seed, up to twice) and counted; finish reasons are logged.
- **1 genuine:** held both return candidates, booked the wrong one.
Re-scored with the pickup fix: 16/20 (h11 2/5, h17 5/5, h24 5/5, h28 4/5).
 
**Decision (Rishabh, 29 Sep 2026): amend the rule, do not simplify.** Simplifying would remove the carried-fact errors the study exists to measure. The rule was flawed: it assumed h11 is the easiest horizon, and 5 episodes cannot separate 0.4 from 0.8. **New rule:** a fresh English pilot with 10 seeds per horizon (40 episodes); the design is frozen and the gate runs if pooled English success ≥ 0.7. The amendment was made after English-only data and before any other language ran, so it cannot favour a language result. Recorded in `docs/TRIP_SPEC.md`.
 
**Early signal worth keeping:** even in English, the one failure type that appears is a *carried* fact taken from a neighbouring row, not a forgotten request constraint. Early, mid and late (per-traveller) constraints were 100% in booked English episodes, with zero binding swaps.
 
### 15.15 Trip pilot 2 and trip gate v1 results (29 Sep 2026)
 
**Pilot 2** (English, 40 episodes, commit f0faba1): h11 0.50, h17 1.00, h24 0.80, h28 0.90; pooled **0.80 ≥ 0.7 → pass**, design frozen, gate run unchanged.
 
**Gate v1** (trip_001 × h11/17/24/28 × 5 languages × 3 seeds = 60 episodes; 0 infra errors, 0 empty replies, 60/60 booked). Summary in `results/trip_gate_v1_qwen36_27b_fp8.json`.
 
| lang | h11 | h17 | h24 | h28 | overall |
|---|---|---|---|---|---|
| en | 0.00 | 1.00 | 1.00 | 1.00 | 0.75 |
| zh | 0.67 | 1.00 | 1.00 | 1.00 | 0.92 |
| hi | 1.00 | 0.67 | 0.67 | 0.33 | 0.67 |
| ta | 0.33 | 0.33 | 0.00 | 0.00 | 0.17 |
| hinglish | 0.33 | 0.33 | 0.67 | 1.00 | 0.58 |
 
Mid constraints (hotel, rooms, cab type, tickets) were 1.00 in every cell. The failures come from four distinct mechanisms, which the constraint classes separate:
 
1. **Return flight: switching objective under a coupled budget (early class; the main language gap).** The earliest non-stop after 18:00 (6E622) breaks the joint ₹30,000 budget. The correct move is the next earliest (SG306); instead the model switches to the *cheapest* (IX143), the outbound leg's objective. Counts: en 0/12 (pilot 2/40), zh 0/12, hi 2/12, hinglish 4/12, **ta 8/12**. In some Tamil runs "earliest" is already missing from the model's opening paraphrase; in Hindi it is present and lost when the budget check fails. Not horizon-dependent: a language gap in a reasoning step, not accumulation.
2. **Arrival time copied from the neighbouring flight row (carried class).** Pickup set from 6E612's arrival (08:25) while calling it 6E621's: en h11 3/3, zh h11 1/3, hinglish h11 2/3, plus single cases at h17. Concentrated at **h11**, the one level where the flight list appears once, already filtered. At h17+ it is searched and then filtered, so it appears twice. **This is a presentation effect, not a distance effect, and a confound in the horizon manipulation** (levels change how information is shown, not only how far back it is).
3. **Tamil self-ticket booked as "student" (late class) at h24/h28 only (4/6, 0/6 at h11/h17).** The reasoning shows the model unsure what பெரியவர் டிக்கெட் means when it re-reads the Tamil request late in the episode. The trigger is my wording, so the template needs fixing. The horizon pattern (re-reading the native request late) is worth testing with an unambiguous wording.
4. **One binding swap (Hindi h28):** the user was given the mother's aisle seat on both legs.
**Against RQ1:** the English–Indic gap is large (en 0.75, zh 0.92 vs hi 0.67, hinglish 0.58, ta 0.17), but on this template it mostly sits in one early reasoning step (mechanism 1), not in accumulation over horizon. Hindi's decline (1.00 → 0.33) is 3 episodes per cell, from mechanisms 1 and 4, which is not enough to claim a slope. Reasoning language: en/hinglish ~100% Latin, ta 0.96, hi 0.88, zh 0.54.
 
**Implications:** (a) fix the Tamil ticket wording; (b) fix the h11 presentation confound: every level should present flight results the same way; (c) the coupled-constraint objective switch is a strong, measurable, language-sensitive failure and should be a deliberate element of every template; (d) more templates and seeds are needed before any horizon claim.
 
### 15.16 Fixes after trip gate v1, and four more templates (29 Sep 2026)
 
Decided (Rishabh) from the gate v1 analysis, before the next run:
- **h11 presentation confound removed.** Every horizon now shows search results the same way (full list, then filtered list). The shortest level is **h14** (was h11); horizons are 14 / 17 / 24 / 28.
- **Tamil adult ticket** now "சாதாரண பெரியவர்களுக்கான (அடல்ட்) டிக்கெட்" (was read as "student").
- **trip_002–trip_005** added (origins Bengaluru, Hyderabad, Mumbai, Kolkata; destination Jaipur), all with the same traps as trip_001:
  - a **joint flight budget** that rules out the objective-best return flight (the dominant language-sensitive failure in gate v1);
  - a **nightly hotel budget** that rules out the top-rated hotel;
  - **near-identical flight ids** next to the answer (6E4512 / 6E4521 …), for carried-fact errors;
  - **per-traveller seats, meals and ticket categories** that listing order gets wrong for everyone (including student tickets for the user);
  - a **decoy for every constraint** (13–14 per template);
  - varied objectives (earliest / latest / cheapest), rooms (twin / suite / double), vehicles (sedan / SUV / tempo traveller) and attractions (City Palace, Hawa Mahal, Jantar Mantar, Nahargarh Fort).
- Gold built and every rule checked by `tasks/build_trip_gold.py`; 324 tests; 180-episode mock smoke test passes with each fault caught only in its own class.
- **Main run v1:** 5 templates × 4 horizons × 5 languages × 5 seeds = **500 episodes**, `configs/trip_main_v1.yaml`, 32 concurrent episodes; spans more than one Colab session via `--resume`.
- Rishabh to verify the new hi / ta / hinglish requests (Appendix A.3); zh by back-translation.
---
 
## 16. Review-I artefacts and panel preparation
 
### 16.1 Review-I rubric (5 marks)
 
- Title and abstract: 3 marks (clear, concise, complete, no ambiguity).
- Compliance (0.5 each): title updated in VTOP; SDG finalised; TRL 3 or above identified; project outcome identified.
### 16.2 Deck structure (as submitted)
 
Title → Aim → Abstract → Literature Review (2 slides, 14 papers in a table: Author/Year, Objective, Methodology/Dataset, Findings, Limitations) → Research Gap (5 bullets) → Objectives (5 bullets + SDG 10 / TRL 3 / Outcome caption) → References (2 slides).
 
### 16.3 Deck objectives (verbatim)
 
1. To construct a controlled multi-step tool environment with deterministic ground truth for tool sequence, arguments and terminal state, parameterised by required step count, enabling automatic failure detection without manual annotation.
2. To test the accumulation hypothesis by measuring task success as a function of horizon across English, a high-resource control language, Hindi, Tamil and code-mixed Hinglish, estimating a per-language drift slope that distinguishes compounding from fixed degradation.
3. To decompose failures by execution stage — intent parsing, tool selection, argument construction, entity handling, state carryover and termination — extending single-turn and plan-level taxonomies to multi-step execution.
4. To characterise cross-lingual error recovery by injecting tool failures at controlled points and measuring repair rate, retry quality and recovery latency per language.
5. To design and evaluate mitigation through language-pinned internal state and localised error surfaces, quantifying the trade-off between execution accuracy and response quality.
### 16.4 Form abstract (987 characters)
 
> Multi-step LLM agents degrade substantially in non-English settings. Existing work attributes this to two sources: parameter errors at the tool-call interface, and grounding losses during plan generation. Both are studied under single-turn evaluation or at the request-to-plan boundary, so neither can observe what happens across successive execution steps.
>
> We test a third source: progressive corruption of task state during execution. If degradation accumulates, the English/non-English gap should widen with step count rather than stay constant. We also examine recovery, since tool errors are emitted in English regardless of user language.
>
> We build a controlled tool environment with deterministic ground truth, requiring no manual annotation. Tasks are parameterised by step count across English, a control language, Hindi, Tamil and Hinglish, with injected failures. We then evaluate language-pinned reasoning as mitigation, measuring the accuracy/quality trade-off.
 
### 16.5 Likely panel questions and answers
 
| Question | Answer |
|---|---|
| How is this different from the Fujitsu planning paper? | They measure what is lost when the plan is written. I measure what is lost while the plan is executed, with plan errors removed by an oracle-plan control. |
| Lost in Execution already tested your mitigation. | They show English-parameter prompting and translation don't close the gap, but can't explain the residual because single-turn has no accumulated state. |
| Isn't your environment a toy? | Control is the point; it is what allows removing the two known failure sources. Schemas mirror real APIs, and we validate on DeepPlanning's parallel ZH/EN tasks. |
| How do you make the same request take 2 or 8 steps? | The request and tool names never change. Only what each tool requires changes (a city code, a hold token, a fare class), so a value only another tool can produce forces that tool into the chain. The final choice is the same at every length, so longer tasks are longer, not harder. |
| How do you know a wrong answer was drift and not something else? | Every constraint has a decoy: forgetting the budget books one specific flight, forgetting the time books another. The outcome tells us which constraint was lost. |
| Why Chinese as the control? | It is high-resource, MLCL found Chinese has the highest parameter-mismatch rate, and DeepPlanning has parallel ZH/EN tasks with complexity levels, which gives an external check on the accumulation result. |
| Why only open-source models, not GPT or Claude? | The question is whether the gap widens with horizon, which needs models above the capability gate, not frontier ones. Open models make the study reproducible and allow the SFT and hidden-state analyses. Meta's OmnilingualGAIA2 found the language gap grows with model size, so the effect is not expected to vanish at the frontier. A frontier subset can be added through the same code. |
| Why Tamil and Hinglish, not just Hindi? | Hindi already appears in several recent benchmarks, including a Meta benchmark (OmnilingualGAIA2, Aug 2026). Tamil has appeared in exactly one benchmark to date (BabelArena, Alibaba, Sep 2026), and only as an observational comparison — turn count is held roughly constant there rather than manipulated, so no work isolates a language × horizon interaction for Tamil, or for any Indic language. Code-mixed input appears in no agent benchmark we have found: every existing multilingual agent benchmark, including both of the above, is built by translation, which cannot produce code-mixing by construction. |
| Why no human evaluation? | Every correctness criterion is checkable against gold trajectories we author. Judge papers show LLM judges are unreliable across languages, so we avoid them for primary metrics. |
| What if there is no drift? | Then multilingual agent failure is front-loaded, which tells builders to fix the interface and plan. Recovery and the code-mixed benchmark stand regardless. |
| Why hasn't anyone done code-mixed? | Benchmarks are made by translation, and translation cannot produce code-mixing. It must be authored. |
| Reliability vs validity? | Reliability is consistency; validity is correctness. Our deterministic verifier measures validity directly. |
| What did you actually run this on? | Google Colab Pro (a single A100, 80GB VRAM) serving open-weight models with vLLM. No institutional compute cluster; the run grid was sized to what a solo student on one GPU can finish in the available time. |
 
---
 
## 17. Next actions
 
In order:
 
1. ~~**Novelty re-check** with Section 18 keywords~~ — **done 28 Sep 2026** (Section 15.7). Three new papers found and folded in; core novelty survives. Next re-check due before Phase 2.
2. ~~**Settle the compute environment**~~ — **done 28 Sep 2026** (Section 15.8): Colab Pro (A100 80GB / 150GB RAM), no lab GPU; model shortlist trimmed; run grid temporarily descoped to a reduced pilot-scale plan.
3. **Decide the TART response** (Section 15.1): M1 is a dynamic ledger; TART-style baseline to be built from TART's published prompt. *Decided; implementation pending (Phase 7). The baseline can be built on the real-model policy now that it exists.*
4. ~~**Decide the control language**~~ — **done 28 Sep 2026: Chinese (Simplified)**, verified by translator back-translation + answerability (Section 8.3).
5. ~~**Decide model access**~~ — **done 28 Sep 2026: open-source primary, APIs optional** (Section 8.7). One OpenAI-compatible policy built and tested (40 tests in the repo).
6. ~~**Run the capability gate on Colab**~~ — **done 28 Sep 2026** (Section 15.10). Thinking mode fixed ON. Ceiling in en/zh/hi; comprehension failures in ta/hinglish.
   - a. ~~Decide on late-binding constraints~~ — agreed and built (Section 15.11).
   - b. ~~Check the Tamil phrasing~~ — natural; the Tamil failure is the model's (Section 15.10).
   - c. ~~Run gate v2 on Colab~~ — **done 28 Sep 2026** (Section 15.12). First drift lead: Hindi late seat binding fails at h10–12 (8/12 vs 0/48 in other languages); confounded with the switch to seat ids at h10.
   - d. Rishabh: check the new seat and meal clauses in hi / ta / hinglish for all three templates (Appendix A).
   - e. ~~Interface × distance control~~ — superseded by the trip domain, which holds the late-constraint interface fixed across horizons (Section 15.13).
   - f. ~~Trip English pilot 1~~ — ran 29 Sep 2026; rule failed; scoring and harness fixed; rule amended (Section 15.14).
   - f2. ~~Trip English pilot 2 and trip gate v1~~ — done 29 Sep 2026 (Section 15.15). Large language gap, mostly in a coupled-budget objective switch (early), not accumulation; h11 presentation confound found.
   - f3. ~~Fix Tamil ticket wording and h11 confound; author trip_002–005~~ — done 29 Sep 2026 (Section 15.16).
   - f4. **Next: trip main run v1** (500 episodes, 2+ Colab sessions). Then the error-injection pilot (RQ4), then a second model.
   - g. Rishabh: check the trip_001 hi / ta / hinglish requests (Appendix A.2); run zh through back-translation.
   - h. Author trip_002–trip_005 on the Jaipur world, then a second world, under the same rules.
7. **Phase 1 spec** — *in progress*, `docs/PHASE1_SPEC.md`. Done: travel domain (7 tools, horizons 2/4/6/8, strict/lenient, injection with en/zh/hi/ta/hinglish messages, verifier). Remaining:
   - a. Build the shop domain (5 tools, specified in the spec §4); settle how delivery estimates reach the decision without per-candidate lookups.
   - b. Implement validation injection as persistent specification drift.
   - c. Author the remaining templates (target 40), each with one decoy per constraint.
   - d. Rishabh: verify hi / ta / hinglish text of travel_017; run the zh text through translator back-translation.
   - e. Collect a final user-facing reply after the booking (needed for RQ5 output-language fidelity).
8. **Model shortlist:** Qwen 3.6 27B and Gemma 4 31B first; add a smaller model for a size contrast; keep only models that pass the gate in all five languages.
9. **Fix deck references** (Section 15.3) and restore the architecture slide with the new controls for Review-II.
10. ~~**Repo scaffold**~~ — created 28 Sep 2026 matching Appendix D; on GitHub at khalerishabh/xlingual-drift.
---
 
## 18. Novelty re-check keywords
 
**Kill A — someone measured failure growth over horizon by language**
```
multilingual agent long-horizon degradation
cross-lingual error propagation multi-step agent
language gap trajectory length LLM agent
multilingual agent failure accumulation steps
DeepPlanning Chinese English complexity
```
 
**Kill B — someone proposed language-pinned or dynamic state for multilingual agents**
```
language consistency LLM agent reasoning
internal reasoning language control multilingual agent
pivot language reasoning cross-lingual agent
structured task representation multilingual agent memory
TART taxonomy-guided actionable task representation
```
 
**Kill C — a code-mixed agentic benchmark exists**
```
code-mixed tool calling benchmark
Hinglish agent benchmark tool use
transliterated input function calling LLM
code-switching multi-turn agent evaluation
```
 
**Kill D — cross-lingual recovery**
```
multilingual agent error recovery tool feedback
cross-lingual self-correction agent error message
localized error messages LLM agent
```
 
**Kill E — Indic agentic work**
```
Indic language LLM agent tool use
Hindi Tamil agentic evaluation benchmark
Indian language function calling LLM
```
 
**Classification rule:** "non-English agents perform worse" is not a kill (already cited). A kill is: failure measured **as a function of step count**; a proposal to control the agent's **internal working state or language**; code-mixed input as an agent task; or cross-lingual recovery measured. Check the plots, not only the abstract.
 
**Re-check log:**
- August 2026 (original): no collisions found.
- 28 Sep 2026: OmnilingualGAIA2, BabelArena, ToolBench-X found (Section 15.7). No kill triggered on any of the five categories; Indic language coverage (Kill E) has grown and must keep being checked closely.
---
 
## 19. References (IEEE) with verification status
 
[1] O. Hofman et al., "MAPS: A Multilingual Benchmark for Agent Performance and Security," in *Findings of the ACL: EACL 2026*, pp. 821–845. **Verified.**
 
[2] H. Li et al., "PolyWorkBench: Benchmarking LLM Agents for Cross-Lingual Long-Horizon Workflows," arXiv:2607.06008, 2026. **Verified.**
 
[3] Z. Luo, T. P. Kutralingam, O. N. Okoani, W. Xu, H. Wei, and X. Hu, "Lost in Execution: On the Multilingual Robustness of Tool Calling in Large Language Models," in *Proc. 64th Annu. Meeting ACL (Vol. 1: Long Papers)*, 2026, pp. 44059–44077. **Verified.**
 
[4] V. Pahuja et al., "An Actionable Diagnosis of Multilingual, Multi-Agent Planning Failures," arXiv:2608.03735, 2026. **Verified.**
 
[5] M. Kulkarni, V. Mazzia, J. Gaspers, C. Hench, and J. FitzGerald, "MASSIVE-Agents: A Benchmark for Multilingual Function-Calling in 52 Languages," in *Findings of the ACL: EMNLP 2025*, pp. 20193–20215. **Verified.**
 
[5a] A. Caciolai et al., "OmnilingualGAIA2: Evaluating the Multilingual Gap in Frontier AI Agents," arXiv:2608.08775, 2026. **Verified.**
 
[5b] P. Kuang et al., "BabelArena: A Large-Scale Multilingual Benchmark for LLM Agents," arXiv:2609.23490, 2026. **Verified.**
 
[6] S. Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models," in *Proc. ICLR*, 2023. **Verified.**
 
[7] G. Mialon et al., "GAIA: A Benchmark for General AI Assistants," in *Proc. ICLR*, 2024. **Verified.**
 
[8] S. Zhou et al., "WebArena: A Realistic Web Environment for Building Autonomous Agents," in *Proc. ICLR*, 2024. **Verified.**
 
[9] Y. Zhang et al., "DeepPlanning: Benchmarking Long-Horizon Agentic Planning with Verifiable Constraints," in *Proc. 64th Annu. Meeting ACL (Vol. 1: Long Papers)*, 2026, pp. 7377–7407. **Verified.**
 
[10] Z. Li et al., "In-the-Flow Agentic System Optimization for Effective Planning and Tool Use," in *Proc. ICLR*, 2026. **Verified.**
 
[11] X. Huang, S. Cheng, S. Huang, J. Shen, Y. Xu, C. Zhang, and Y. Qu, "QueryAgent: A Reliable and Efficient Reasoning Framework with Environmental Feedback-based Self-Correction," in *Proc. 62nd Annu. Meeting ACL (Vol. 1: Long Papers)*, 2024, pp. 5014–5035. **Verified.**
 
[12] X. Shen et al., "Metacognitive Self-Correction for Multi-Agent System via Prototype-Guided Next-Execution Reconstruction." **Venue unverified.**
 
[12a] Y. Tian et al., "Beyond Function Calling: Benchmarking Tool-Using Agents under Tool-Environment Unreliability," arXiv:2606.25819, 2026. **Verified.**
 
[13] L. Qin, Q. Chen, F. Wei, S. Huang, and W. Che, "Cross-lingual Prompting: Improving Zero-shot Chain-of-Thought Reasoning across Languages," in *Proc. EMNLP*, 2023, pp. 2695–2709. **Verified.**
 
[14] S. Jajee, A. Kumar, N. Kotecha, V. Jain, A. Chadha, and S. Bhaduri, "IndicMMLU-Pro: Benchmarking Indic Large Language Models on Multi-Task Language Understanding," in *Proc. Fifth Workshop on Generation, Evaluation and Metrics (GEM)*, pp. 102–111. **Venue verified; confirm year.**
 
[15] A. Mahmood, S. Abdaljalil, and H. Kurban, "Multilingual Prompt Localization for Agent-as-a-Judge: Language and Backbone Sensitivity in Requirement-Level Evaluation," arXiv:2604.04532, 2026. **Verified.**
 
[16] X. Fu and W. Liu, "How Reliable is Multilingual LLM-as-a-Judge?" in *Findings of the ACL: EMNLP 2025*, pp. 11040–11053. **Verified.**
 
[17] I. Chung and L. Freienthal, "Cross-Lingual Stability of LLM Judges Under Controlled Generation: Evidence from Finno-Ugric Languages," in *Proc. First Workshop on Multilingual Multicultural Evaluation*, 2026, pp. 133–148. **Verified.**
 
[18] A. S. Doğruöz, X. Liao, V. Blaschke, J. Prange, S. Li, and D. I. Adelani, "Challenges and Recommendations for LLMs-as-a-Judge in Multilingual Settings and Low-Resource Languages," arXiv:2607.02235, 2026. **Verified.**
 
[19] S. KC, "BabelJudge: Measuring LLM-as-a-Judge Reliability Across Languages and Agent Trajectories," arXiv:2606.22329, 2026. **Verified.**
 
[20] C. Wen, A. Zhu, R. Long, H. Huang, J. Jiang, and C. S. Lee, "CalibJudge: Calibrated LLM-as-a-Judge for Multilingual RAG with Uncertainty-Aware Scoring," in *Proc. CAIC 2026*, Sanya, China. DOI: 10.1145/3807246.3807349. **Verified.**
 
[21] M. Raghavendra, A. Gunjal, B. Liu, and Y. He, "Agentic Rubrics as Contextual Verifiers for SWE Agents," in *Proc. 64th Annu. Meeting ACL (Vol. 1: Long Papers)*, 2026, pp. 15265–15290. **Verified.**
 
[22] J. Sha and M. Zhu, "Verifying the Subjective: Structured Multilingual Rewards for Low-Resource Alignment," in *Findings of the ACL: ACL 2026*, pp. 23442–23474. **Verified.**
 
[23] K. Marchisio, S. Dash, H. Chen, D. Aumiller, A. Üstün, S. Hooker, and S. Ruder, "How Does Quantization Affect Multilingual LLMs?" in *Findings of the ACL: EMNLP 2024*. arXiv:2407.03211. **Verified** (abstract: non-Latin-script languages are hurt most; automatic metrics understate the damage, e.g. Japanese −1.7% automatic vs −16.0% human-rated). Not one of the 22 project PDFs; added 28 Sep 2026 to justify pinning precision per backbone.
 
---
 
## 20. Appendices
 
### Appendix A — Task templates in all language conditions
 
**travel_017** — latest morning flight under a budget, with an aisle seat and a Jain meal. (Objective changed 28 Sep 2026 from "cheapest", which left the budget unable to change the answer; seat and meal added as late constraints the same day.)
 
| Condition | Request text | Verification |
|---|---|---|
| English | Book the latest morning flight from Chennai to Delhi tomorrow, under ₹8000, with an aisle seat and a Jain meal. | author |
| Chinese | 预订明天从钦奈飞往德里的最晚一班上午航班，价格在8000卢比以内，要靠过道的座位和耆那教餐。 | pending: translator back-translation + answerability |
| Hindi | कल चेन्नई से दिल्ली की सुबह की सबसे आखिरी फ्लाइट बुक करो, ₹8000 के अंदर, आइल सीट और जैन खाने के साथ। | pending: Rishabh |
| Tamil | நாளை சென்னையிலிருந்து டெல்லிக்கு காலை நேரத்தின் கடைசி விமானத்தை ₹8000-க்குள் பதிவு செய்யுங்கள், நடைபாதை பக்க இருக்கையும் ஜெயின் உணவும் வேண்டும். | core phrase verified by Rishabh; seat/meal clause pending |
| Hinglish | Kal Chennai se Delhi ki morning ki sabse last flight book karo, budget 8000 ke andar, aisle seat aur Jain meal ke saath. | pending: Rishabh |
| Tanglish | Naalaikku Chennai la irundhu Delhi ku morning la last flight book pannunga, 8000 kulla, aisle seat um Jain meal um venum. | pending: Rishabh |
 
Answer 6E212 (09:10, ₹7900), aisle seat, Jain meal. Early decoys: lose the budget → SG118; lose "morning" → AI552; ignore the objective → AI440 (also the recovery fallback).
 
**travel_018** — cheapest flight from Delhi to Bengaluru on 25 August leaving after 17:00, with a window seat and a vegetarian meal.
 
| Condition | Request text |
|---|---|
| English | Book the cheapest flight from Delhi to Bengaluru on 25 August that leaves after 5 pm, with a window seat and a vegetarian meal. |
| Chinese | 预订8月25日从德里飞往班加罗尔、下午5点以后起飞的最便宜航班，要靠窗座位和素食餐。 |
| Hindi | 25 अगस्त को दिल्ली से बेंगलुरु की शाम 5 बजे के बाद वाली सबसे सस्ती फ्लाइट बुक करो, खिड़की वाली सीट और शाकाहारी खाने के साथ। |
| Tamil | ஆகஸ்ட் 25 அன்று டெல்லியிலிருந்து பெங்களூருக்கு மாலை 5 மணிக்குப் பிறகு புறப்படும் மிகக் குறைந்த கட்டண விமானத்தை பதிவு செய்யுங்கள், ஜன்னல் இருக்கையும் சைவ உணவும் வேண்டும். |
| Hinglish | 25 August ko Delhi se Bengaluru ki shaam 5 baje ke baad wali sabse sasti flight book karo, window seat aur veg meal ke saath. |
| Tanglish | August 25 Delhi la irundhu Bengaluru ku saayangalam 5 manikku apram kelambura cheapest flight book pannunga, window seat um veg saapadum venum. |
 
Answer AI803 (18:05, ₹5600), window seat, vegetarian meal. Early decoys: lose "after 5 pm" → 6E501; ignore the objective → UK811 (also the recovery fallback). All non-English text pending verification.
 
**travel_019** — earliest flight from Delhi to Chennai on 26 August under ₹6000, with an aisle seat and a diabetic meal.
 
| Condition | Request text |
|---|---|
| English | Book the earliest flight from Delhi to Chennai on 26 August that costs under ₹6000, with an aisle seat and a diabetic meal. |
| Chinese | 预订8月26日从德里飞往钦奈、价格低于6000卢比的最早航班，要靠过道的座位和糖尿病餐。 |
| Hindi | 26 अगस्त को दिल्ली से चेन्नई की ₹6000 से कम वाली सबसे पहली फ्लाइट बुक करो, आइल सीट और डायबिटिक खाने के साथ। |
| Tamil | ஆகஸ்ட் 26 அன்று டெல்லியிலிருந்து சென்னைக்கு ₹6000-க்குக் குறைவான கட்டணத்தில் உள்ள முதல் விமானத்தை பதிவு செய்யுங்கள், நடைபாதை பக்க இருக்கையும் நீரிழிவு நோயாளிகளுக்கான உணவும் வேண்டும். |
| Hinglish | 26 August ko Delhi se Chennai ki 6000 se kam wali sabse pehli flight book karo, aisle seat aur diabetic meal ke saath. |
| Tanglish | August 26 Delhi la irundhu Chennai ku 6000 kulla irukura first flight book pannunga, aisle seat um diabetic saapadum venum. |
 
Answer 6E223 (08:45, ₹5900), aisle seat, diabetic meal. Early decoys: lose the budget → AI439; ignore the objective → SG136 (also the recovery fallback). All non-English text pending verification.
 
The session date (2026-08-21) is given to the model in the system prompt, so relative dates are resolvable.
 
#### A.2 trip_001 (family trip organiser, docs/TRIP_SPEC.md)
 
**en:** Plan our Jaipur trip: my parents and I are flying from Chennai on 14 October and coming back on 16 October. For the flight there, take the cheapest non-stop flight that leaves before noon. For the return, take the earliest non-stop flight after 6 pm, keeping all six tickets together within ₹30,000. Book the highest-rated hotel within 3 km of Hawa Mahal that has a lift and serves a pure-veg breakfast: a double room for my parents and a single room for me. Book an SUV to pick us up at Jaipur airport when we land and take us to the hotel. On the 15th, get Amber Fort tickets for the first slot after 9 am - senior-citizen tickets for my parents and an adult ticket for me. On both flights Papa wants a window seat and Mummy an aisle seat, and I'll take a middle seat. Meals: diabetic for Papa, Jain for Mummy, vegetarian for me.
 
**zh:** 帮我安排斋浦尔之行：我和父母10月14日从钦奈出发，10月16日返回。去程选中午12点前起飞的最便宜的直飞航班。回程选晚上6点以后最早的直飞航班，但六张机票的总价要控制在30000卢比以内。酒店请订距离风之宫殿3公里以内、有电梯、只提供素食早餐的评分最高的酒店：给我父母订一间双人床房，给我订一间单人房。订一辆SUV，在我们落地时到斋浦尔机场接我们，送到酒店。15日买琥珀堡上午9点以后第一个时段的门票，我父母买老年票，我买成人票。两段航班上，爸爸要靠窗的座位，妈妈要靠过道的座位，我坐中间的座位。餐食：爸爸要糖尿病餐，妈妈要耆那教餐，我要素食餐。
 
**hi:** हमारी जयपुर ट्रिप प्लान कर दो: मैं और मेरे मम्मी-पापा 14 अक्टूबर को चेन्नई से जा रहे हैं और 16 अक्टूबर को वापस आएंगे। जाने के लिए दोपहर 12 बजे से पहले निकलने वाली सबसे सस्ती नॉन-स्टॉप फ्लाइट लो। वापसी में शाम 6 बजे के बाद की सबसे पहली नॉन-स्टॉप फ्लाइट लो, लेकिन सारे छह टिकट मिलाकर ₹30,000 के अंदर रहें। हवा महल से 3 किलोमीटर के अंदर, लिफ्ट वाला और शुद्ध शाकाहारी नाश्ता देने वाला सबसे अच्छी रेटिंग वाला होटल बुक करो: मम्मी-पापा के लिए एक डबल रूम और मेरे लिए एक सिंगल रूम। जयपुर एयरपोर्ट पर हमारे उतरते ही हमें लेने के लिए एक SUV बुक करो, जो हमें होटल तक छोड़ दे। 15 तारीख को आमेर किले के टिकट सुबह 9 बजे के बाद वाले पहले स्लॉट के लिए लो - मम्मी-पापा के लिए सीनियर सिटिज़न टिकट और मेरे लिए एडल्ट टिकट। दोनों फ्लाइट में पापा को खिड़की वाली सीट चाहिए, मम्मी को आइल सीट, और मैं बीच वाली सीट ले लूँगा। खाना: पापा के लिए डायबिटिक, मम्मी के लिए जैन, और मेरे लिए शाकाहारी।
 
**ta:** எங்கள் ஜெய்ப்பூர் பயணத்தைத் திட்டமிடுங்கள்: நானும் என் அப்பா அம்மாவும் அக்டோபர் 14 அன்று சென்னையிலிருந்து புறப்பட்டு அக்டோபர் 16 அன்று திரும்புகிறோம். போகும்போது மதியம் 12 மணிக்கு முன் புறப்படும், மிகக் குறைந்த கட்டணமுள்ள நேரடி (நான்-ஸ்டாப்) விமானத்தை எடுங்கள். திரும்பும்போது மாலை 6 மணிக்குப் பிறகு புறப்படும் முதல் நேரடி விமானத்தை எடுங்கள், ஆனால் ஆறு டிக்கெட்டுகளும் சேர்த்து ₹30,000-க்குள் இருக்க வேண்டும். ஹவா மஹாலிலிருந்து 3 கி.மீ.க்குள் இருக்கும், லிஃப்ட் உள்ள, சுத்த சைவ காலை உணவு தரும் ஹோட்டல்களில் மிக அதிக மதிப்பீடு பெற்றதை புக் செய்யுங்கள்: அப்பா அம்மாவுக்கு ஒரு டபுள் ரூம், எனக்கு ஒரு சிங்கிள் ரூம். நாங்கள் ஜெய்ப்பூர் விமான நிலையத்தில் இறங்கியதும் எங்களை அழைத்துச் சென்று ஹோட்டலில் விட ஒரு SUV புக் செய்யுங்கள். 15 ஆம் தேதி ஆமேர் கோட்டைக்கு காலை 9 மணிக்குப் பிறகு உள்ள முதல் நேர ஸ்லாட்டுக்கு டிக்கெட் வாங்குங்கள் - அப்பா அம்மாவுக்கு மூத்த குடிமக்கள் டிக்கெட், எனக்கு சாதாரண பெரியவர்களுக்கான (அடல்ட்) டிக்கெட். இரண்டு விமானங்களிலும் அப்பாவுக்கு ஜன்னல் இருக்கை, அம்மாவுக்கு நடைபாதை பக்க இருக்கை, எனக்கு நடு இருக்கை. உணவு: அப்பாவுக்கு நீரிழிவு நோயாளிகளுக்கான உணவு, அம்மாவுக்கு ஜெயின் உணவு, எனக்கு சைவ உணவு.
 
**hinglish:** Hamari Jaipur trip plan kar do: main aur mere mummy-papa 14 October ko Chennai se ja rahe hain aur 16 October ko wapas aayenge. Jaane ke liye dopahar 12 baje se pehle nikalne wali sabse sasti non-stop flight lo. Wapsi mein shaam 6 baje ke baad ki sabse pehli non-stop flight lo, but saare 6 tickets mila ke ₹30,000 ke andar rehne chahiye. Hawa Mahal se 3 km ke andar, lift wala aur pure veg breakfast dene wala sabse high-rated hotel book karo: mummy-papa ke liye ek double room aur mere liye ek single room. Jaipur airport pe land karte hi humein pick karne ke liye ek SUV book karo jo hotel tak chhod de. 15 tareekh ko Amber Fort ke tickets subah 9 baje ke baad wale pehle slot ke liye lo - mummy-papa ke liye senior citizen ticket aur mere liye adult ticket. Dono flights mein papa ko window seat chahiye, mummy ko aisle seat, aur main middle seat le lunga. Khana: papa ke liye diabetic, mummy ke liye Jain, aur mere liye veg.
 
#### A.3 trip_002–trip_005 (please check hi / ta / hinglish)
 
**trip_002** (Bengaluru-Jaipur: latest outbound before 10:00; latest return before 21:00 under a joint budget; top-rated hotel under a nightly budget; twin + single; sedan at landing; City Palace last slot before 16:00.)
 
*en:* Plan our Jaipur trip: my parents and I are flying from Bengaluru on 6 November and coming back on 8 November. For the flight there, take the latest non-stop flight that leaves before 10 am. For the return, take the latest non-stop flight that leaves before 9 pm, as long as all six tickets together stay within ₹42,000. Book the highest-rated hotel within 2 km of Hawa Mahal that has a lift and whose rooms start at no more than ₹4,000 a night: a twin room for my parents and a single room for me. Book a sedan to pick us up at Jaipur airport when we land and take us to the hotel. On the 7th, get City Palace tickets for the last slot before 4 pm - senior-citizen tickets for my parents and an adult ticket for me. On both flights I want a window seat, and Papa and Mummy both want aisle seats. Meals: vegetarian for me and for Papa, diabetic for Mummy.
 
*zh:* 帮我安排斋浦尔之行：我和父母11月6日从班加罗尔出发，11月8日返回。去程选上午10点前起飞的最晚一班直飞航班。回程选晚上9点前起飞的最晚一班直飞航班，但六张机票的总价要控制在42000卢比以内。酒店请订距离风之宫殿2公里以内、有电梯、房价每晚最低不超过4000卢比的评分最高的酒店：给我父母订一间双床房，给我订一间单人房。订一辆轿车，在我们落地时到斋浦尔机场接我们，送到酒店。7日买城市宫殿下午4点前最后一个时段的门票，我父母买老年票，我买成人票。两段航班上，我要靠窗的座位，爸爸和妈妈都要靠过道的座位。餐食：我和爸爸要素食餐，妈妈要糖尿病餐。
 
*hi:* हमारी जयपुर ट्रिप प्लान कर दो: मैं और मेरे मम्मी-पापा 6 नवंबर को बेंगलुरु से जा रहे हैं और 8 नवंबर को वापस आएंगे। जाने के लिए सुबह 10 बजे से पहले निकलने वाली सबसे आखिरी नॉन-स्टॉप फ्लाइट लो। वापसी में रात 9 बजे से पहले निकलने वाली सबसे आखिरी नॉन-स्टॉप फ्लाइट लो, लेकिन सारे छह टिकट मिलाकर ₹42,000 के अंदर रहें। हवा महल से 2 किलोमीटर के अंदर, लिफ्ट वाला और जिसके कमरे ₹4,000 प्रति रात या उससे कम से शुरू होते हों, ऐसा सबसे अच्छी रेटिंग वाला होटल बुक करो: मम्मी-पापा के लिए एक ट्विन रूम और मेरे लिए एक सिंगल रूम। जयपुर एयरपोर्ट पर हमारे उतरते ही हमें लेने के लिए एक सेडान बुक करो, जो हमें होटल तक छोड़ दे। 7 तारीख को सिटी पैलेस के टिकट शाम 4 बजे से पहले वाले आखिरी स्लॉट के लिए लो - मम्मी-पापा के लिए सीनियर सिटिज़न टिकट और मेरे लिए एडल्ट टिकट। दोनों फ्लाइट में मुझे खिड़की वाली सीट चाहिए, और पापा-मम्मी दोनों को आइल सीट। खाना: मेरे और पापा के लिए शाकाहारी, मम्मी के लिए डायबिटिक।
 
*ta:* எங்கள் ஜெய்ப்பூர் பயணத்தைத் திட்டமிடுங்கள்: நானும் என் அப்பா அம்மாவும் நவம்பர் 6 அன்று பெங்களூருவிலிருந்து புறப்பட்டு நவம்பர் 8 அன்று திரும்புகிறோம். போகும்போது காலை 10 மணிக்கு முன் புறப்படும் நேரடி (நான்-ஸ்டாப்) விமானங்களில் கடைசியாகப் புறப்படுவதை எடுங்கள். திரும்பும்போது இரவு 9 மணிக்கு முன் புறப்படும் நேரடி விமானங்களில் கடைசியாகப் புறப்படுவதை எடுங்கள், ஆனால் ஆறு டிக்கெட்டுகளும் சேர்த்து ₹42,000-க்குள் இருக்க வேண்டும். ஹவா மஹாலிலிருந்து 2 கி.மீ.க்குள் இருக்கும், லிஃப்ட் உள்ள, அறைகள் ஒரு இரவுக்கு ₹4,000 அல்லது அதற்குக் குறைவான விலையில் தொடங்கும் ஹோட்டல்களில் மிக அதிக மதிப்பீடு பெற்றதை புக் செய்யுங்கள்: அப்பா அம்மாவுக்கு ஒரு ட்வின் ரூம், எனக்கு ஒரு சிங்கிள் ரூம். நாங்கள் ஜெய்ப்பூர் விமான நிலையத்தில் இறங்கியதும் எங்களை அழைத்துச் சென்று ஹோட்டலில் விட ஒரு செடான் கார் புக் செய்யுங்கள். 7 ஆம் தேதி சிட்டி பேலஸுக்கு மாலை 4 மணிக்கு முன் உள்ள கடைசி நேர ஸ்லாட்டுக்கு டிக்கெட் வாங்குங்கள் - அப்பா அம்மாவுக்கு மூத்த குடிமக்கள் டிக்கெட், எனக்கு சாதாரண பெரியவர்களுக்கான (அடல்ட்) டிக்கெட். இரண்டு விமானங்களிலும் எனக்கு ஜன்னல் இருக்கை, அப்பா அம்மா இருவருக்கும் நடைபாதை பக்க இருக்கை. உணவு: எனக்கும் அப்பாவுக்கும் சைவ உணவு, அம்மாவுக்கு நீரிழிவு நோயாளிகளுக்கான உணவு.
 
*hinglish:* Hamari Jaipur trip plan kar do: main aur mere mummy-papa 6 November ko Bengaluru se ja rahe hain aur 8 November ko wapas aayenge. Jaane ke liye subah 10 baje se pehle nikalne wali sabse last non-stop flight lo. Wapsi mein raat 9 baje se pehle nikalne wali sabse last non-stop flight lo, but saare 6 tickets mila ke ₹42,000 ke andar rehne chahiye. Hawa Mahal se 2 km ke andar, lift wala aur jiske rooms ₹4,000 per night ya usse kam se start hote hon, aisa sabse high-rated hotel book karo: mummy-papa ke liye ek twin room aur mere liye ek single room. Jaipur airport pe land karte hi humein pick karne ke liye ek sedan book karo jo hotel tak chhod de. 7 tareekh ko City Palace ke tickets shaam 4 baje se pehle wale last slot ke liye lo - mummy-papa ke liye senior citizen ticket aur mere liye adult ticket. Dono flights mein mujhe window seat chahiye, aur papa-mummy dono ko aisle seat. Khana: mere aur papa ke liye veg, mummy ke liye diabetic.
 
**trip_003** (Hyderabad-Jaipur: cheapest outbound after 07:00; earliest return after 16:00 under a joint budget; top-rated hotel under a nightly budget; suite + single; SUV at landing; Hawa Mahal first slot after 10:00; student ticket for self.)
 
*en:* Plan our Jaipur trip: my parents and I are flying from Hyderabad on 20 November and coming back on 22 November. For the flight there, take the cheapest non-stop flight that leaves after 7 am. For the return, take the earliest non-stop flight after 4 pm, keeping all six tickets together within ₹36,000. Book the highest-rated hotel within 3 km of Hawa Mahal whose rooms start at no more than ₹3,500 a night: a suite for my parents and a single room for me. Book an SUV to pick us up at Jaipur airport when we land and take us to the hotel. On the 21st, get Hawa Mahal tickets for the first slot after 10 am - senior-citizen tickets for my parents and a student ticket for me. On both flights I want a window seat, Mummy a middle seat and Papa an aisle seat. Meals: Jain for me and for Mummy, diabetic for Papa.
 
*zh:* 帮我安排斋浦尔之行：我和父母11月20日从海得拉巴出发，11月22日返回。去程选上午7点以后起飞的最便宜的直飞航班。回程选下午4点以后最早的直飞航班，但六张机票的总价要控制在36000卢比以内。酒店请订距离风之宫殿3公里以内、房价每晚最低不超过3500卢比的评分最高的酒店：给我父母订一间套房，给我订一间单人房。订一辆SUV，在我们落地时到斋浦尔机场接我们，送到酒店。21日买风之宫殿上午10点以后第一个时段的门票，我父母买老年票，我买学生票。两段航班上，我要靠窗的座位，妈妈要中间的座位，爸爸要靠过道的座位。餐食：我和妈妈要耆那教餐，爸爸要糖尿病餐。
 
*hi:* हमारी जयपुर ट्रिप प्लान कर दो: मैं और मेरे मम्मी-पापा 20 नवंबर को हैदराबाद से जा रहे हैं और 22 नवंबर को वापस आएंगे। जाने के लिए सुबह 7 बजे के बाद निकलने वाली सबसे सस्ती नॉन-स्टॉप फ्लाइट लो। वापसी में शाम 4 बजे के बाद की सबसे पहली नॉन-स्टॉप फ्लाइट लो, लेकिन सारे छह टिकट मिलाकर ₹36,000 के अंदर रहें। हवा महल से 3 किलोमीटर के अंदर, जिसके कमरे ₹3,500 प्रति रात या उससे कम से शुरू होते हों, ऐसा सबसे अच्छी रेटिंग वाला होटल बुक करो: मम्मी-पापा के लिए एक सुइट और मेरे लिए एक सिंगल रूम। जयपुर एयरपोर्ट पर हमारे उतरते ही हमें लेने के लिए एक SUV बुक करो, जो हमें होटल तक छोड़ दे। 21 तारीख को हवा महल के टिकट सुबह 10 बजे के बाद वाले पहले स्लॉट के लिए लो - मम्मी-पापा के लिए सीनियर सिटिज़न टिकट और मेरे लिए स्टूडेंट टिकट। दोनों फ्लाइट में मुझे खिड़की वाली सीट चाहिए, मम्मी को बीच वाली सीट और पापा को आइल सीट। खाना: मेरे और मम्मी के लिए जैन, पापा के लिए डायबिटिक।
 
*ta:* எங்கள் ஜெய்ப்பூர் பயணத்தைத் திட்டமிடுங்கள்: நானும் என் அப்பா அம்மாவும் நவம்பர் 20 அன்று ஹைதராபாத்திலிருந்து புறப்பட்டு நவம்பர் 22 அன்று திரும்புகிறோம். போகும்போது காலை 7 மணிக்குப் பிறகு புறப்படும், மிகக் குறைந்த கட்டணமுள்ள நேரடி (நான்-ஸ்டாப்) விமானத்தை எடுங்கள். திரும்பும்போது மாலை 4 மணிக்குப் பிறகு புறப்படும் முதல் நேரடி விமானத்தை எடுங்கள், ஆனால் ஆறு டிக்கெட்டுகளும் சேர்த்து ₹36,000-க்குள் இருக்க வேண்டும். ஹவா மஹாலிலிருந்து 3 கி.மீ.க்குள் இருக்கும், அறைகள் ஒரு இரவுக்கு ₹3,500 அல்லது அதற்குக் குறைவான விலையில் தொடங்கும் ஹோட்டல்களில் மிக அதிக மதிப்பீடு பெற்றதை புக் செய்யுங்கள்: அப்பா அம்மாவுக்கு ஒரு சூட் ரூம், எனக்கு ஒரு சிங்கிள் ரூம். நாங்கள் ஜெய்ப்பூர் விமான நிலையத்தில் இறங்கியதும் எங்களை அழைத்துச் சென்று ஹோட்டலில் விட ஒரு SUV புக் செய்யுங்கள். 21 ஆம் தேதி ஹவா மஹாலுக்கு காலை 10 மணிக்குப் பிறகு உள்ள முதல் நேர ஸ்லாட்டுக்கு டிக்கெட் வாங்குங்கள் - அப்பா அம்மாவுக்கு மூத்த குடிமக்கள் டிக்கெட், எனக்கு மாணவர் (ஸ்டூடன்ட்) டிக்கெட். இரண்டு விமானங்களிலும் எனக்கு ஜன்னல் இருக்கை, அம்மாவுக்கு நடு இருக்கை, அப்பாவுக்கு நடைபாதை பக்க இருக்கை. உணவு: எனக்கும் அம்மாவுக்கும் ஜெயின் உணவு, அப்பாவுக்கு நீரிழிவு நோயாளிகளுக்கான உணவு.
 
*hinglish:* Hamari Jaipur trip plan kar do: main aur mere mummy-papa 20 November ko Hyderabad se ja rahe hain aur 22 November ko wapas aayenge. Jaane ke liye subah 7 baje ke baad nikalne wali sabse sasti non-stop flight lo. Wapsi mein shaam 4 baje ke baad ki sabse pehli non-stop flight lo, but saare 6 tickets mila ke ₹36,000 ke andar rehne chahiye. Hawa Mahal se 3 km ke andar, jiske rooms ₹3,500 per night ya usse kam se start hote hon, aisa sabse high-rated hotel book karo: mummy-papa ke liye ek suite aur mere liye ek single room. Jaipur airport pe land karte hi humein pick karne ke liye ek SUV book karo jo hotel tak chhod de. 21 tareekh ko Hawa Mahal ke tickets subah 10 baje ke baad wale pehle slot ke liye lo - mummy-papa ke liye senior citizen ticket aur mere liye student ticket. Dono flights mein mujhe window seat chahiye, mummy ko middle seat aur papa ko aisle seat. Khana: mere aur mummy ke liye Jain, papa ke liye diabetic.
 
**trip_004** (Mumbai-Jaipur: earliest outbound after 08:00; latest return before 20:00 under a joint budget; top-rated hotel under a nightly budget within 6 km; double + single; tempo traveller at landing; Jantar Mantar last slot before 14:00.)
 
*en:* Plan our Jaipur trip: my parents and I are flying from Mumbai on 4 December and coming back on 6 December. For the flight there, take the earliest non-stop flight that leaves after 8 am. For the return, take the latest non-stop flight that leaves before 8 pm, keeping all six tickets together within ₹33,000. Book the highest-rated hotel within 6 km of Hawa Mahal whose rooms start at no more than ₹6,000 a night: a double room for my parents and a single room for me. We have a lot of luggage, so book a tempo traveller to pick us up at Jaipur airport when we land and take us to the hotel. On the 5th, get Jantar Mantar tickets for the last slot before 2 pm - senior-citizen tickets for my parents and an adult ticket for me. On both flights Papa wants a window seat and Mummy an aisle seat, and I'll take a middle seat. Meals: diabetic for me, lacto-vegetarian for Mummy, vegetarian for Papa.
 
*zh:* 帮我安排斋浦尔之行：我和父母12月4日从孟买出发，12月6日返回。去程选上午8点以后最早的直飞航班。回程选晚上8点前起飞的最晚一班直飞航班，但六张机票的总价要控制在33000卢比以内。酒店请订距离风之宫殿6公里以内、房价每晚最低不超过6000卢比的评分最高的酒店：给我父母订一间双人床房，给我订一间单人房。我们行李很多，所以请订一辆Tempo Traveller面包车，在我们落地时到斋浦尔机场接我们，送到酒店。5日买简塔·曼塔天文台下午2点前最后一个时段的门票，我父母买老年票，我买成人票。两段航班上，爸爸要靠窗的座位，妈妈要靠过道的座位，我坐中间的座位。餐食：我要糖尿病餐，妈妈要奶素餐，爸爸要素食餐。
 
*hi:* हमारी जयपुर ट्रिप प्लान कर दो: मैं और मेरे मम्मी-पापा 4 दिसंबर को मुंबई से जा रहे हैं और 6 दिसंबर को वापस आएंगे। जाने के लिए सुबह 8 बजे के बाद निकलने वाली सबसे पहली नॉन-स्टॉप फ्लाइट लो। वापसी में रात 8 बजे से पहले निकलने वाली सबसे आखिरी नॉन-स्टॉप फ्लाइट लो, लेकिन सारे छह टिकट मिलाकर ₹33,000 के अंदर रहें। हवा महल से 6 किलोमीटर के अंदर, जिसके कमरे ₹6,000 प्रति रात या उससे कम से शुरू होते हों, ऐसा सबसे अच्छी रेटिंग वाला होटल बुक करो: मम्मी-पापा के लिए एक डबल रूम और मेरे लिए एक सिंगल रूम। हमारे पास सामान बहुत है, इसलिए जयपुर एयरपोर्ट पर हमारे उतरते ही हमें लेने के लिए एक टेम्पो ट्रैवलर बुक करो, जो हमें होटल तक छोड़ दे। 5 तारीख को जंतर मंतर के टिकट दोपहर 2 बजे से पहले वाले आखिरी स्लॉट के लिए लो - मम्मी-पापा के लिए सीनियर सिटिज़न टिकट और मेरे लिए एडल्ट टिकट। दोनों फ्लाइट में पापा को खिड़की वाली सीट चाहिए, मम्मी को आइल सीट, और मैं बीच वाली सीट ले लूँगा। खाना: मेरे लिए डायबिटिक, मम्मी के लिए लैक्टो-वेजिटेरियन, और पापा के लिए शाकाहारी।
 
*ta:* எங்கள் ஜெய்ப்பூர் பயணத்தைத் திட்டமிடுங்கள்: நானும் என் அப்பா அம்மாவும் டிசம்பர் 4 அன்று மும்பையிலிருந்து புறப்பட்டு டிசம்பர் 6 அன்று திரும்புகிறோம். போகும்போது காலை 8 மணிக்குப் பிறகு புறப்படும் முதல் நேரடி (நான்-ஸ்டாப்) விமானத்தை எடுங்கள். திரும்பும்போது இரவு 8 மணிக்கு முன் புறப்படும் நேரடி விமானங்களில் கடைசியாகப் புறப்படுவதை எடுங்கள், ஆனால் ஆறு டிக்கெட்டுகளும் சேர்த்து ₹33,000-க்குள் இருக்க வேண்டும். ஹவா மஹாலிலிருந்து 6 கி.மீ.க்குள் இருக்கும், அறைகள் ஒரு இரவுக்கு ₹6,000 அல்லது அதற்குக் குறைவான விலையில் தொடங்கும் ஹோட்டல்களில் மிக அதிக மதிப்பீடு பெற்றதை புக் செய்யுங்கள்: அப்பா அம்மாவுக்கு ஒரு டபுள் ரூம், எனக்கு ஒரு சிங்கிள் ரூம். எங்களிடம் நிறைய லக்கேஜ் இருப்பதால், நாங்கள் ஜெய்ப்பூர் விமான நிலையத்தில் இறங்கியதும் எங்களை அழைத்துச் சென்று ஹோட்டலில் விட ஒரு டெம்போ டிராவலர் புக் செய்யுங்கள். 5 ஆம் தேதி ஜந்தர் மந்தருக்கு மதியம் 2 மணிக்கு முன் உள்ள கடைசி நேர ஸ்லாட்டுக்கு டிக்கெட் வாங்குங்கள் - அப்பா அம்மாவுக்கு மூத்த குடிமக்கள் டிக்கெட், எனக்கு சாதாரண பெரியவர்களுக்கான (அடல்ட்) டிக்கெட். இரண்டு விமானங்களிலும் அப்பாவுக்கு ஜன்னல் இருக்கை, அம்மாவுக்கு நடைபாதை பக்க இருக்கை, எனக்கு நடு இருக்கை. உணவு: எனக்கு நீரிழிவு நோயாளிகளுக்கான உணவு, அம்மாவுக்கு பால் சேர்ந்த சைவ (லாக்டோ-வெஜிடேரியன்) உணவு, அப்பாவுக்கு சைவ உணவு.
 
*hinglish:* Hamari Jaipur trip plan kar do: main aur mere mummy-papa 4 December ko Mumbai se ja rahe hain aur 6 December ko wapas aayenge. Jaane ke liye subah 8 baje ke baad nikalne wali sabse pehli non-stop flight lo. Wapsi mein raat 8 baje se pehle nikalne wali sabse last non-stop flight lo, but saare 6 tickets mila ke ₹33,000 ke andar rehne chahiye. Hawa Mahal se 6 km ke andar, jiske rooms ₹6,000 per night ya usse kam se start hote hon, aisa sabse high-rated hotel book karo: mummy-papa ke liye ek double room aur mere liye ek single room. Humare paas luggage bahut hai, isliye Jaipur airport pe land karte hi humein pick karne ke liye ek tempo traveller book karo jo hotel tak chhod de. 5 tareekh ko Jantar Mantar ke tickets dopahar 2 baje se pehle wale last slot ke liye lo - mummy-papa ke liye senior citizen ticket aur mere liye adult ticket. Dono flights mein papa ko window seat chahiye, mummy ko aisle seat, aur main middle seat le lunga. Khana: mere liye diabetic, mummy ke liye lacto-vegetarian, aur papa ke liye veg.
 
**trip_005** (Kolkata-Jaipur: cheapest outbound before 11:00; earliest return after 15:00 under a joint budget; top-rated veg-breakfast hotel under a nightly budget; twin + single; sedan at landing; Nahargarh Fort first slot after 12:00; student ticket for self.)
 
*en:* Plan our Jaipur trip: my parents and I are flying from Kolkata on 18 December and coming back on 20 December. For the flight there, take the cheapest non-stop flight that leaves before 11 am. For the return, take the earliest non-stop flight after 3 pm, keeping all six tickets together within ₹39,000. Book the highest-rated hotel within 3 km of Hawa Mahal that serves a pure-veg breakfast and whose rooms start at no more than ₹3,500 a night: a twin room for my parents and a single room for me. Book a sedan to pick us up at Jaipur airport when we land and take us to the hotel. On the 19th, get Nahargarh Fort tickets for the first slot after 12 noon - senior-citizen tickets for my parents and a student ticket for me. On both flights Papa and I want window seats and Mummy wants an aisle seat. Meals: vegetarian for me, Jain for Mummy, lacto-vegetarian for Papa.
 
*zh:* 帮我安排斋浦尔之行：我和父母12月18日从加尔各答出发，12月20日返回。去程选上午11点前起飞的最便宜的直飞航班。回程选下午3点以后最早的直飞航班，但六张机票的总价要控制在39000卢比以内。酒店请订距离风之宫殿3公里以内、只提供素食早餐、房价每晚最低不超过3500卢比的评分最高的酒店：给我父母订一间双床房，给我订一间单人房。订一辆轿车，在我们落地时到斋浦尔机场接我们，送到酒店。19日买纳哈加尔堡中午12点以后第一个时段的门票，我父母买老年票，我买学生票。两段航班上，爸爸和我都要靠窗的座位，妈妈要靠过道的座位。餐食：我要素食餐，妈妈要耆那教餐，爸爸要奶素餐。
 
*hi:* हमारी जयपुर ट्रिप प्लान कर दो: मैं और मेरे मम्मी-पापा 18 दिसंबर को कोलकाता से जा रहे हैं और 20 दिसंबर को वापस आएंगे। जाने के लिए सुबह 11 बजे से पहले निकलने वाली सबसे सस्ती नॉन-स्टॉप फ्लाइट लो। वापसी में दोपहर 3 बजे के बाद की सबसे पहली नॉन-स्टॉप फ्लाइट लो, लेकिन सारे छह टिकट मिलाकर ₹39,000 के अंदर रहें। हवा महल से 3 किलोमीटर के अंदर, शुद्ध शाकाहारी नाश्ता देने वाला और जिसके कमरे ₹3,500 प्रति रात या उससे कम से शुरू होते हों, ऐसा सबसे अच्छी रेटिंग वाला होटल बुक करो: मम्मी-पापा के लिए एक ट्विन रूम और मेरे लिए एक सिंगल रूम। जयपुर एयरपोर्ट पर हमारे उतरते ही हमें लेने के लिए एक सेडान बुक करो, जो हमें होटल तक छोड़ दे। 19 तारीख को नाहरगढ़ किले के टिकट दोपहर 12 बजे के बाद वाले पहले स्लॉट के लिए लो - मम्मी-पापा के लिए सीनियर सिटिज़न टिकट और मेरे लिए स्टूडेंट टिकट। दोनों फ्लाइट में पापा को और मुझे खिड़की वाली सीट चाहिए, और मम्मी को आइल सीट। खाना: मेरे लिए शाकाहारी, मम्मी के लिए जैन, और पापा के लिए लैक्टो-वेजिटेरियन।
 
*ta:* எங்கள் ஜெய்ப்பூர் பயணத்தைத் திட்டமிடுங்கள்: நானும் என் அப்பா அம்மாவும் டிசம்பர் 18 அன்று கொல்கத்தாவிலிருந்து புறப்பட்டு டிசம்பர் 20 அன்று திரும்புகிறோம். போகும்போது காலை 11 மணிக்கு முன் புறப்படும், மிகக் குறைந்த கட்டணமுள்ள நேரடி (நான்-ஸ்டாப்) விமானத்தை எடுங்கள். திரும்பும்போது மதியம் 3 மணிக்குப் பிறகு புறப்படும் முதல் நேரடி விமானத்தை எடுங்கள், ஆனால் ஆறு டிக்கெட்டுகளும் சேர்த்து ₹39,000-க்குள் இருக்க வேண்டும். ஹவா மஹாலிலிருந்து 3 கி.மீ.க்குள் இருக்கும், சுத்த சைவ காலை உணவு தரும், அறைகள் ஒரு இரவுக்கு ₹3,500 அல்லது அதற்குக் குறைவான விலையில் தொடங்கும் ஹோட்டல்களில் மிக அதிக மதிப்பீடு பெற்றதை புக் செய்யுங்கள்: அப்பா அம்மாவுக்கு ஒரு ட்வின் ரூம், எனக்கு ஒரு சிங்கிள் ரூம். நாங்கள் ஜெய்ப்பூர் விமான நிலையத்தில் இறங்கியதும் எங்களை அழைத்துச் சென்று ஹோட்டலில் விட ஒரு செடான் கார் புக் செய்யுங்கள். 19 ஆம் தேதி நாஹர்கர் கோட்டைக்கு மதியம் 12 மணிக்குப் பிறகு உள்ள முதல் நேர ஸ்லாட்டுக்கு டிக்கெட் வாங்குங்கள் - அப்பா அம்மாவுக்கு மூத்த குடிமக்கள் டிக்கெட், எனக்கு மாணவர் (ஸ்டூடன்ட்) டிக்கெட். இரண்டு விமானங்களிலும் அப்பாவுக்கும் எனக்கும் ஜன்னல் இருக்கை, அம்மாவுக்கு நடைபாதை பக்க இருக்கை. உணவு: எனக்கு சைவ உணவு, அம்மாவுக்கு ஜெயின் உணவு, அப்பாவுக்கு பால் சேர்ந்த சைவ (லாக்டோ-வெஜிடேரியன்) உணவு.
 
*hinglish:* Hamari Jaipur trip plan kar do: main aur mere mummy-papa 18 December ko Kolkata se ja rahe hain aur 20 December ko wapas aayenge. Jaane ke liye subah 11 baje se pehle nikalne wali sabse sasti non-stop flight lo. Wapsi mein dopahar 3 baje ke baad ki sabse pehli non-stop flight lo, but saare 6 tickets mila ke ₹39,000 ke andar rehne chahiye. Hawa Mahal se 3 km ke andar, pure veg breakfast dene wala aur jiske rooms ₹3,500 per night ya usse kam se start hote hon, aisa sabse high-rated hotel book karo: mummy-papa ke liye ek twin room aur mere liye ek single room. Jaipur airport pe land karte hi humein pick karne ke liye ek sedan book karo jo hotel tak chhod de. 19 tareekh ko Nahargarh Fort ke tickets dopahar 12 baje ke baad wale pehle slot ke liye lo - mummy-papa ke liye senior citizen ticket aur mere liye student ticket. Dono flights mein papa ko aur mujhe window seat chahiye, aur mummy ko aisle seat. Khana: mere liye veg, mummy ke liye Jain, aur papa ke liye lacto-vegetarian.
 
### Appendix B — Gold trajectory format (horizon 6, ASCII only)
 
```json
{
  "task_id": "travel_017_h6",
  "horizon": 6,
  "template_id": "travel_017",
  "entities": {"origin": "MAA", "destination": "DEL"},
  "constraints": {"date": "2026-08-22", "depart_before": "12:00", "max_price": 8000,
                  "objective": "latest_departure"},
  "late_constraints": {"seat_type": "aisle", "meal": "jain"},
  "terminal_state": {"booking.flight_id": "6E212", "booking.price": 7900,
                     "booking.seat_type": "aisle", "booking.meal": "jain"},
  "recovery_fallback": "AI440",
  "decoys": {"depart_before": "AI552", "max_price": "SG118", "objective": "AI440"},
  "gold_steps": [
    {"tool": "resolve_city", "args": {"name": "Chennai"}, "returns": {"code": "MAA"}},
    {"tool": "resolve_city", "args": {"name": "Delhi"}, "returns": {"code": "DEL"}},
    {"tool": "search_flights", "args": {"origin": "MAA", "destination": "DEL", "date": "2026-08-22"}},
    {"tool": "filter_flights", "args": {"depart_before": "12:00", "max_price": 8000}},
    {"tool": "get_seat_availability", "args": {"flight_id": "6E212"}, "returns": {"hold_token": "H-6E212-STD"}},
    {"tool": "book_flight", "args": {"flight_id": "6E212", "hold_token": "H-6E212-STD",
                                     "seat_type": "aisle", "meal": "jain"}}
  ]
}
```
 
Generated by `python -m tasks.build_gold`; never edited by hand.
 
### Appendix C — Run config cells (mock injection and real model)
 
```yaml
- name: recover_notfound_en
  policy: mock
  mock_mode: recover
  seeds: [1]
  inject: {error_type: not_found, at_tool: book_flight, message_language: en}
 
- name: qwen36_27b_think
  policy: openai_compat
  model: Qwen/Qwen3.6-27B
  base_url: http://localhost:8000/v1
  temperature: 0.6
  max_tokens: 8192
  extra_body: {chat_template_kwargs: {enable_thinking: true}}
  seeds: [1, 2, 3]
```
 
For the injected cell, the flight is marked sold out for the rest of the episode, so the only valid recovery is `recovery_fallback` (AI440). The verifier scores `success` against the best remaining option, and `recovered = success` on injected episodes.
 
### Appendix D — Repository structure and development workflow
 
**Compute setup (decided 28 Sep 2026):** GitHub is the single source of truth for code. Everything that doesn't need a GPU (environment, tasks, verifier, stats) is written and debugged locally. Serving open-weight models (and the optional SFT ablation) runs on **Google Colab Pro** (A100, 80GB VRAM; ~150GB system RAM) with vLLM — no institutional lab access. Colab sessions `git clone`/`git pull` the repo at the start of each session rather than syncing code through Drive; raw run logs go to Google Drive (they survive disconnects, and the runner resumes from them), and condensed results get committed back to GitHub at the end of a session. A laptop with Ollama can run the same policy for debugging; its results are never reported.
 
```
xlingual-drift/
  README.md           # setup, dev workflow, how to run a real model
  requirements.txt
  pytest.ini
  .gitignore
  .env.example        # API key placeholders (never commit the real .env)
  docs/
    PHASE1_SPEC.md    # environment, template, gold, injection and model-serving design
  env/
    tools/            # travel_tools.py, schemas.py (per horizon), horizons.py (horizon profiles)
    data/             # flights.py (decoy-annotated), error_messages.json (en/zh/hi/ta/hinglish)
    aliases/          # multilingual alias tables for lenient mode
    inject.py         # failure injection (by tool or step)
  tasks/
    templates/        # one file per template, all languages + verification status
    gold/             # gold trajectories per (template, horizon), with decoys and fallback
  agent/
    policies/         # mock_policy.py (scripted), openai_compat_policy.py (any model)
    prompts/          # system_v1.txt (versioned system prompt)
    react_loop.py
    mitigations/      # ledger, reanchor, error_localise, tart_static (stubs)
  eval/
    run_grid.py       # CLI: horizon x language x cell x seed grid, resumable
    verifier.py       # success given state, constraint survival, displacement, recovery
    metrics.py        # quick summaries
    stats/            # mixed-effects and survival analysis (Phase 5)
  tests/              # 40 pytest checks
  configs/            # smoke_test, capability_gate, local_ollama_debug
  notebooks/
    colab_runner.ipynb  # clone, start vLLM, run gate, summarise, commit summary
  runs/               # raw logs (jsonl), one line per episode — gitignored; on Drive in Colab
```
 
### Appendix E — Run log fields (one JSON line per episode)
 
Implemented: `episode_key, run_name, task_id, template_id, horizon, language, interface_mode, cell, policy, model, extra_body (thinking setting), seed, error_type, inject_at_tool, message_language, success, matches_gold_terminal, booked_flight, constraint_survival (per constraint), all_constraints_survived, fact_displacements, first_error_step, num_steps_taken, extra_steps, injected, injected_at_step, recovered, hit_step_limit, final_text, latency_s, steps (full trajectory), transcript (messages, per-turn reasoning, token usage, prompt version)`. Endpoint failures are logged as `infra_error` with no score; analyses keep the last scored row per `episode_key`.
 
To add: `seam, plan_mode, mitigation, schema_tokens`
 
### Appendix F — Architecture (text version of the diagram)
 
```
Tool environment (10-15 deterministic tools) --+
Task templates (horizon 2/4/6/8)              --+--> Language condition generator (EN / ZH / HI / TA / Hinglish)
Gold trajectories + decoys -------------------+          |
                                               |          v
                                               |   Seam placement (request / tool output / error message)
                                               |          |
                                               |          v
                                               |   Equivalence + answerability + script-hygiene checks (before any run)
                                               |          |
                                               |          v
                                               |   Interface mode (strict / lenient) x Plan mode (own / oracle)
                                               |          |
                                               |          v
                                               |   Agent under test (open-weight models via vLLM, one policy, ReAct loop) <--> Failure injection
                                               |          |
                                               +--------> Deterministic verifier (diff vs gold)
                                                          |
                                     +--------------------+--------------------+
                                     v                                         v
                        Characterisation metrics                     Recovery metrics
            (success x horizon, drift slope, first-error,    (recovery rate, retries, propagation depth)
             constraint survival, per-stage rates)
                                     |                                         |
                                     +--------------------+--------------------+
                                                          v
                  Mitigation: baseline | PT/PRE | TART-style static | M1 dynamic ledger | M2 re-anchor | M3 error localisation
                                                          |
                                                          v
                                  Accuracy vs output-quality trade-off
```
 
---
 
*End of document. Prepared 28 Sep 2026 from the full project conversation and a fresh re-read of all 22 reference PDFs. Updated 28 Sep 2026 (same day) following novelty re-check #2 (Section 15.7), a compute-environment decision (Section 15.8), Phase 1 work (Section 15.9), and the model-access decision: open-source models via vLLM as the primary setup, APIs optional, the first capability gate run, and the late-binding redesign built in response (Sections 15.10, 15.11).*