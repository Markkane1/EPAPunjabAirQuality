# Pollution corridors

Nothing in this document is built until you say so. No application code, no mock code.

This is the picture we will put on the map for pollution moving between Punjab districts and pollution moving in from India and the other sides. It is one ribbon. The border is a place that ribbon crosses.

The Copernicus product already mapped around Punjab is **CAMS**, the Copernicus Atmosphere Monitoring Service: global PM2.5 at 117 points around the province, combined with ECMWF wind. That is the outside concentration the ribbons start from. **CEMS** is a different Copernicus service (emergencies: floods, burned area). The fire pins already come from NASA FIRMS. This plan does not add a second fire layer.

---

## The choice, already made

Last time the only open choice was how many corridors to show on the plains view.

It is settled:

- At most **two** corridors on screen.
- A quiet hour shows **none**.
- You do not need to pick this. If you want a single path only, say so and the maximum becomes one.

Everything else below is the same rule applied inside the province and outside it.

---

## What you should see

The color wash stays the pollution. The short white dashes stay the air moving. A corridor is where that air is carrying a real load from one place into the next.

On the plains view the eye gets one or two pale threads, bent the way the wind bends, thicker where more PM2.5 is moving and thinner as they travel. One of them may cross the India line. The other, on some hours, comes out of Khyber Pakhtunkhwa or leaves toward Sindh. They are the same kind of mark.

Close in, a thread breaks into the short hops it is made of. Kasur into Lahore is a short thick piece. A hop the wind is not aimed at is missing.

Far out, over Pakistan and the neighbors, you may see only the strongest thread crossing into the basin, or nothing. Country names stay as they are. The thread does not get a label painted on it.

The place card says the sentence. The map does not.

Examples, for Lahore on an inflow hour:

- “Receiving from the east through Kasur.”
- “Across the border this hour: coming in.”

For a district the air is only passing:

- “Passing through toward Lahore.”

The long list of every allowed hop stays behind See details. It is the evidence. It is not the picture.

---

## One ribbon, two places it runs

### Between districts

A hop from district A to district B is allowed only when all of these are true for that hour, for a real mass concentration (PM2.5, and the other mass pollutants if that chip is on):

- The wind at the source is at least 0.5 m/s.
- B lies inside a 35° cone of the direction the wind is blowing toward.
- The centroids are at most 180 km apart.
- There is a positive concentration at the source.

The amount is concentration × wind speed × how squarely the wind points at the receiver × a decay that weakens with distance (e-folding length 100 km). AQI is never used. AQI is a health index, not a mass, so it cannot be carried.

Hops that line up in the same direction become one corridor. The path is not a straight line between centroids. A straight line would cross districts the air did not cross. The path follows the same smoothed ECMWF 10 m field as the white dashes, and it stays inside the districts that hop claims.

Width is the amount of mass on that hop. The thread narrows as it goes. That narrowing is the decay. It is not a second color scale. The thread is a light stroke on top of the wash, in the same family as the dashes, longer and fewer, so it reads as the load rather than as more wind.

At plains zoom only the strongest one or two chains are drawn. Zooming in may show the shorter hops that belong to the open place. Zooming out drops back to the chain, then to nothing if the chain is weak.

### Across the border, and the other sides

The outside end of a thread is a CAMS point, not an Indian city anchor.

What is already mapped:

- 117 points, about 25 km apart, around the whole boundary of Punjab, not only the India line.
- At each point, CAMS global PM2.5 and ECMWF 10 m wind.
- The sides those points belong to: Indian Punjab, Rajasthan, Jammu, Khyber Pakhtunkhwa, Islamabad, Azad Kashmir, Balochistan, Sindh.

A crossing is drawn only where the wind has a real component across that side and the CAMS concentration is positive. The thread starts just outside the line, at that CAMS point, crosses, and joins the district hop on the inside if one exists. Inflow is a little brighter. Outflow is the same thread, thinner, leaving the province. Wind parallel to the line draws nothing on that stretch.

The 39 marks along the India border stay available as the gate on that one side. They are not a parade of arrows. A mark appears only on a stretch where mass is crossing, sized by how much. The other sides use the same rule on their own CAMS points. Afghanistan, Iran, and China are in the map frame, but they are not a Punjab boundary side, so they do not grow a corridor unless a later CAMS point is actually on that frontier. This plan does not invent those points.

Indian city anchors (Amritsar, Ludhiana, Chandigarh, Delhi, Jaipur, Srinagar) stay off the ribbons. Their numbers in the mock follow Lahore. A ribbon that started there would point a path out of a copied value. When a city has its own IQAir or CAMS reading, the ribbon can start at that city. The drawing does not change. The endpoint becomes real.

Fires stay pins. A fire under an inflow thread is the reason you can see. Fires do not each grow a string to Lahore. Rajasthan detections south of 27°N stay out, as they already do.

### What the November record already says the threads must be able to show

