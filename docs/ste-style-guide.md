# The writing standard: ASD-STE100 Simplified Technical English

Use these rules for every README and for `docs/ste-style-guide.md` in each repository. Copy this file
into the repository as `docs/ste-style-guide.md` and add a **project vocabulary** section (Section 3)
with the technical names and technical verbs of that project.

## 1. The writing rules

### Words

1. Use one word for one meaning, and one meaning for one word. Do not use synonyms for variety.
2. Use a word only as one part of speech. For example, `test` is a noun or a verb, `check` is a verb.
3. Do not use phrasal verbs (`set up`, `carry out`, `find out`, `pick up`, `look up`, `come up with`).
   Use one verb: `prepare`, `do`, `find`, `get`, `make`.
4. Do not use an `-ing` form as a noun or an adjective (`the running job`, `after indexing`).
   Exception: a technical name, a file name, a command or a status value.
5. Do not use contractions (`don't`, `it's`, `can't`). Do not use slang or idioms
   (`out of the box`, `under the hood`, `at a glance`, `gotcha`, `bells and whistles`).
6. Do not use `and/or`. Write `A, B or both`.
7. Do not use `should`, `could`, `would` or `may` for instructions. Use `must` for a rule, the
   imperative for a step and `can` for a possibility.
8. Keep the articles `a`, `an` and `the` in sentences.
9. Do not make a noun cluster of more than three words. A technical name is one word.

### Sentences

1. A procedural sentence (an instruction) has a maximum of **20 words**.
2. A descriptive sentence has a maximum of **25 words**.
3. Write one instruction in one sentence.
4. Use the imperative for an instruction: `Run the tests.` Not `The tests should be run.`
5. Use the active voice. Use the passive voice only when the agent of the action is not important.
6. Use only the simple present, the simple past and the simple future.
7. Put a condition before the instruction: `If the index is stale, build it again.`
8. Do not use semicolons in sentences. Write two sentences.

### Paragraphs, notes and warnings

1. A paragraph has one topic and a maximum of **6 sentences**. Start with the topic sentence.
2. A warning or a caution starts with a clear command. Then it gives the reason.
3. A note gives information. It does not give an instruction.
4. Use a vertical list for a sequence or a set of conditions. Each item of a numbered procedure is one step.

### Tables, headings and diagrams

1. A table cell can be a short phrase. If a cell has a sentence, the sentence obeys the rules.
2. A heading is a noun phrase (`The cost model`) or an imperative (`Run the demo`).
   Do not start a heading with an `-ing` form.
3. A diagram label is a short phrase. Use the same terms as the text.

### What STE does not change

Code, commands, file names, paths, field names, environment variables, status values, enum values,
product names and URLs stay exactly as they are. They are technical names. Put them in backticks.

## 2. General words to replace

| Do not use | Use |
|---|---|
| utilize, leverage | use |
| in order to | to |
| set up | prepare, install, configure |
| carry out, perform | do |
| make sure, ensure | make sure (allowed), or `check that` |
| a lot of, lots of | many, much |
| e.g., i.e. | for example, that is |
| should (instruction) | must (rule) / imperative (step) |
| might, may (possibility) | can |
| very, really, just, simply, easily | (delete) |
| seamless, robust, powerful, blazing | (delete or give a measured fact) |

## 3. Project vocabulary


This section gives the technical names and the technical verbs of ResumeForge AI. The README uses each term with only this meaning.

### 3.1 Technical names (nouns)

| Term | Meaning | Do not use |
|---|---|---|
| **JD** | The job description text that the user pastes, the `jd_text` field | posting, ad, vacancy text |
| **profile** | One row of the `profiles` table: contact data, skills, experience, education and certifications of one user | CV data, user record |
| **master resume** | The `raw_resume_text` and `master_resume_url` fields of the profile | base CV, original resume |
| **job** | One row of the `jobs` table: one JD with its keywords, first ATS score and gap JSON | application (except in "application log"), posting |
| **run** | One execution of the LangGraph graph for one JD, with the `run_id` as its LangGraph thread ID | session, job, workflow instance |
| **run state** | The `ResumeState` values of one run, stored by the checkpointer | context, memory |
| **node** | One step function of the LangGraph graph | agent (except in a file name), step |
| **interrupt node** | A node that has an `interrupt_before` pause: `show_ats`, `show_resume`, `cover_letter_ask`, `show_cover_letter` | breakpoint, pause node |
| **gate** | One user decision: Gate 1 `user_confirmed`, Gate 2 `is_confirmed`, Gate 3 `wants_cover_letter` | checkpoint (this word is for LangGraph), approval |
| **checkpointer** | The `AsyncPostgresSaver` that stores the run state in the Supabase database | saver, persistence layer |
| **ATS score** | A number from 0 to 100 that Claude Opus gives for the match of a profile or resume with a JD | match rate, fit score |
| **section score** | The ATS score of one resume section: summary, skills, experience, education, certifications | sub-score |
| **gap JSON** | The `ats_gap` object: missing keywords, matched keywords, experience gaps, section scores, rewrite hints | gap report, analysis |
| **rewrite hint** | One `{section, hint}` item of the gap JSON | tip, suggestion |
| **bullet** | One line of experience text in `experience_json` | point, line item |
| **resume** | The text document that the system makes for one job. A noun only | CV |
| **resume version** | One row of the `resumes` table for one job, with a `version` number | draft, iteration |
| **pass threshold** | `ats_pass_threshold`, 95 | target, cut-off |
| **retry** | One more pass of the resume writer and the ATS rescorer after a score below the pass threshold | loop, attempt (except for LLM calls) |
| **tool server** | One of the 5 in-process Python classes in `backend/mcp_servers/`, with a name such as `storage-mcp` | MCP server (the code does not use the MCP protocol), service |
| **tool** | One async method of a tool server | function, endpoint |
| **application log** | One row of the `application_logs` table | history entry, record |
| **circuit breaker** | The per-provider guard in `core/circuit_breaker.py`: `closed`, `open`, `half_open` | fuse, kill switch |
| **guardrail** | One validation function in `core/guardrails.py` | filter, check function |

### 3.2 Technical verbs

| Verb | Meaning |
|---|---|
| **analyze** | Extract the JD keywords and give the first ATS score and the gap JSON (`ats_analyzer`) |
| **rewrite** | Change the bullets with GPT-4o for the target role (`rewrite_bullets`) |
| **assemble** | Make the full resume text with Claude Sonnet from the profile and the rewritten bullets (`assemble_resume`) |
| **rescore** | Give a new ATS score for an assembled resume (`ats_rescorer`) |
| **pause** | Stop a run before an interrupt node |
| **continue** | Start a paused run again with `POST /api/graph/resume/{run_id}`. Do not use "resume" as a verb |
| **poll** | Read the run status every 2 seconds with `GET /api/graph/status/{run_id}` |
| **confirm** | Set `is_confirmed` on a resume version |
| **render** | Make a PDF from an HTML template with WeasyPrint |
| **log** | Write one application log row (`append_log`) |
