# Social media kit

Everything you need to share `fwi-chain`: images, ready-to-post texts, and
hashtags. Copy, adapt, and post. Thank you!

**Link:** https://github.com/agent-engineering-studio/fwi-chain
**Install:** `pip install fwi-chain`

## Images

| Image | Use it for | File |
|---|---|---|
| Social card, 1280 × 640 | GitHub social preview, link previews, X / LinkedIn / Mastodon | [`images/social-preview.png`](images/social-preview.png) |
| The chain diagram | explaining what the FWI is | [`images/fwi-chain-diagram.svg`](images/fwi-chain-diagram.svg) |
| A fire season | the "wow" chart | [`images/fire-season.svg`](images/fire-season.svg) |
| Three memories | the science hook | [`images/moisture-codes.svg`](images/moisture-codes.svg) |
| Storm recovery | the "did you know" hook | [`images/memory.svg`](images/memory.svg) |
| Cold restart | the engineering hook | [`images/restart.svg`](images/restart.svg) |

> Most platforms do not accept SVG uploads. Export a PNG by opening the SVG in a
> browser and taking a screenshot, or run
> `uv run --with cairosvg python -c "import cairosvg; cairosvg.svg2png(url='docs/images/fire-season.svg', write_to='fire-season.png', output_width=2000)"`.

**Set the GitHub social preview once:** repository → *Settings* → *General* →
*Social preview* → upload `docs/images/social-preview.png`.

## LinkedIn

> 🔥 **Wildfire danger, in about 300 lines of pure Python.**
>
> We just open-sourced **fwi-chain**: the Canadian Forest Fire Weather Index (FWI), the index fire services and the European EFFIS publish every day, as small, typed, dependency-free Python functions.
>
> Four noon readings (temperature, humidity, wind, rain) → six numbers that say how easily a fire would start, how fast it would spread, and how hard it would be to fight.
>
> What makes it different:
> ✅ Zero dependencies: it fits in a database job, a stream processor, a serverless function
> ✅ Verified, not just tested: all six outputs match the published reference day to 1e-9
> ✅ The "memory" of the forest floor (weeks of drought) is an explicit state you persist, not hidden in an array
> ✅ Every line tied to an equation number in Van Wagner (1987)
>
> It already runs the wildfire danger chain for every ~9 km weather node in Italy.
>
> We're looking for contributors: fire scientists, meteorologists, Python developers, technical writers. There are good first issues for everyone.
>
> 👉 https://github.com/agent-engineering-studio/fwi-chain
>
> #wildfire #opensource #python #climate #firescience #meteorology #EFFIS

*(attach `social-preview.png` or `fire-season.png`)*

## X / Bluesky / Mastodon

**Launch (≤ 280 chars)**

> 🔥 fwi-chain: the Canadian Fire Weather Index in pure Python.
> Zero deps · fully typed · verified to 1e-9 against the reference day · Apache-2.0
>
> pip install fwi-chain
> https://github.com/agent-engineering-studio/fwi-chain
> #Python #wildfire #opensource

**Science hook** (attach `memory.svg` as PNG)

> After a 40 mm storm in July:
> 🌾 fine fuels are bone-dry again in 2 days
> 🍂 the duff layer takes a week
> 🪵 deep drought takes 17+ days
>
> That memory is why fire danger is a *chain*, not a formula. Explained, with code: https://github.com/agent-engineering-studio/fwi-chain/blob/main/docs/how-fwi-works.md

**Engineering hook** (attach `restart.svg` as PNG)

> Bug you won't see in a unit test: restart your fire-danger model mid-season from default values and it underestimates danger for weeks.
>
> fwi-chain makes the state explicit, so you can't forget to persist it. 🧵👇
> https://github.com/agent-engineering-studio/fwi-chain

**Thread (5 posts)**

1. 🔥 How do fire services decide that today is "extreme" fire danger? Most use the Canadian Fire Weather Index. We open-sourced a tiny, verified Python implementation. A thread on how it works 🧵
2. It needs only 4 noon readings: temperature, humidity, wind, and 24 h rain. From them it computes 3 moisture codes, one for each layer of the forest floor, from surface litter to deep soil. *(diagram)*
3. Each layer has a different memory: ~16 hours, ~12 days, ~52 days. So today's danger depends on the whole season, and that's why it's a *chain*. *(moisture-codes)*
4. Forget that memory (restart mid-season) and you underestimate danger for weeks. fwi-chain hands you the state as a plain value: store it in SQL, a file, a cache. *(restart)*
5. Zero deps, mypy --strict, verified to 1e-9, Apache-2.0. Contributors welcome: reference data, latitude tables, docs, translations. ⭐ https://github.com/agent-engineering-studio/fwi-chain

## Reddit (r/Python, r/datascience, r/gis, r/meteorology)

**Title:** I open-sourced a zero-dependency, verified implementation of the Canadian Fire Weather Index

**Body:**

> The FWI is the fire danger index used across Canada, by EFFIS for Europe, and by many other agencies. I extracted the implementation we use in production (Italy, ~9 km grid) into a standalone package:
>
> - pure functions, no NumPy, no I/O, about 300 lines, `mypy --strict`
> - verified against the cffdrs reference day to 1e-9, plus tests for every rain branch and for physical bounds
> - the recursive state (the "memory" of the forest floor) is an explicit dataclass you persist yourself
>
> For gridded climate data xclim is still the better tool. This one is for services, databases and streams.
>
> Docs explain the science in plain words, with charts generated by the library. Feedback and contributions very welcome!
>
> https://github.com/agent-engineering-studio/fwi-chain

## Hacker News

**Title:** Show HN: fwi-chain – the Canadian Fire Weather Index in pure, verified Python

## Hashtags

`#wildfire` `#firescience` `#FWI` `#Python` `#opensource` `#climate` `#meteorology`
`#EFFIS` `#GIS` `#climatechange` `#forestfire` `#datascience`

## Suggested GitHub topics

Add them under *About* → ⚙️ on the repository page:

```
fire-weather-index  wildfire  fwi  python  meteorology  climate  fire-danger
forest-fire  cffdrs  van-wagner  zero-dependency  typed
```

## Key facts (for writing your own post)

- Implements Van Wagner (1987), *Forestry Technical Report 35*.
- 6 outputs: FFMC, DMC, DC, ISI, BUI, FWI.
- Python 3.12+, no runtime dependencies, Apache-2.0.
- About 300 lines of library code. Reference day matched to an absolute 1e-9.
- A few microseconds per location per day.
- Extracted from Limen, which runs it on every ~9 km node in Italy.
