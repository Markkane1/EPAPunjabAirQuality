# Punjab Air — map preview plan

This folder is a throwaway mock. It does not change the application. Open `index.html` through a local static server (`atlas.js` is loaded beside it).

The preview is here so we can agree the feel before anything in `src/` moves.

## What is wrong with the current screen

The system already has the hard parts: 79 stations, 41 districts, nine pollutants, wind, airports, fires, and the border. The current screen puts those streams on stage at once. Matrices, guard rails, and instrument chrome compete with the map. A person cannot see the air.

IQAir’s map is the opposite shape. The map is the page. Color is the sentence. One card holds the place you picked. Layers are a few pills. Time is a thin control. That is the interaction to take. Their world map, shop, and brand are not.

## The frame

The opening view is a neighborhood, not the globe and not Punjab alone.

- Pakistan is the subject, with room past its border.
- India is drawn whole. The northeast, the south, and the islands stay inside the opening camera. Nothing slices the India polygon.
- Afghanistan, Nepal, Bhutan, Bangladesh, Sri Lanka, and Tajikistan sit in the same frame.
- Eastern Iran, the Karakoram edge of China, a strip of Myanmar, and the edge of Turkmenistan are visible because they touch this neighborhood. The camera does not fly out to Tehran or Shanghai. Fitting all of China would shrink Pakistan to a corner, which is the world-map problem again.
- You can zoom and drag inside this frame. You cannot pan out to Europe or Africa.
- Wind, smoke, and the air color cross political borders. India is inside the flow, not a wall.

“Neighborhood” returns to that frame. “The plains” eases into the winter basin from Lahore across the border toward Delhi. Clicking a place eases the camera there. Zooming is navigation. It does not crop a country out of the data.

## The screen

One map, full bleed. Sea is a cool monsoon blue. Land is warm dust, with Pakistan a shade lighter so it reads as home. Country names are set in italic Fraunces and fade once you come in close. District lines appear as you approach.

The left card is glass. The place name is italic Fraunces. The number is Fraunces, upright and large, with a vertical pool of the AQI color beside it. The category and one plain sentence sit under it. Nine pollutant chips recolor the map. The bars are the other eight pollutants for an EPA place. A sparkline is the 72-hour episode, with the playhead in it.

Under that, Punjab districts ranked for the hour, then six cross-border cities. Search jumps to a district, a station, or one of those cities.

On the right, six pills: Stations, Air, Wind, Fires, Border, Airports. Wind and the air field are on when the page opens. The border line is always drawn, thin and red-brown. The Border pill adds moving chevrons along the Punjab stretch of that line. Fires and airports stay off until asked.

The bottom holds the PEPC-style legend and a 72-hour scrubber. Play walks the episode. The map color eases between hours.

Dots: filled for EPA sites, ringed for the Indian anchors. Closer in, the dots become the 79 stations. Farther out, they are districts plus the anchors, so Lahore does not turn into a pile of labels.

## Type and motion

Fraunces carries the name, the number, the country labels, and the one sentence. Outfit carries everything you operate. The number does not use a monospace instrument face.

The camera eases for about 900ms. Pollutant changes blend the field. The color pool takes the same time. Wind is short streaks, advected across land, and they die over the sea so the water stays quiet. Reduced-motion settings stop the streaks and the transitions.

Map colors sit next to the PEPC bands (good through hazardous). They are shifted just enough to stay visible on dust-colored land. Pure `#FFFF00` disappears on this paper. The statutory hex can return in the product if the land under it is cooler.

## What is real, and what is only for the preview

Real, from the local baseline (1–9 Nov 2026, last 72 hours):

- District shapes, station coordinates, and the nine pollutant series
- The international border line
- Airport positions and their METAR wind components

Placed, and labeled as such in “Where this comes from”:

- Amritsar, Ludhiana, Chandigarh, Delhi, Jaipur, and Srinagar. Their numbers follow Lahore’s hour so the cross-border picture has a shape. They are not an IQAir feed.
- Fire marks in the plains. They show the layer. They are not a FIRMS pull.
- The wind streaks follow a field with an easterly push into Lahore and a slower drift elsewhere. The live build should advect the ECMWF u/v grid the workstation already has.

Chiniot and Lodhran have no matching station series in this extract, so they have outlines and no number.

## How this would later enter the repo

Do this only after the preview is accepted. Leave the pipelines alone.

1. Keep the ingestion, the AQI math, and the wind grid. The mock replaces the shell, not the evidence.
2. Make the map the viewport. Retire the five-zone console as the default. Move flux, the wind rose, QC flags, and the guard rails behind the place card, one level down.
3. Drive the same camera: neighborhood frame, plains, place. India stays whole in the data even when the camera is on Lahore.
4. Draw wind as streaks through the ECMWF grid, across Pakistan and the neighboring countries, not as rings or arrowheads.
5. Feed Indian cities from the IQAir stream when that stream is actually loaded. Until then, do not present the anchor numbers as measurements.
6. Feed fires from FIRMS the same way.
7. Keep the PEPC names. Tune the light-map hex only where a band fails contrast, and record the pair.
8. The scrubber should use the same hours the API already serves.

The React workstation can host this. The first implementation pass is a new view beside the current one, switched by a route, so the old console remains until this one is doing the real job.

## Out of scope for the mock

No accounts, no shop, no world globe, no 3D earth, no rewritten API, and no change to the files under `src/`.
