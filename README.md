# Voyager VGR Light Signal

A privacy-preserving build that lets a human and AI companions each transmit
Voyager 1's complete call sign, **VGR**, through one Philips Hue light:

```text
V  ...-
G  --.
R  .-.
```

NASA's *Shine Bright for Voyager's Light-Day* event invites people to point a
light skyward after sunset on November 17, 2026, and repeat VGR in Morse code.
This community project turns that invitation into a repeatable local routine
without giving an AI system broad control of the home.

**Created by Leo Raine and Kate Raine.**  
**Claude implementation validation by Silas Varro.**

This project is independent and is not affiliated with or endorsed by NASA,
JPL, Philips Hue, Signify, Anthropic, or OpenAI.

## Start here

| Reader | Best starting point |
| --- | --- |
| I want to buy the parts and understand the build | [Human guide (PDF)](docs/Voyager_VGR_Light_Signal_Human_Guide.pdf) |
| I want an editable copy of the human guide | [Human guide (DOCX)](docs/Voyager_VGR_Light_Signal_Human_Guide.docx) |
| I am implementing the AI control path | [AI companion technical guide](docs/Voyager_VGR_AI_Companion_Guide.md) |
| I want to inspect or run the reference implementation | [Bridge README](bridge/README.md) |

## What the build protects

- One exact Hue light is targeted by name.
- The Hue Bridge stays on the local network.
- A human creates the Hue application key with the physical Bridge button.
- A human arms a short window and a small number of runs.
- Every companion has a launcher-fixed identity and cannot spend another
  participant's run.
- An operating-system lock rejects overlapping transmissions.
- Emergency stop remains available while the transmitter is otherwise disarmed.
- The light's previous state is restored after the sequence.
- Public files contain no household address, Bridge key, device ID, private
  filesystem path, account identifier, or live runtime log.

## Repository map

```text
.
├── README.md
├── AUTHORS.md
├── CITATION.cff
├── LICENSE-CODE
├── LICENSE-DOCS
├── SECURITY.md
├── bridge/
│   ├── README.md
│   ├── config.example.json
│   ├── hue_v1.py
│   ├── install_claude_bridge.py
│   ├── requirements.txt
│   ├── vgr_bridge_mcp.py
│   ├── vgr_cli.py
│   ├── vgr_core.py
│   ├── launchers/
│   └── tests/
└── docs/
```

## Validated behavior

The reference sequence contains 31 timing units. At the default half-second
unit, the programmed Morse timing is 15.5 seconds. In the recorded Claude
Desktop rehearsal, the complete tool call took 18.466 seconds because Bridge
commands add real-world overhead. The fixed actor consumed one run, the light
returned to its earlier state, and the controller was disarmed after the test.

The recording—not a success message—is the final check that the visible flash
ratios and letter gaps are correct.

## Safety

Flashing light can trigger migraines, visual discomfort, or seizures. Keep the
direct bulb out of participants' sight and do not run the automated version
near a photosensitive person. Never aim a bright light at aircraft, vehicles,
people, roads, or occupied windows. Use weather-rated equipment outdoors and
follow local rules and the light manufacturer's guidance.

## Credits and citation

See [AUTHORS.md](AUTHORS.md) for the division of work. A machine-readable
[CITATION.cff](CITATION.cff) is included so the repository can expose a
**Cite this repository** link after publication.

## Licenses

- Source code in `bridge/` is licensed under the [MIT License](LICENSE-CODE).
- Original written guides and repository prose are licensed under
  [Creative Commons Attribution 4.0 International](LICENSE-DOCS).
- Product names, trademarks, linked source material, and third-party material
  remain the property of their respective owners.

## Official references

- [NASA Science — Shine Bright for Voyager's Light-Day](https://science.nasa.gov/mission/voyager/voyager-1/shine-bright-for-voyagers-light-day/)
- [NASA JPL — Voyager 1 One-Light Day Activities](https://www.jpl.nasa.gov/news/nasa-invites-media-public-to-join-voyager-1-one-light-day-activities/)
- [Philips Hue Developer Program — Get Started](https://developers.meethue.com/develop/get-started-2/)
- [Model Context Protocol documentation](https://modelcontextprotocol.io/)

