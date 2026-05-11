# MVP: Human / Robot / AI Music System

## Purpose

The MVP is a MIDI-based prototype for the human-robot-AI music project. It should listen to a musical input, analyze a small set of musical parameters, and generate a reactive MIDI response that feels structurally intentional rather than purely generative.

The first version is intentionally modest:

- no real-time audio analysis
- no trained custom model
- no robotics integration
- no live musician input required
- MIDI only

The goal is to create a convincing first interaction layer that can later be extended into a richer performance system.

## Core Idea

The system acts as a call-and-response partner.

It should:

- observe an input MIDI phrase or section
- extract useful musical features
- decide on a response strategy
- generate a new MIDI passage after a short latency buffer

The response should support the project’s broader artistic aim: tension, escalation, contrast, and repetition, inspired by minimalist and process-based composition.

## MVP Scope

### In scope

- MIDI file input
- basic feature extraction
- rule-based response generation
- output as a new MIDI file
- configurable latency of about one bar
- simple support for contrasting or repeating material
- enough structure to test with rehearsal MIDI or DAW-generated sketches

### Out of scope

- real-time microphone or audio transcription
- vision-based perception
- robotic performance control
- custom deep learning model training
- automatic orchestration of large ensemble textures
- full composition engine

## Input

The MVP takes a MIDI source as its primary input.

Useful signals to extract from the input:

- tempo
- note density
- phrase length
- register
- rhythmic activity
- simple harmonic context when available
- recent motif or phrase contour

If the input contains multiple instruments, the MVP can start by focusing on a single selected track.

## Output

The MVP produces a MIDI response that:

- starts after a configurable delay
- follows a chosen response strategy
- stays within a musically usable register
- can be written to disk as a new `.mid` file

The response may be:

- a repetition of source material
- a fragmented variation
- a transposed sequence
- a contrastive counter-line
- a denser or sparser answer depending on input state

## Response Logic

The first version should be rule-based.

Suggested response states:

- `repeat` - echo the incoming phrase
- `fragment` - break the phrase into smaller motivic pieces
- `sequence` - transpose a motif by small intervals
- `contrast` - answer with different register or density
- `escalate` - increase rhythmic or textural intensity

The system should not always choose the same reaction. It should map musical features to response behavior.

## Timing

The email thread suggests using a latency buffer of roughly one bar to give the system time to analyze and decide.

The MVP should therefore:

- detect the current musical state
- wait or schedule the response for the next structural boundary
- generate output aligned to bar-level timing

This makes the system feel deliberate rather than instantaneous and chaotic.

## Musical Principles

The system should reflect the project’s artistic framing:

- human and machine as interacting performers
- compositional rules before heavy ML
- repetition and gradual transformation
- tension through alignment and misalignment
- material that can grow from rehearsal data later

The first prototype should be musically legible even if it is simple.

## Success Criteria

The MVP is successful if it can:

- take a MIDI file as input
- analyze a small set of features reliably
- generate a response that is not random noise
- preserve enough musical shape to sound like a response
- run reproducibly for demo and debugging purposes
- serve as a base for later integration with scores, rehearsals, and robot control

## Technical Direction

Recommended implementation shape:

- pure Python core logic
- notebook or small CLI for demo purposes
- feature extraction helpers
- response policy layer
- MIDI rendering layer
- optional seed for deterministic generation

Deployment target for the MVP:

- frontend deployed on `Vercel`
- backend deployed on `Render`
- shared musical logic kept in the Python core so the web app stays thin

## Suggested Next Step After MVP

Once the MVP works, the next version can add:

- better phrase detection
- harmonic awareness
- more style-specific rules based on Daniel Brandt’s material
- rehearsal-data conditioning
- live-input support
- robot/actuator output

## Open Questions

- Which MIDI track should be treated as the “lead” input?
- Should the first response favor imitation or contrast?
- What is the preferred default latency: one bar or two bars?
- What degree of randomness is acceptable for a demo?
- Which compositional rules matter most for the first artistic proof of concept?
