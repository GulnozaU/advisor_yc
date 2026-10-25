# Advisor on Call: Call Screen Module for the Team Pipeline

This is a voice call screen that founders open to hear their advisor speak first about what matters right now. It takes a ready-made briefing from the team's pipeline (Gmail and Calendar, ranking, drafts), talks it through, takes in live updates during the call, and puts drafted replies on screen with one-click send.

## Who it's for
- **Early-stage founders** on the call, who want the one thing to do next spoken to them, not a dashboard.
- **The teammates building the pipeline** (Composio integrations, scoring layer, drafts). They hand this module a briefing and get actions back, without touching voice code.

## Core features and experience
1. **Briefing-driven call.** The pipeline sends a briefing: founder name, ranked priorities with short reasons, and any drafted replies. It gets back a call link. Opening the link and pressing Start call makes the advisor open with the top priority, for example: "You promised Priya the deck today, and your Beta call is in two hours."
2. **Advisor speaks first, from real context.** The briefing goes to the ElevenLabs agent when the session starts. The opening line and the priority list come from the briefing, not from generic tips.
3. **Push back and it re-plans.** The founder can interrupt and object out loud ("Priya can wait, the investor email is more urgent"). The advisor reorders on the spot, using only what the briefing contains.
4. **Live interruptions.** While a call is running, the pipeline can push an update such as a competitor pricing change. The advisor brings it up right away, and an update banner shows briefly on screen.
5. **Draft cards with one-click send.** When the advisor talks about a reply, a card appears under the character with the recipient, subject and body. The card has two buttons:
   - **Send**, which passes the draft back to the team's pipeline to send.
   - **Open in Gmail**, which opens a pre-filled compose window. If no send address is configured, this is the only option.
6. **Demo mode.** An editable sample briefing (a fictional founder with three ranked items, one draft and one scripted competitor update) lets the 3-minute demo run end to end before the pipeline is connected.
7. **Fully built here, ready to drop in.** All the Phase 1 code is finished and tested in this project, so teammates don't spend anything rebuilding it. They pull the finished folder from GitHub. The only work on their side is pointing their pipeline at the briefing and update addresses.
8. **Handoff guide.** A short guide in the project explains to teammates and their Emergent agent:
   - the briefing format
   - how to create a call
   - how to push live updates
   - how Send gets handed back
   - the ready-to-paste ElevenLabs agent prompt and first message

What stays as already built: the orange call screen, the Rive character with its talking mouth, the Start/End call button, status text, the secure voice token and the health check.

## User flow
1. The team's pipeline builds a briefing and sends it to this module. It gets back a call link.
2. The founder opens the link and sees their name and "3 priorities ready". They press Start call and allow the microphone.
3. The advisor opens with the top priority and why it can't wait.
4. The founder pushes back. The advisor re-plans out loud.
5. A competitor change arrives from the pipeline. The advisor interrupts with it, and a banner appears.
6. The advisor brings up the drafted reply and a draft card appears. The founder taps Send, or Open in Gmail, and the card shows "Sent" or "Opened".
7. The founder ends the call. The screen shows a short "Done this call" list of drafts sent.

## UI/UX feel
The current look carries on: calm, minimal and warm off-white, with the orange palette and the orange character in the circle. New elements are added quietly:
- a small priorities count above the button
- draft cards that slide up beneath the character
- a slim orange update banner for live interruptions

Nothing crowds the call. The voice leads and the screen supports it.

## Implementation phases
**Phase 1: MVP (built now)**
- Briefing intake from the pipeline, returning a call link per briefing
- The advisor opens with that briefing's priorities and can re-plan when challenged
- Live updates pushed during a call
- Draft cards with Send (handed to the pipeline) and Open in Gmail
- Demo mode with an editable sample briefing
- The handoff guide and agent prompt
- All of it built and tested here, then saved to GitHub as finished code that teammates pull in as-is

**Phase 2: Joined to the team pipeline**
- Founder sign-in and per-founder briefings, coming from the team's real Composio Gmail and Calendar data and the scoring layer
- Call outcomes (what was deferred, what was sent, what the founder objected to) sent back to the pipeline so the next ranking learns from them
- Briefings stored permanently

**Phase 3: Beyond the browser**
- Zoom bot via Recall, with this web call kept as the fallback
- Waitlist signup for founders who commit to connecting their inbox
- A paid plan for the first paying user

## Assumptions
- **What this module covers:** this piece is only the call experience. Gmail and Calendar access, ranking, competitor watching and writing drafts stay with the teammates' pipeline. Because of that, the questions on draft delivery, whose inbox and which AI model are settled like this:
  - **Draft delivery:** both Send (handed to the pipeline) and Open in Gmail, so it works whether or not the pipeline has send access.
  - **Whose inbox:** whichever founder the pipeline creates the briefing for. There is no sign-in in this module for Phase 1.
  - **AI model:** the advisor's voice and reasoning run on the model chosen inside the ElevenLabs agent settings. This module adds no other AI model, and the labelling model stays the teammates' choice.
- **Locked briefings:** briefing intake and live updates are protected by a shared secret between the pipeline and this module, because briefings contain inbox content.
- **Temporary briefings:** in Phase 1, briefings are kept only while the server is running and expire after 24 hours.
- **Agent settings to change:** the ElevenLabs agent's prompt and first message must be updated with the provided text so the briefing can be filled in. This is done once, in the ElevenLabs dashboard.
- **Getting it to teammates:** all the code is built in this project, on your credits. You save it to GitHub. Teammates either clone it directly, which costs no Emergent credits, or import the finished repo into their Emergent project and only connect their pipeline to it. Nothing gets rebuilt on their side.
- **Folder to copy:** the module stays in its own self-contained folder (advisor-on-call), so it can be copied into their project without clashing with their code.
- **Sample data:** all demo data is fictional and clearly labelled as a sample.
