Instance: sl-questionnaire-test
InstanceOf: Questionnaire
Title: "Second Look observer test"
Description: "The two minute photo test. One group per feature, four photo items each. The response stores the per-feature score computed by code."
Usage: #example
* url = "https://github.com/alejandro-publius/second-look/fhir/Questionnaire/sl-questionnaire-test"
* name = "SecondLookObserverTest"
* title = "Second Look observer test"
* status = #draft
* date = "2026-09-20"
* publisher = "Second Look"
* item[0].linkId = "artificial_bank"
* item[0].text = "Built banks"
* item[0].type = #group
* item[0].item[0].linkId = "artificial_bank.score"
* item[0].item[0].text = "Items answered correctly out of 4"
* item[0].item[0].type = #integer
* item[1].linkId = "dug_out_channel"
* item[1].text = "Dug-out channel"
* item[1].type = #group
* item[1].item[0].linkId = "dug_out_channel.score"
* item[1].item[0].text = "Items answered correctly out of 4"
* item[1].item[0].type = #integer
* item[2].linkId = "invasive_plant"
* item[2].text = "Plants that do not belong"
* item[2].type = #group
* item[2].item[0].linkId = "invasive_plant.score"
* item[2].item[0].text = "Items answered correctly out of 4"
* item[2].item[0].type = #integer
* item[3].linkId = "pipe_running"
* item[3].text = "Pipes and sewage signs"
* item[3].type = #group
* item[3].item[0].linkId = "pipe_running.score"
* item[3].item[0].text = "Items answered correctly out of 4"
* item[3].item[0].type = #integer

Instance: sl-questionnaire-check
InstanceOf: Questionnaire
Title: "Second Look creek check"
Description: "The guided check at the creek. Link ids are the stable item ids from content/form.yaml. Coding displays are the code systems' own displays; the words a person sees live in content/form.yaml and mirror the official OneAquaHealth app where marked, unverified until checked against screenshots."
Usage: #example
* url = "https://github.com/alejandro-publius/second-look/fhir/Questionnaire/sl-questionnaire-check"
* name = "SecondLookCreekCheck"
* title = "Second Look creek check"
* status = #draft
* date = "2026-09-20"
* publisher = "Second Look"
* item[0].linkId = "bank_type"
* item[0].text = "What are the banks like?"
* item[0].type = #choice
* item[0].answerOption[0].valueCoding = TemporaryOahSystem#present "Present"
* item[0].answerOption[1].valueCoding = TemporaryOahSystem#absent "Absent"
* item[0].answerOption[2].valueCoding = SecondLookCS#cant-tell "Can't tell"
* item[1].linkId = "channel_form"
* item[1].text = "Does the channel look dug out or straightened?"
* item[1].type = #choice
* item[1].answerOption[0].valueCoding = TemporaryOahSystem#present "Present"
* item[1].answerOption[1].valueCoding = TemporaryOahSystem#absent "Absent"
* item[1].answerOption[2].valueCoding = SecondLookCS#cant-tell "Can't tell"
* item[2].linkId = "invasive_species"
* item[2].text = "Do you see any non-native or invasive plant species?"
* item[2].type = #choice
* item[2].answerOption[0].valueCoding = TemporaryOahSystem#present "Present"
* item[2].answerOption[1].valueCoding = TemporaryOahSystem#absent "Absent"
* item[2].answerOption[2].valueCoding = SecondLookCS#cant-tell "Can't tell"
* item[3].linkId = "draining_pipes"
* item[3].text = "Are there pipes draining polluted water into the stream?"
* item[3].type = #choice
* item[3].answerOption[0].valueCoding = TemporaryOahSystem#present "Present"
* item[3].answerOption[1].valueCoding = TemporaryOahSystem#absent "Absent"
* item[3].answerOption[2].valueCoding = SecondLookCS#cant-tell "Can't tell"
* item[4].linkId = "water_height_m"
* item[4].text = "Water height in metres"
* item[4].type = #decimal