These are facts from the 1–9 November all-sides product, not shapes we will hard-code:

- India was 56% of inflow over those days (Rajasthan 29%, Indian Punjab 22%, Jammu 5%).
- Rajasthan was the largest net source, into Bahawalnagar and Bahawalpur.
- Over the nine days more air left toward Indian Punjab than arrived. On 8–9 November that reversed.
- Khyber Pakhtunkhwa was a net source into Dera Ghazi Khan’s side of the province (Dera Ismail Khan, Bhakkar, Layyah).
- Punjab was a net exporter toward Sindh, Balochistan, and Azad Kashmir.

A scrubber that only ever draws “India into Lahore” cannot show that record. Two threads, allowed to point inward or outward on any side, can.

CAMS reads lower than the Punjab stations. The thread uses CAMS to decide where the outside load is and how strong the crossings are relative to each other. The wash inside Punjab stays the station field and the PEPC colors. The thread is not repainted in a CAMS color, and a CAMS number is not drawn as if it were an AQMS reading.

---

## Movement

The dashes already drift. Along a corridor they gather into the thread: same curves, same speed, a longer brighter run only where a hop or a crossing is real.

Scrubbing the hour rebuilds the threads from that hour’s wind and that hour’s concentrations. A morning inflow can be gone by evening, or reversed. The evening of 9 November is a light southwest wind. The first time this layer is turned on at that hour, the map may show almost nothing. That is the right picture. A layer that always marches into Lahore would be decoration.

With reduced motion the thread is still drawn. It does not travel.

The control is the existing Border switch.

- Off: the thin border line only.
- On: the corridors for the scrubbed hour, inside the province and across every side that has a CAMS point.

Wind stays the air-motion layer. Border becomes the part of that motion that is carrying pollution.

---

## What stays off the map

- The full set of hops. The math keeps up to 60. Drawing them is a spiderweb. The screen keeps two chains.
- Straight chords between district centroids.
- A second color ramp for “transboundary PM2.5” on top of the wash.
- Chevrons marching the whole India line on hours when the wind is calm, parallel, or outbound.
- Ribbons from the Lahore-scaled city anchors.
- AQI multiplied by wind.
- Kilograms per second from the CAMS worker fixture. That worker currently returns a fixed sample summary (about 482 kg/s in, 125 kg/s out) and does not query Copernicus. The threads use the 117-point series, the rank of side against side, not that fixture.
- Any change to station bubbles, the wash, the wind dashes, the fires, the card layout, the search, the zoom limit, or `src/`, until you accept the mock.

---

## What the card and the details add

On the open place, under the wind lines that are already there, two short lines when the Border layer is on and the hour has something to say:

- The inside role: receiving, passing through, or sending on. Name the neighbor on the strongest hop only.
- The outside role, if this district touches a side or is the end of a thread that does: coming in, leaving, or quiet. Name the side (Indian Punjab, Rajasthan, Khyber Pakhtunkhwa, Sindh, and the others), not a percentage printed on the map.

See details can list the hops that built the thread: from, to, distance, and whether each one is inside or a crossing. That list is text. It does not turn the map back into the 60-link diagram.

No pressure, humidity, or temperature is added. The baseline still does not have them.

---

## How a hour is chosen, in order

1. Read the hour’s ECMWF 10 m wind and the Punjab PM2.5 (the station field, never AQI).
2. Keep a hop only if it passes the calm cutoff, the 35° cone, and the 180 km limit. Rank by the flux formula.
3. Read the 117 CAMS points for that hour. Keep a crossing only where the wind component across the boundary and the CAMS PM2.5 are both real.
4. Join a crossing to the inside hop it feeds, or leave it as a short thread that fades inside the 120 km belt if no inside hop qualifies.
5. Chain inside hops that share a direction into paths. Score a path by its strongest hop.
6. Draw the top path. Draw the second only if it is not the same path and it is still strong. Otherwise draw one, or none.
7. The card sentence is taken from the path that touches the open place.

---

## When you say build

The first build is the mock only, under `ui-mock/`. `src/` stays as it is.

1. Put the 117-point CAMS series for this episode where the mock can read it, one value per point per hour. Do not wire the fixture kilograms.
2. Compute hops and crossings with the rules above. Cap the drawing at two paths.
3. Draw the thread after the wash and the district lines, with the wind dashes, so it feels like the same air.
4. Add the two card lines. Leave See details as the hop list.
5. You look at three hours on purpose: a quiet hour (9 November, 23:00), an inflow hour (8–9 November, India side), and an outflow hour toward Sindh or Indian Punjab. The three pictures must not be the same ribbon pointing at Lahore.

After that we talk about moving it into the application. Not before.

---

## If “CEMS” meant something else

If the Copernicus access you have is the emergency service rather than the atmosphere service, say which product. The concentrations this plan uses are CAMS PM2.5 at the 117 boundary points. Emergency burned-area maps would sit with the fire pins, not with the corridors.
