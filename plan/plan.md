# Advisor on Call: Founder Dashboard with Sign-up and Login

A signed-in home for founders: create an account, set up a short founder profile, see and manage today's top priorities, and start a live voice call with the orange advisor from the dashboard. The advisor already knows that founder's priorities. The Gmail, Calendar, ranking and competitor pipeline stays with the teammates' build. This dashboard is the shell it plugs into.

## Who it's for
- **Early-stage founders** who sign up, keep a short list of what matters, and talk it through with the advisor.
- **The teammates building the pipeline**, who later feed real ranked priorities and drafts into this dashboard instead of rebuilding it.

## Core features and experience
1. **Sign up and log in.** Email and password, or Google, with password reset and email verification included. Log out from the user menu. Every page except the landing page needs sign-in, and so does the voice token, so strangers can't use up agent minutes.
2. **Landing page.** A calm intro to Advisor on Call, with Sign up and Log in buttons and the orange character.
3. **Onboarding.** One screen after the first sign-up, taking under a minute:
   - name and company
   - a one-line description
   - website
   - a goal, picked from Raise, First customers, Revenue, Ship or Hire

   This can be edited later in Settings.
4. **Dashboard (home).** Shows:
   - a greeting with today's date
   - a large "Start call" tile with the orange character
   - the **Top 5 priorities** list, where each card shows the type (send, meet, decide or learn), the action, who it's for, the reason, and a countdown to its deadline
   - a **Recent calls** strip
5. **Manage priorities by hand.** Until the pipeline is connected, founders can add a priority, edit it, drag it to reorder, mark it done, or dismiss it. Completed and dismissed items move to a "Done" tab. New accounts start with three clearly labelled sample priorities that can be deleted.
6. **Call page.** This is the existing orange call screen:
   - the Rive character with its talking mouth
   - Start/End call
   - the status line
   - a mute button and a call timer (both new)

   The top-5 list sits beside the character. The advisor opens with the founder's #1 priority and why it matters, using their name, goal and list.
7. **Call history.** Each call is saved with its date, length and which priorities were open at the time. It is shown on the dashboard and on a Calls page.
8. **Connections page.** Gmail and Google Calendar are shown honestly as "Coming with the team pipeline", with no fake connect buttons. This is where the teammates' connection flow will plug in.
9. **Settings.** Edit the founder profile and goal, and manage the account (email, password, delete account) through the user menu.

## User flow
1. A visitor lands on the landing page and clicks Sign up. They create an account with email or Google.
2. Onboarding asks for name, company, one-liner, website and goal, then opens the Dashboard.
3. The Dashboard shows three sample priorities. The founder edits them, adds their own, and reorders them.
4. They click Start call. The advisor greets them by name and opens with priority #1 and why.
5. The founder talks back or pushes back, then ends the call. The call appears in Recent calls.
6. They mark items done and the list moves up. They return tomorrow, log in, and pick up where they left off.

## UI/UX feel
This extends the current look: calm, minimal, a warm off-white background, the orange palette (#F97316, #EA580C, #FFEDD5 and #FED7AA) and the orange character.
- **Navigation:** a slim left sidebar with Dashboard, Calls, Connections and Settings.
- **Cards:** soft priority cards with orange countdown chips, and smooth slide and reorder motion when items are completed or reordered.
- **Sign-in screens:** match the same palette.
- **Phones:** everything works on a phone. The sidebar becomes a bottom bar.

## Implementation phases
**Phase 1: MVP (built now)**
- Sign up, log in (email + Google), log out, and protected pages and voice token
- Onboarding and founder profile
- Dashboard with a hand-managed top-5 priorities list (add, edit, reorder, done, dismiss), starting with sample items
- Call page using the orange character, with mute, a timer, and the priorities passed to the advisor so it opens with #1
- Call history
- Connections page with an honest "coming with the team pipeline" status
- Settings
- Saved to GitHub as finished code

**Phase 2: Plug in the team pipeline**
- The teammates' real Gmail and Calendar data, ranking and drafts replace the hand-managed list
- Draft cards with one-click Send
- Re-ranking when the founder pushes back on the call
- Live competitor interruptions

**Phase 3: Growth**
- Waitlist for founders who commit to connecting their inbox
- A paid plan for the first paying user
- Zoom bot via Recall, with this web call as the fallback

## Assumptions
- **Sign-in methods:** email + password and Google, through Emergent-managed sign-in. No sign-in code is built from scratch.
- **Rebuilt on the main project structure:** the dashboard runs on this workspace's standard structure (a React interface with a Python server), because Emergent-managed sign-in only supports that setup. The orange call screen, character and talking mouth carry over unchanged in look and behaviour. The standalone Express call-screen folder stays in the project as it is, as a separate copy.
- **No Claude or other AI model is added in this phase.** The advisor's voice and reasoning run on the model set in your ElevenLabs agent. Labelling, ranking and drafting stay with the teammates' pipeline.
- **No real Gmail or Calendar access** in this phase. Priorities are typed in by the founder or come from the sample items.
- **One-time agent setup:** the ElevenLabs agent needs one update, a provided prompt and first message pasted into its dashboard, so it can use the founder's name, goal and priorities. Until then, calls still work but open generically.
- **Separate accounts:** every founder sees only their own profile, priorities and calls. No admin role or team accounts.
- **Test accounts:** preview accounts and live accounts are separate. People sign up again on the published app.
- **What gets saved from calls:** only the date, length and open priorities. No audio and no transcript.
- **The team spec isn't being built here:** the Claude Code spec is used only to keep the founder profile fields (one-liner, website, goal chips) and the priority card fields consistent with it.
- **Security warning about your pasted keys:** the Claude Code prompt you pasted includes a real Supabase project address and partly visible keys. Treat any key that has been shared in chat as exposed, and rotate it in its provider's dashboard.
