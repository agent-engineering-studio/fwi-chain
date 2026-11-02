# FAQ

### What is the FWI, in one sentence?

A number, computed every day from noon weather, that estimates how intense a
wildfire would be if one started. It is the core output of the Canadian Forest
Fire Weather Index System, used by fire agencies worldwide and by EFFIS for Europe.

### Is this an official implementation?

No. It is an independent transcription of Van Wagner (1987), verified against
the reference day of the `cffdrs` R package to 1e-9. See [Validation](validation.md).

### How does it compare with `cffdrs` and `xclim`?

| | fwi-chain | cffdrs | xclim |
|---|---|---|---|
| Language | Python | R | Python |
| Dependencies | none | R + packages | NumPy, xarray, … |
| Unit of work | one location, one day | data frames | gridded arrays |
| State between days | explicit value you persist | inside the data frame | inside the time dimension |
| Best for | services, databases, streams, teaching | research in R | climate grids, NetCDF |

They answer the same equations. Pick the one that fits your pipeline.

### Why should I persist the state? Can't I just start from 85 / 6 / 15 every day?

No. DMC and DC remember weeks of weather. Restarting throws that memory away and
underestimates danger. With the synthetic season in the docs, a 1 July restart
underestimates the FWI by up to 48 points for weeks.
See [How the FWI works](how-fwi-works.md#why-it-is-a-chain).

### When does the season start?

Traditionally the chain starts three days after snowmelt, or when noon
temperatures have stayed above about 12 °C for three days in climates without snow.
It starts from the standard codes, or from an overwintered DC if you track one.
Many Mediterranean services simply run the chain all year round.

### Can I use daily maximum temperature and minimum humidity?

You can, but the system was calibrated on noon values. Daily extremes produce
systematically higher, uncalibrated numbers. A forecast or reanalysis valid at
local noon is the right input.

### Does it work in the southern hemisphere / the tropics / the Arctic?

The equations do. The **day-length tables** must match your latitude:
`STANDARD_PARAMS` is for 46°N. Pass your own `FwiParams`, as in
[example 05](../examples/05_southern_hemisphere.py).

### Does it compute danger classes?

Deliberately not. Classes are a regional policy choice. Example 02 and the
[cookbook](cookbook.md#danger-classes) show the EFFIS classes in five lines.

### Is it fast enough for a whole country?

One call takes a few microseconds. A full 214-day season for 1,000 locations
takes about a second and a half on one core, and locations parallelise trivially.
For multi-gigabyte climate grids, a vectorised library (xclim) is the better tool.

### Can I use it commercially?

Yes. It is Apache-2.0.

### Where did it come from?

It was extracted from [Limen](https://github.com/agent-engineering-studio/limen), where
it computes wildfire danger for every ~9 km weather node in Italy.

### How can I help?

See [CONTRIBUTING.md](../CONTRIBUTING.md). Reference vectors, latitude tables,
docs and translations are especially welcome.
