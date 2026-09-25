# Every screen

The phone screens of Second Look, in one drawn frame, captured by `make screens` (`apps/web/scripts/gallery.mjs`). Each caption says the route; "mock" marks a screen from a local build with the mocked API, and the rest come from the live site. The sizes, the frame and the alt text are checked by `scripts/tests/test_gallery.py` against `results/screens.json`.

<table>
<tr>
<td align="center"><img src="landing.webp" width="200" alt="The first screen: the question Which creek is healthier? above two creek photos."><br>Landing<br><code>/</code></td>
<td align="center"><img src="landing-guess.webp" width="200" alt="The same screen after a tap on the left photo: the guess is kept on the phone until the person agrees to take part."><br>The guess<br><code>/</code></td>
<td align="center"><img src="consent.webp" width="200" alt="The consent screen: what the test is, what is stored, and two boxes to tick."><br>Consent<br><code>/t</code> (mock)</td>
<td align="center"><img src="lesson-card.webp" width="200" alt="A lesson card on built banks: a concrete channel with two numbered marks, and what each mark points at."><br>A lesson card with its marks<br><code>/t</code> (mock)</td>
</tr>
<tr>
<td align="center"><img src="test-item.webp" width="200" alt="A test item: one creek photo, the question, and the buttons Yes, No and Can't tell."><br>A test item<br><code>/t</code> (mock)</td>
<td align="center"><img src="score.webp" width="200" alt="The score screen: the total and a score for each of the four features."><br>The score<br><code>/t</code> (mock)</td>
<td align="center"><img src="demo.webp" width="200" alt="Judge mode today: it opens on Sep 28, when the data locks."><br>Judge mode today<br><code>/demo</code></td>
<td align="center"><img src="judges.webp" width="200" alt="The page for judges: every part of Second Look, in order."><br>For judges<br><code>/judges</code></td>
</tr>
<tr>
<td align="center"><img src="walks.webp" width="200" alt="Check a creek from your desk: one short clip of a creek for each country."><br>Walks<br><code>/walk</code></td>
<td align="center"><img src="walk.webp" width="200" alt="A walk: the clip of a creek, with its credit, and a button to start the check."><br>A walk<br><code>/walk/v02</code></td>
<td align="center"><img src="walk-in-progress.webp" width="200" alt="A walk in progress: a question about the creek in the clip, with a progress count."><br>A walk in progress<br><code>/walk/v02</code></td>
<td align="center"><img src="walk-record.webp" width="200" alt="The record from the walk, made on the phone and never sent, with a line saying every link inside it checks out."><br>The walk record<br><code>/walk/v02</code></td>
</tr>
<tr>
<td align="center"><img src="walk-city.webp" width="200" alt="The walk seen as a city would see it, after answering Artificial for the bank: what this demo creek needs, in OneAquaHealth's own measures, each with its source."><br>The walk as a city sees it<br><code>/city?walk=v02</code></td>
<td align="center"><img src="check-start.webp" width="200" alt="The creek check: what it asks and a button to start."><br>Creek check<br><code>/check</code></td>
<td align="center"><img src="check-location.webp" width="200" alt="The creek check asks where you are: use the phone's location or drop a pin."><br>Where are you?<br><code>/check</code></td>
<td align="center"><img src="check-question.webp" width="200" alt="The first question of the creek check, with the answers as big buttons."><br>First question<br><code>/check</code></td>
</tr>
<tr>
<td align="center"><img src="quick.webp" width="200" alt="The quick check: water colour, smell and the pipe, in three taps."><br>Quick check<br><code>/quick</code></td>
<td align="center"><img src="spot-record.webp" width="200" alt="A sample creek record: what the volunteer saw, and the observer score that goes with it."><br>A sample record<br><code>/spot?id=example</code> (mock)</td>
<td align="center"><img src="spot-fhir.webp" width="200" alt="The same record opened with View as FHIR: the Observation the record is stored as."><br>View as FHIR<br><code>/spot?id=example</code> (mock)</td>
<td align="center"><img src="city.webp" width="200" alt="The city view of Strawberry Creek before anyone has checked it: no visits yet, and no OneAquaHealth measure shown yet."><br>City view<br><code>/city?creek=strawberry-creek</code></td>
</tr>
<tr>
<td align="center"><img src="two.webp" width="200" alt="Two kinds of observer: a volunteer record in the same viewer built for a laboratory result."><br>Two kinds of observer<br><code>/two</code></td>
<td align="center"><img src="how-we-know.webp" width="200" alt="How we know: where each rule and each number comes from."><br>How we know<br><code>/how-we-know</code></td>
<td align="center"><img src="credits.webp" width="200" alt="Credits: every photo and clip with its author and licence."><br>Credits<br><code>/credits</code></td>
<td align="center"><img src="privacy.webp" width="200" alt="Privacy: what is stored and what is not."><br>Privacy<br><code>/privacy</code></td>
</tr>
<tr>
<td align="center"><img src="about.webp" width="200" alt="About: what Second Look is and who made it."><br>About<br><code>/about</code></td>
<td align="center"><img src="poster.webp" width="200" alt="The poster to print and put up by a creek, with its QR code."><br>Poster<br><code>/poster</code></td>
<td align="center"><img src="verify.webp" width="200" alt="Check a record: its receipt, its place in the audit log and the OpenTimestamps proof."><br>Check a record<br><code>/verify</code></td>
<td align="center"><img src="warmup.webp" width="200" alt="The warm-up: which creek is healthier, asked once before the test and answered at the end."><br>The warm-up<br><code>/t</code> (mock)</td>
</tr>
<tr>
<td align="center"><img src="accessibility.webp" width="200" alt="Accessibility: what we aim for and how each part is checked."><br>Accessibility<br><code>/accessibility</code></td>
<td align="center"><img src="offline.webp" width="200" alt="The page a phone shows when it has no signal: what still works."><br>Offline<br><code>/offline</code></td>
<td align="center"><img src="share.webp" width="200" alt="The page a shared score opens: the score card and a link to take the test."><br>A shared score<br><code>/share/12</code></td>
<td align="center"><img src="spot-health.webp" width="200" alt="The end of the sample record: the What you can do card, with one thing to do for you, one for your pet and one for the city, and the source of each."><br>The health card<br><code>/spot?id=example</code> (mock)</td>
</tr>
</table>
