# MVP

The MVP is a MIDI-first call-and-response prototype for the We Are All John Henry project.

## Goal

Take a MIDI file, analyze a small set of musical features, and generate a reactive MIDI response that feels structurally intentional.

## MVP Scope

- MIDI input and output only
- rule-based response logic
- one-bar-ish latency
- no real-time audio analysis
- no robotics in the core algorithm yet
- no custom model training

## Core Inputs

- tempo
- density
- register
- phrase length
- short motif / contour
- ensemble-specific instrumentation context

## Core Outputs

- response MIDI file
- response mode such as `repeat`, `fragment`, `sequence`, or `contrast`
- enough musical structure for a musician to evaluate quickly
- enough structure to support a performance arc moving between control, loss of control, and machine takeover

## Ensemble Context

- four professional musicians: cello, trombone, drum set, percussion
- four music robots with the same instrumentation
- repetitive, physically demanding material that can be interpreted by both human and robotic players

## Deployment Target

- frontend on `Vercel`
- backend on `Render`
- shared MIDI logic in Python

## Success Criteria

- the system can load a MIDI file
- it produces a clear response
- the response is not just random notes
- the result is easy to test and iterate on with a musician
