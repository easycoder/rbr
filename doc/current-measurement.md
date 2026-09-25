# Current measurement

> For how this could be built — files, data path, module boundary — see [PROPOSAL-current-measurement.md](PROPOSAL-current-measurement.md).

The present RBR installations (there are only 2) read temperatures and control radiators but know nothing of the environment. I would like to position the product so as to offer particular advantages for all-electric installations, by monitoring current flow. I identify the following primary flows:

1. Power from and to the grid
2. Power from solar panels
3. Power to storage, e.g. battery, heat store or hot water cylinder
4. Power to and from electric vehicle(s)

The output of solar panels indicates the amount of energy arriving from the sun. Some rooms benefit from solar gain, which affects the way they heat and cool irrespective of the heating system, so there's an indirect but close link between power flow and heating system performance. It may be posible to estimate solar gain for each room by recording the power flow from the solar panels and by knowing which compass direction the room's windows face.

The other primary flows may not be related to heating performce but they offer the means to correlate consumption of electricity with solar input, tariff bands and electric battery storage/use. Such information helps when planning an entire system.

I'd like to start with my own system, which has a heat pump, solar panels and a phase-change heat store for hot water. I will need to buy some Zigbee current clamps; how many of these will I need?
