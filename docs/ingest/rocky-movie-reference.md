# Ingest — Rocky (Project Hail Mary 2026 film) movement / voice / personality

Sourced from BTS interviews (James Ortiz, Neal Scanlan, sound designers Erik
Aadahl & Ethan Van der Ryn) + the novel. Drives the Rocky reference gait, chord
voice, and future persona model. NUMBERS below marked [INF] are our engineering
inference from qualitative BTS notes — tune, not canon.

## Movement / gait (feeds rocky_reference.py)
- **Syncopated, NOT synchronized.** Scanlan: "one's moving slightly different than
  the other" + unpredictable pauses/foot-taps. Clean crab/spider gaits FAILED
  (read as "scary"). → we perturb the even 72° offsets (PHASE_DESYNC) + per-leg
  lift variation.
- **Never perfectly still.** Ortiz: "when you lift one leg, the whole body rocks
  over to the side… never a way to be perfectly still", "electric and crackly".
  "If Rocky stops moving, the character stops working." → body_roll() couples roll
  to the lifting leg; idle must keep micro-motion.
- **Deliberate tempo** ~1.2–2.0 s/step [INF], phrased in irregular "breaths" with
  ±15–25% jitter [INF]; occasional 0.5–1.5 s pauses + taps.
- **Duty ~0.7–0.8** (usually 4/5 planted); moderate-HIGH lift (reads deliberate).
- **Radial / omnidirectional** — no front, senses by sonar; "turning" = re-index
  which legs lead, not a body yaw. Legs-as-hands: stand on 3–4, free 1–2 to reach.
- Reference points Ortiz named: birds (sharp, processing), Madeline Kahn / David
  Hyde Pierce cadence (twitchy, precise, reactive — NOT smooth).

## Voice / sound (feeds rocky/audio — chord voice)
- **Real musical chords, up to 5 simultaneous notes**, human hearing range;
  meaning in RELATIVE pitch/contour (transpose-invariant), note-length distinctions.
- Film used **organic sources, no synth**: ocarina (primary), water-jug (bass),
  didgeridoo, humpback whale (lowest), birdsong whippoorwill/solitaire (highs),
  contra-alto clarinet (agitated). Range: whale → piccolo.
- **Emotion → sound:** agitated = pitch UP + reedier timbre; grave/sincere = pitch
  DOWN. "Question?" = fast rising cluck. ~250-word lexicon, each a fixed chord.
- IMPLICATION for our synth: keep chords (we have 1–4; extend toward 5), add
  organic-ish timbres (breathy + noise), map arousal→pitch/brightness, a rising
  interrogative gesture. Our A-minor-pentatonic codec is a fine base; add contour +
  organic timbre + emotion→pitch.

## Personality / mannerisms (feeds future persona model)
- Earnest, logical, loyal engineer; childlike wonder; deadpan warmth; anxious
  undertone. Catchphrases: **"Question?"**, **"Amaze amaze amaze"** (triple-repeat
  on success), **"Good good good"**, **"Fist my bump"** (literal idiom scrambles;
  can't tell thumbs up/down).
- Emotes with NO face → all body + sound: arousal (fast/sharp/jittery + pitch up)
  vs solemnity (slow/low/still-not-frozen). Model as arousal×valence driving gait
  params + voice params + a gesture library (reach/tap/fist-bump/forearm-play).

## Operator behavioral spec (authoritative — synthesized into code)
Implemented in `rocky/persona.py` + `rocky_reference.py` poses:
- **Anatomy:** 5 IDENTICAL limbs, each 3 joints (body-proximal / elbow-knee / wrist)
  ending in a 3-pronged hand-foot; any limb is arm or leg. (Our build actuates
  grips on 2 legs for cost; all 5 feet get the 3-prong shape — CAD TODO.)
- **Omnidirectional, NO chassis yaw:** directional movement = shift the kinetic
  vector to a different set of limbs, never rotate the body. → RL: command is a 2D
  velocity vector on the 0.35 m/s disk, PENALIZE base yaw-rate, no heading reward.
- **Gait:** arachnid alternating/quad-support wave (e.g. 1-3-5 step while 2-4
  support, or a syncopated cascade); fast & agile; can climb/clamp with fingers.
- **Dormant rock-dome:** withdraw all 5 limbs tightly up under the carapace →
  flat solid dome. → `rocky_reference.rest_pose()`.
- **Dialogue syntax (MANDATORY tags):** append ", question!"/", question?" for
  questions, ", statement!" for assertions; drop articles/copula; literal
  descriptors ("humans"→"leaky space blobs"); "No understand word" on unknown
  syntax. → `persona.say(text, tag)`.
- **Emotion = body+sound (no face):** excitement/agree = rapid 3-prong TAPPING +
  carapace SWAY; distress/fear = RETRACT limbs + rapid carapace CHATTER (clicking
  stone); curious = hold still, TILT carapace toward subject + echolocation clicks;
  contact = trace with one finger. → `persona.jitter/gait_mod/voice_params` +
  EMOTIONS states (excited/agree/curious/solemn/distress/dormant).
- **Voice:** native melodic chords/whale-song, in-film translated via a rugged,
  slightly clipped, low-fi TTS (Ortiz). → our chord voice + a mechanical TTS gloss;
  agitation→pitch up, grave→down.
- **Cultural markings (CAD TODO):** base-3 math scales/rulers etched into limbs +
  a carved marriage symbol (two interlocking circles) on one primary limb.

Sources: HollywoodReporter (Ortiz), GoldDerby (Scanlan), BlackGirlNerds, MovieWeb,
The Credits/MPA + Space.com (sound), LinguisticDiscovery (Eridian language),
WinterIsComing (catchphrases). Video (Scanlan): youtube.com/watch?v=J3V9e3uqplM.
Caveat: no numeric gait data exists (human puppeteers); [INF] numbers are ours.
