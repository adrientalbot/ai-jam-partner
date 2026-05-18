# MVP

The MVP is a MIDI-first call-and-response prototype for the human / robot / AI music project.

## Goal

Take a MIDI file, analyze a small set of musical features, and generate a reactive MIDI response that feels structurally intentional.

## MVP Scope

- MIDI input and output only
- rule-based response logic
- one-bar-ish latency
- no real-time audio analysis
- no robotics
- no custom model training

## Core Inputs

- tempo
- density
- register
- phrase length
- short motif / contour

## Core Outputs

- response MIDI file
- response mode such as `repeat`, `fragment`, `sequence`, or `contrast`
- enough musical structure for a musician to evaluate quickly

## Deployment Target

- frontend on `Vercel`
- backend on `Render`
- shared MIDI logic in Python

## Success Criteria

- the system can load a MIDI file
- it produces a clear response
- the response is not just random notes
- the result is easy to test and iterate on with a musician
