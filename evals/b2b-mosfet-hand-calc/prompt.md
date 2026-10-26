---
tags: [openfoam-electronics-cooling]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

I've got two 100V MOSFETs back to back as a bidirectional battery switch, 50 A continuous through both. Datasheet says Rds(on) max 1.7 mOhm at 25C, roughly 1.7x at 125C, Rth j-c 0.4 K/W, D2PAK-7 size. They sit side by side on an IMS (60x50 mm, 100 um dielectric at 2.2 W/mK, 1.5 mm alu) with a 100 um thermal pad (3 W/mK) on a black anodised extrusion: 150 mm wide, 200 mm tall, 8 mm base, 12 vertical fins 2 mm thick and 40 mm high. No fan, ambient can reach 40 C. Will this run cool enough, and do I need a proper CFD run? Put the numbers in a file thermal-check.md.
