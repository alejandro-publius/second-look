CodeSystem: SecondLookCS
Id: second-look
Title: "Second Look codes"
Description: """Codes for the four stream features a volunteer is tested on, the answer a person cannot give, and the test itself. Everything else reuses the OneAquaHealth temporary code system."""
* ^url = "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look"
* ^status = #draft
* ^experimental = true
* ^caseSensitive = true
* ^content = #complete
* #artificial-bank "Artificial bank" "A built bank: concrete walls, stones set in concrete, or other constructed edges."
* #dug-out-channel "Dug-out channel" "A channel that was deepened or straightened: even sloped banks, a straightened course, the same width all along, slow flat water."
* #invasive-plant "Invasive plant" "A non-native or invasive plant species present on the bank or in the channel."
* #pipe-running "Pipe running" "A pipe or outlet with flow, or sewage signs such as staining or grey water."
* #cant-tell "Can't tell" "The observer could not decide from what they saw."
* #second-look-test "Second Look observer test" "A two minute photo test on the four features, scored per feature out of 4."
* #software "Second Look software" "The Second Look application acting as an agent."

ValueSet: SecondLookFeatureVS
Id: second-look-feature-vs
Title: "Second Look feature codes"
Description: "The four features an observer answers about."
* ^status = #draft
* SecondLookCS#artificial-bank
* SecondLookCS#dug-out-channel
* SecondLookCS#invasive-plant
* SecondLookCS#pipe-running

ValueSet: SecondLookAnswerVS
Id: second-look-answer-vs
Title: "Second Look answer values"
Description: "Present and absent come from the OneAquaHealth temporary code system. Can't tell is ours."
* ^status = #draft
* TemporaryOahSystem#present
* TemporaryOahSystem#absent
* SecondLookCS#cant-tell
