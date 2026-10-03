# Roadmap and known gaps

Difficulty: **S** days of work, **M** about a week, **L** several weeks.

## Honest gaps today

| Gap | Impact |
|---|---|
| Fund holdings are samples, not real factsheets | overlap answers cannot cover a user's actual funds |
| Tip scanner understands English tips only | most scam forwards in Indian languages are not scanned |
| Prices are a frozen snapshot | not for live decisions |
| Only English and Hindi; Standalone Portfolio/Research pages are not fully Hindi | |
| Typed Hinglish needs the optional local model | offline it asks for clarification |
| TTS runs on CPU only | ~2 s to first English audio |
| Voice and Hindi speech recognition judged only on synthesized speech | needs human listening tests |

## Done recently

- **Scam recovery coach** (first-hour plan, clock, checklist, ready-to-send drafts, English and Hindi).

## Next features, by value

| Feature | Problem | Size | Interactivity |
|---|---|---|---|
| **Loan prepayment vs investing** | The common household decision | S | high (sliders) |
| **Scam photo checker** | Scams arrive as screenshots (fake SMS, UPI "collect" requests): OCR then the existing scanners | M | high |
| **Real fund data import** | CAS statement / AMC monthly holdings (Excel) + AMFI NAVs for true overlap and fees | L | high |
| **Old vs new tax regime** | Every salaried person asks yearly; needs maintained slabs and clear "as of" dates | M | high |
| **Insurance gap meter** | Term cover vs income | S | high |
| **Cooling-off before selling** | A short check-in, the replay and a 24 h pause when the market falls | S-M | medium |
| **Multi-goal planner** | School fees, wedding and house together, with inflation and SIP step-ups | M | high |
| **Where should Rs 1 lakh sit?** | FD, PPF, gold, index fund after tax and inflation, stated as arithmetic | S | high |
| **Elder mode** | Large text, voice-only, one big button for the people most at risk from scams | S-M | medium |
| **More Indian languages** (Marathi, Tamil, Bengali, Telugu) | Reach | L | n/a |
| **Installable web app / offline** | Phone-first, patchy data | M | n/a |

## Not feasible in this form

- **Live call protection**: a web page cannot listen to a phone call.
- **Family alerts** (notify a relative): needs a server and notifications, which conflicts with the local-only rule.

## Engineering backlog

- Move UI strings to a catalogue to make adding a language mechanical.
- Cache `/translate` results server-side across restarts.
- GPU TTS (onnxruntime-gpu + CUDA) for about a one-second gain.
- Replace the process-wide `session` with per-user sessions if ever hosted.
- Expand the blind routing sets and track the first-run score over time.
