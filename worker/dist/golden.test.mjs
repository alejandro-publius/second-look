// test/golden.test.ts
import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

// src/content.json
var content_default = {
  check_languages: [
    "en",
    "pt",
    "nl",
    "no",
    "fr",
    "it"
  ],
  content_hash: "fa7a36fea4214cf4",
  creeks: [
    {
      name: "Strawberry Creek",
      reaches: [
        {
          bbox: [
            37.869,
            -122.253,
            37.878,
            -122.235
          ],
          flows_into: "south-fork-campus",
          name: "South Fork, Strawberry Canyon",
          slug: "south-fork-canyon"
        },
        {
          bbox: [
            37.8695,
            -122.2645,
            37.873,
            -122.253
          ],
          flows_into: "campus-west",
          name: "South Fork, central campus",
          slug: "south-fork-campus"
        },
        {
          bbox: [
            37.8731,
            -122.2645,
            37.8775,
            -122.253
          ],
          flows_into: "campus-west",
          name: "North Fork, campus",
          slug: "north-fork-campus"
        },
        {
          bbox: [
            37.87,
            -122.267,
            37.8735,
            -122.2645
          ],
          flows_into: "downtown-culvert",
          name: "Below the forks, west campus",
          slug: "campus-west"
        },
        {
          bbox: [
            37.866,
            -122.286,
            37.874,
            -122.267
          ],
          flows_into: "strawberry-creek-park",
          name: "Downtown culvert",
          slug: "downtown-culvert"
        },
        {
          bbox: [
            37.8655,
            -122.2905,
            37.869,
            -122.286
          ],
          flows_into: "west-culvert",
          name: "Strawberry Creek Park",
          slug: "strawberry-creek-park"
        },
        {
          bbox: [
            37.86,
            -122.32,
            37.872,
            -122.2905
          ],
          flows_into: null,
          name: "West Berkeley culvert, to the Bay",
          slug: "west-culvert"
        }
      ],
      slug: "strawberry-creek",
      source: "Hand filled 2026-09-21 from public maps of the UC Berkeley campus and the City of Berkeley. Boxes are approximate."
    }
  ],
  feature_list: [
    {
      id: "artificial_bank",
      name: "Built banks",
      plain: "concrete walls and other built banks",
      question: "Are the banks artificial, such as concrete or stones set in concrete?"
    },
    {
      id: "dug_out_channel",
      name: "Dug-out channel",
      plain: "a channel that was deepened or straightened",
      question: "Has this channel been straightened or dug out?"
    },
    {
      id: "invasive_plant",
      name: "Plants that do not belong",
      plain: "pretty plants that do not belong here",
      question: "Do you see any non-native or invasive plant species?"
    },
    {
      id: "pipe_running",
      name: "Pipes and drain outlets",
      plain: "pipes and drain outlets that empty into the creek",
      question: "Can you see a pipe or drain outlet that empties into this creek?"
    }
  ],
  features: [
    "artificial_bank",
    "dug_out_channel",
    "invasive_plant",
    "pipe_running"
  ],
  fhir: {
    oah_displays: {
      LandUse: "Land use in the margins",
      absent: "Absent",
      bushes: "Bushes (height (1.5-3m)",
      foam: "Foam/colour/smell",
      herbaceous: "Herbaceous (height < 1.5m)",
      hydrology: "Hydrology of the stream",
      invasiveOrganisms: "Invasive invertebrate, plants and fish",
      morophology: "Morphology of the streams",
      present: "Present",
      riparianVegetation: "Riparian vegetation",
      trees: "Trees (height >3m)"
    },
    oah_location_profile: "http://hl7.eu/fhir/ig/oah/StructureDefinition/location-oah",
    oah_observation_profile: "http://hl7.eu/fhir/ig/oah/StructureDefinition/observation-indicators-oah",
    oah_system: "http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu",
    repo_url: "https://github.com/alejandro-publius/second-look",
    sl_displays: {
      "aquatic-vegetation": "Aquatic vegetation",
      "artificial-bank": "Artificial bank",
      "cant-tell": "Can't tell",
      dry: "Dry channel",
      "dug-out-channel": "Dug-out channel",
      example: "Example, not a real result",
      "fallen-branches": "Fallen branches",
      "fallen-trees": "Fallen trees",
      fast: "Fast flow",
      "first-rating": "First overall rating",
      flat: "Flat channel",
      good: "Good overall rating",
      "invasive-plant": "Invasive plant",
      "lab-ecoli-cfu": "Escherichia coli, colony forming units",
      "lab-enterobacteriaceae-share": "Enterobacteriaceae, share of 16S reads",
      "lab-hf183": "Human faecal marker HF183",
      "leaf-deposits": "Deposits of fallen leaves",
      moderate: "Moderate overall rating",
      "overall-rating": "Overall rating",
      "pipe-running": "Pipe running",
      poor: "Poor overall rating",
      riffles: "Riffles, rapids or falls",
      "sand-banks": "Sand banks",
      "sand-islands": "Sand islands",
      "second-look-test": "Second Look observer test",
      slow: "Slow flow",
      software: "Second Look software",
      stagnant: "Stagnant or intermittent flow",
      "stone-deposits": "Stone deposits",
      "test-pipe-outflow": "Test the water coming out of this pipe",
      "u-shape": "U shaped channel",
      "v-shape": "V shaped channel"
    },
    sl_system: "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look",
    ucum_displays: {
      "%": "percent",
      Cel: "degree Celsius",
      "[CFU]/dL": "colony forming units per 100 mL",
      cm: "centimetre",
      m: "metre",
      mL: "millilitre"
    }
  },
  followups: {
    max_questions: 2,
    rules: [
      {
        dry_rule: {
          max_mm: 2.5,
          window_hours: 72
        },
        fail_closed: "if rainfall or location is unknown, this rule does not fire",
        id: "dry_pipe",
        needs_items: [
          "draining_pipes",
          "sewage_discharge"
        ],
        priority: 1,
        question_key: "followup.dry_pipe",
        trigger: "draining_pipes or sewage_discharge answered present, and rainfall status is dry"
      },
      {
        id: "rating_check",
        needs_items: [
          "overall_rating",
          "bank_type",
          "impervious_left",
          "impervious_right",
          "invasive_species",
          "sewage_discharge"
        ],
        priority: 2,
        question_key: "followup.rating_check",
        stores: [
          "first_rating",
          "final_rating"
        ],
        trigger: "overall_rating is good, and any of bank_type present, impervious_left present, impervious_right present, invasive_species present, sewage_discharge present"
      },
      {
        feature_flag: "CHECKER_ENABLED",
        id: "checker_flag",
        needs_items: [],
        priority: 3,
        question_key: "followup.checker_flag",
        trigger: "a Flag from core.gate for a feature the model passed, shown only after the person answered"
      },
      {
        asks_for: "photo",
        id: "low_score",
        needs_items: [
          "bank_type",
          "draining_pipes",
          "invasive_species"
        ],
        priority: 4,
        question_key: "followup.low_score",
        trigger: "observer scored 2 of 4 or lower on a feature and answered absent for that feature"
      }
    ]
  },
  form_items: [
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah"
      },
      id: "channel_form",
      name: "Channel Form",
      options: [
        {
          id: "flat",
          label: "Flat",
          value: "flat"
        },
        {
          id: "u_shape",
          label: "U Shape",
          value: "u_shape"
        },
        {
          id: "v_shape",
          label: "V Shape",
          value: "v_shape"
        },
        {
          id: "not_sure",
          label: "I\u2019m not sure",
          value: "cant_tell"
        }
      ],
      section: "what_you_see",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "The channel form is...",
      type: "choice",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah",
        finding: "Artificial channel bottom"
      },
      id: "bottom_type",
      name: "Bottom Type",
      options: [
        {
          id: "natural",
          label: "Natural",
          value: "absent"
        },
        {
          id: "artificial",
          label: "Artificial (concrete or stones with concrete)",
          value: "present"
        },
        {
          id: "not_sure",
          label: "I\u2019m not sure",
          value: "cant_tell"
        }
      ],
      section: "what_you_see",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "The bottom of the wet channel is\u2026",
      type: "choice",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: "artificial_bank",
      fhir: {
        category: "morophology",
        code: "artificial-bank",
        code_system: "sl"
      },
      id: "bank_type",
      name: "Bank Type",
      options: [
        {
          id: "natural",
          label: "Natural",
          value: "absent"
        },
        {
          id: "artificial",
          label: "Artificial (concrete or stones with concrete)",
          value: "present"
        },
        {
          id: "laid_stones",
          label: "Layed stones with no concrete",
          value: "absent"
        },
        {
          id: "not_sure",
          label: "I\u2019m not sure",
          value: "cant_tell"
        }
      ],
      section: "what_you_see",
      short_label: "artificial banks",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "The banks of the channel are\u2026",
      type: "choice",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah"
      },
      id: "habitats",
      name: "Habitats",
      options: [
        {
          id: "sand_banks",
          label: "Sand banks",
          value: "sand_banks"
        },
        {
          id: "sand_islands",
          label: "Sand islands",
          value: "sand_islands"
        },
        {
          id: "stone_deposits",
          label: "Stone deposits",
          value: "stone_deposits"
        },
        {
          id: "riffles",
          label: "Riffles, rapids, falls",
          value: "riffles"
        },
        {
          id: "aquatic_vegetation",
          label: "Aquatic vegetation",
          value: "aquatic_vegetation"
        }
      ],
      section: "what_you_see",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Are there any habitats present?",
      type: "multi",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah"
      },
      id: "natural_debris",
      name: "Natural Debris",
      options: [
        {
          id: "fallen_trees",
          label: "Fallen trees",
          value: "fallen_trees"
        },
        {
          id: "fallen_branches",
          label: "Fallen branches",
          value: "fallen_branches"
        },
        {
          id: "leaf_deposits",
          label: "Deposits of fallen leaves",
          value: "leaf_deposits"
        }
      ],
      section: "what_you_see",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Are there any natural debris present?",
      type: "multi",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "hydrology",
        code_system: "oah"
      },
      id: "water_flow",
      name: "Water Flow",
      options: [
        {
          id: "fast",
          label: "Fast (with waves or high velocity)",
          value: "fast"
        },
        {
          id: "slow",
          label: "Slow",
          value: "slow"
        },
        {
          id: "stagnant",
          label: "Stagnant/intermittent",
          value: "stagnant"
        },
        {
          id: "dry",
          label: "Dry",
          value: "dry"
        },
        {
          id: "not_sure",
          label: "I\u2019m not sure",
          value: "cant_tell"
        }
      ],
      section: "what_you_see",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "How is the water flowing",
      type: "choice",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "foam",
        code_system: "oah",
        finding: "Muddy water, foam or a changed colour"
      },
      id: "water_aspect",
      name: "Water Aspect",
      options: [
        {
          id: "clear",
          label: "Clear/transparent",
          value: "absent"
        },
        {
          id: "muddy",
          label: "Muddy/turbid",
          value: "present"
        },
        {
          id: "foam",
          label: "Has foam",
          value: "present"
        },
        {
          id: "colour",
          label: "Has colors/altered color",
          value: "present"
        },
        {
          id: "not_sure",
          label: "I\u2019m not sure",
          value: "cant_tell"
        }
      ],
      section: "water",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "How is the water?",
      type: "choice",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "hydrology",
        code_system: "oah",
        finding: "Water taken from the stream"
      },
      id: "water_withdrawal",
      name: "Water Withdrawal",
      section: "water",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Is there any kind of obvious water collection, use, removal from the stream?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah",
        finding: "Dam or other barrier across the stream"
      },
      id: "barriers",
      name: "Barriers",
      section: "water",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Do you see any dams or other transversal artificial barriers?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: "pipe_running",
      fhir: {
        category: "hydrology",
        code: "pipe-running",
        code_system: "sl"
      },
      id: "draining_pipes",
      name: "Draining Pipes",
      section: "water",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Are there pipes draining polluted water into the stream?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: "pipe_running",
      fhir: {
        category: "hydrology",
        code: "pipe-running",
        code_system: "sl"
      },
      id: "sewage_discharge",
      name: "Sewage discharge",
      section: "water",
      short_label: "a sewage discharge",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Is there any kind of water entry or discharge of sewage?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah",
        finding: "Construction or works in the stream"
      },
      id: "construction",
      name: "Construction",
      section: "water",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Is there any construction/works in stream?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "hydrology",
        code_system: "oah",
        unit: "m"
      },
      id: "water_height_m",
      name: "Water height",
      section: "water",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "What is the water height?",
      type: "number",
      unit: "m",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "LandUse",
        code_system: "oah",
        finding: "Left margin more than one third paved or built on"
      },
      id: "impervious_left",
      name: "Impervious Areas (Left)",
      section: "margins",
      short_label: "a paved left margin",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Is more than one third of the left margin covered by impervious areas (such as roads, sidewalks or buildings)?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "LandUse",
        code_system: "oah",
        finding: "Right margin more than one third paved or built on"
      },
      id: "impervious_right",
      name: "Impervious Areas (Right)",
      section: "margins",
      short_label: "a paved right margin",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Is more than one third of the right margin covered by impervious areas (such as roads, sidewalks or buildings)?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah",
        finding: "Left margin covered by vegetation"
      },
      id: "vegetation_left",
      name: "Vegetation (Left)",
      section: "margins",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Is the left margin covered by vegetation?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah",
        finding: "Right margin covered by vegetation"
      },
      id: "vegetation_right",
      name: "Vegetation (Right)",
      section: "margins",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Is the right margin covered by vegetation?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah"
      },
      id: "vegetation_type_left",
      name: "Vegetation Type (Left)",
      options: [
        {
          id: "herbs",
          label: "Herbs",
          value: "herbaceous"
        },
        {
          id: "shrubs",
          label: "Shrubs",
          value: "bushes"
        },
        {
          id: "trees",
          label: "Trees",
          value: "trees"
        },
        {
          id: "not_sure",
          label: "I\u2019m not sure",
          value: "cant_tell"
        }
      ],
      section: "margins",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Which vegetation is dominant (meaning that it covers more than 50%, or half) in the left margin (first 5 meters from the channel banktop)?",
      type: "choice",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah"
      },
      id: "vegetation_type_right",
      name: "Vegetation Type (Right)",
      options: [
        {
          id: "herbs",
          label: "Herbs",
          value: "herbaceous"
        },
        {
          id: "shrubs",
          label: "Shrubs",
          value: "bushes"
        },
        {
          id: "trees",
          label: "Trees",
          value: "trees"
        },
        {
          id: "not_sure",
          label: "I\u2019m not sure",
          value: "cant_tell"
        }
      ],
      section: "margins",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Which vegetation is dominant (meaning that it covers more than 50%, or half) in the right margin (first 5 meters from the channel bank/top)?",
      type: "choice",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: "invasive_plant",
      fhir: {
        category: "invasiveOrganisms",
        code: "invasive-plant",
        code_system: "sl"
      },
      id: "invasive_species",
      name: "Invasive Species",
      section: "margins",
      short_label: "invasive plants",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Do you see any non-native or invasive plant species?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      depends_on: {
        item: "invasive_species",
        value: "present"
      },
      feature: "invasive_plant",
      fhir: {
        category: "invasiveOrganisms",
        code: "invasive-plant",
        code_system: "sl"
      },
      id: "invasive_which",
      note: "The app offers free text here. We offer the regional list plus Not sure, so no free text is stored.",
      region_list: "invasive_plants",
      section: "margins",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Which ones?",
      type: "pick_region_list",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah",
        finding: "Recent cuts of vegetation on the banks"
      },
      id: "vegetation_cuts",
      name: "Vegetation Cuts",
      section: "margins",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Have there been recent cuts if vegetation (partial or total) on the banks (or just one of the banks) of the stream?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      allow_not_applicable: true,
      feature: null,
      fhir: null,
      id: "feelings",
      section: "feelings",
      sliders: [
        "joy",
        "serenity",
        "anger",
        "fear"
      ],
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Which feeling(s) best describe your experience?",
      type: "sliders",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: null,
      id: "overall_rating",
      options: [
        {
          description: "The ecosystem components are there: riparian vegetation, natural channel, good water quality, biodiversity",
          id: "good",
          label: "Good quality",
          value: "good"
        },
        {
          description: "Some alterations, still biodiverse, with vegetation in the margins, water looks good...",
          id: "moderate",
          label: "Moderate quality",
          value: "moderate"
        },
        {
          description: "Highly modified / artificialized, loss of riparian vegetation, loss of habitats, polluted",
          id: "poor",
          label: "Poor quality",
          value: "poor"
        }
      ],
      rating_check: true,
      section: "overall",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Provide an overall assessment of the stream ecosystem health (choose one of the below possibilities)",
      type: "choice",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    }
  ],
  locale: {
    "error.content": "This photo is missing from the content. Please tell us.",
    "error.network": "Something did not send. Check your connection and try again.",
    "error.nothing_here": "There is nothing to show on this screen. The content may be part way through an edit.",
    "error.retry": "Try again",
    "error.server": "The server could not take that. Try again in a moment.",
    "error.start_over": "Start again",
    "followup.checker_flag": "The checker noticed something that may be {note}. Want to look again?",
    "followup.dry_pipe": "It has not rained here for {days} days. Is anything coming out of that pipe? A pipe still running after three dry days is worth testing.",
    "followup.low_score": "You scored {correct} of 4 on {feature} in the test. Could you take a photo of the {feature} so a reviewer can check?",
    "followup.rating_check": "You rated this stream Good, but you also reported {issues}. Do you want to keep your rating?",
    "label.checker_noticed": "the checker noticed",
    "label.expired": "Score expired. Tested {date}, more than 90 days ago. Retake the test.",
    "label.score": "{correct} of {total} on {feature}, tested {date}",
    "test.cant_tell": "Can't tell",
    "test.no": "No",
    "test.yes": "Yes"
  },
  part2_flags: {
    a01: "present",
    a02: "absent",
    a03: "present",
    a04: "absent",
    a05: null,
    a06: null,
    a07: "present",
    a08: "absent"
  },
  part2_items: [
    {
      feature: "artificial_bank",
      gold: "present",
      id: "a01"
    },
    {
      feature: "artificial_bank",
      gold: "absent",
      id: "a02"
    },
    {
      feature: "dug_out_channel",
      gold: "present",
      id: "a03"
    },
    {
      feature: "dug_out_channel",
      gold: "absent",
      id: "a04"
    },
    {
      feature: "invasive_plant",
      gold: "present",
      id: "a05"
    },
    {
      feature: "invasive_plant",
      gold: "absent",
      id: "a06"
    },
    {
      feature: "pipe_running",
      gold: "present",
      id: "a07"
    },
    {
      feature: "pipe_running",
      gold: "absent",
      id: "a08"
    }
  ],
  region_plants: [
    "Ailanthus altissima",
    "Algerian ivy",
    "Arundo donax",
    "Cape ivy",
    "Conium maculatum",
    "Cortaderia jubata",
    "Delairea odorata",
    "English ivy",
    "Fennel",
    "Foeniculum vulgare",
    "French broom",
    "Genista monspessulana",
    "Giant reed",
    "Hedera canariensis",
    "Hedera helix",
    "Himalayan blackberry",
    "Jubata grass",
    "Periwinkle",
    "Poison hemlock",
    "Rubus armeniacus",
    "Tree of heaven",
    "Vinca major"
  ],
  rules: {
    features_in_order: [
      "artificial_bank",
      "dug_out_channel",
      "invasive_plant",
      "pipe_running"
    ],
    human_pass_min: 3,
    items_per_feature: 4,
    low_score_max_correct: 2,
    measure_for_feature: {
      artificial_bank: [
        "city_replant_margins",
        "city_remove_concrete"
      ],
      barriers: [
        "city_remove_barriers"
      ],
      dug_out_channel: [
        "city_reconnect_floodplain"
      ],
      pipe_running: [
        "city_fix_sewers"
      ]
    },
    pipe_items: [
      "draining_pipes",
      "sewage_discharge"
    ],
    pipe_observers_needed: 2,
    rating_issue_items: [
      "bank_type",
      "impervious_left",
      "impervious_right",
      "invasive_species",
      "sewage_discharge"
    ],
    same_spot_metres: 30,
    score_valid_days: 90,
    test_name_words: [
      "abc",
      "asdf",
      "bar",
      "baz",
      "delete",
      "demo",
      "dummy",
      "example",
      "foo",
      "ignore",
      "placeholder",
      "qwerty",
      "sample",
      "test",
      "testing",
      "todo",
      "xxx"
    ]
  },
  sentences: [
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "city",
      id: "city_replant_margins",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "OneAquaHealth Policy Brief (2026), page 9: rehabilitation of the riparian vegetation should prioritize a diverse corridor with native species, along both stream margins, free from unnecessary clearing. https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf",
      text: "Replant both margins with native trees and shrubs, and stop cutting them back."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "city",
      id: "city_fix_sewers",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "OneAquaHealth Policy Brief (2026), page 9: improvement of sewage systems and water treatments. https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf",
      text: "Find and fix leaking or wrongly connected sewers, and improve the treatment of waste water."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "city",
      id: "city_reconnect_floodplain",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "OneAquaHealth Policy Brief (2026), page 9: creation of space for natural flooding, removal of grey infrastructure from the margins and floodplains. https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf",
      text: "Give the stream room to flood: move walls, pavement and pipes back from the banks and the floodplain."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "city",
      id: "city_remove_barriers",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "OneAquaHealth Policy Brief (2026), page 9: removal of barriers to the longitudinal connectivity (dams, weirs, grids). https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf",
      text: "Remove dams, weirs and grids that stop water, sand and animals moving along the stream."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "city",
      id: "city_remove_concrete",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "OneAquaHealth Policy Brief (2026), page 9: removal of artificial materials (e.g. concrete); renaturalization of channels and margins with natural materials. https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf",
      text: "Take the concrete out of the channel and banks and rebuild them with natural materials."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "pet",
      id: "pet_keep_out_foam",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "CDC, Preventing Illness from Harmful Algal Blooms: keep pets and livestock away from water with signs of a bloom. https://www.cdc.gov/harmful-algal-blooms/prevention/index.html",
      text: "Keep dogs out of water that smells bad, looks discoloured, or has foam, scum or mats, and do not let them drink it."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "pet",
      id: "pet_rinse_after",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "CDC, Preventing Illness from Harmful Algal Blooms: rinse them off immediately; do not let them lick their fur before you rinse them. https://www.cdc.gov/harmful-algal-blooms/prevention/index.html",
      text: "If your dog goes in, rinse it with tap water straight away and do not let it lick its fur first."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "pet",
      id: "pet_bring_water",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "CDC, Preventing Illness from Harmful Algal Blooms: keep pets away from water with signs of a bloom. https://www.cdc.gov/harmful-algal-blooms/prevention/index.html",
      text: "Bring drinking water for your dog so it does not need to drink from the creek."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "pet",
      id: "pet_call_vet",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "CDC, Preventing Illness from Harmful Algal Blooms: if your pets seem sick after going in or near water, call a veterinarian right away. https://www.cdc.gov/harmful-algal-blooms/prevention/index.html",
      text: "If your dog seems sick after being in or near the water, call a vet right away."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "person",
      id: "person_avoid_foam_scum",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "CDC, Preventing Illness from Harmful Algal Blooms: if water looks or smells bad, stay out. https://www.cdc.gov/harmful-algal-blooms/prevention/index.html",
      text: "Stay out of water that smells bad, looks discoloured, or has foam, scum or mats on the surface."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "person",
      id: "person_rinse_hands",
      note: "Both cited pages fetched again on 2026-09-21; the matching sentences are in source_quote.",
      source: "CDC, Preventing Illness from Harmful Algal Blooms: rinse off immediately after touching water; CDC, Healthy Swimming, Steps to Take: wash your hands before eating. https://www.cdc.gov/harmful-algal-blooms/prevention/index.html and https://www.cdc.gov/healthy-swimming/prevention/index.html",
      source_quote: "If you do go in or touch water that may have a harmful algal bloom, rinse off immediately after. Use tap water from a sink, shower, hose, or outdoor spigot. (CDC, Harmful Algal Blooms, Prevention.) Wash your hands for 20 seconds before eating, especially if you have been playing in or touching sand. (CDC, Healthy Swimming, Prevention.)",
      text: "If you touch creek water, rinse your hands with tap water afterwards, and wash them before you eat."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "person",
      id: "person_avoid_pipes",
      note: "Cited page fetched again on 2026-09-21; the matching sentence is in source_quote.",
      source: "CDC, Healthy Swimming, Steps to Take: stay out if you see pipes. https://www.cdc.gov/healthy-swimming/prevention/index.html",
      source_quote: "Stay out if you see pipes. Pipes draining into or around the water could be putting germs or harmful chemicals into the water.",
      text: "Stay out of the water right below a pipe that drains into the creek."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "person",
      id: "person_report_dry_pipe",
      note: "The PDF was fetched again on 2026-09-21 and both sentences found by text search; they are in source_quote.",
      source: "EPA, Illicit Discharge Detection and Elimination guidance manual (2004), page 337 (72 hours dry) and page 6 (testing is needed before calling a flow polluted). https://www.epa.gov/sites/default/files/2015-11/documents/idde_manualwithappendices.pdf",
      source_quote: "While the traditional definition of dry weather has been 72 hours without rainfall, some communities have shortened this window to 48 hours to make sampling more practical. (page 337) Consequently, field testing and/or water quality sampling are needed to confirm whether pollutants are actually present in dry weather flow, in order to classify them as an illicit discharge. (chapter 1, page 6, PDF page 20)",
      text: "If a pipe is running after three dry days, note the place and the date and tell the city. It is worth testing."
    }
  ],
  test_items: [
    {
      feature: "artificial_bank",
      gold: "present",
      id: "t01"
    },
    {
      feature: "artificial_bank",
      gold: "present",
      id: "t02"
    },
    {
      feature: "artificial_bank",
      gold: "absent",
      id: "t03"
    },
    {
      feature: "artificial_bank",
      gold: "absent",
      id: "t04"
    },
    {
      feature: "dug_out_channel",
      gold: "present",
      id: "t05"
    },
    {
      feature: "dug_out_channel",
      gold: "present",
      id: "t06"
    },
    {
      feature: "dug_out_channel",
      gold: "absent",
      id: "t07"
    },
    {
      feature: "dug_out_channel",
      gold: "absent",
      id: "t08"
    },
    {
      feature: "invasive_plant",
      gold: "present",
      id: "t09"
    },
    {
      feature: "invasive_plant",
      gold: "present",
      id: "t10"
    },
    {
      feature: "invasive_plant",
      gold: "absent",
      id: "t11"
    },
    {
      feature: "invasive_plant",
      gold: "absent",
      id: "t12"
    },
    {
      feature: "pipe_running",
      gold: "present",
      id: "t13"
    },
    {
      feature: "pipe_running",
      gold: "present",
      id: "t14"
    },
    {
      feature: "pipe_running",
      gold: "absent",
      id: "t15"
    },
    {
      feature: "pipe_running",
      gold: "absent",
      id: "t16"
    }
  ],
  walks: [
    {
      creek_name: "A creek in Russia",
      id: "v02",
      spot_name: "The stretch in the clip"
    },
    {
      creek_name: "A creek in the United Kingdom",
      id: "v03",
      spot_name: "The stretch in the clip"
    },
    {
      creek_name: "A creek in the United States",
      id: "v07",
      spot_name: "The stretch in the clip"
    }
  ],
  warmup_ids: [
    "w01",
    "w02"
  ]
};

// src/core/core_content.json
var core_content_default = {
  creeks: [
    {
      name: "Strawberry Creek",
      reaches: [
        {
          bbox: [
            37.869,
            -122.253,
            37.878,
            -122.235
          ],
          flows_into: "south-fork-campus",
          name: "South Fork, Strawberry Canyon",
          slug: "south-fork-canyon"
        },
        {
          bbox: [
            37.8695,
            -122.2645,
            37.873,
            -122.253
          ],
          flows_into: "campus-west",
          name: "South Fork, central campus",
          slug: "south-fork-campus"
        },
        {
          bbox: [
            37.8731,
            -122.2645,
            37.8775,
            -122.253
          ],
          flows_into: "campus-west",
          name: "North Fork, campus",
          slug: "north-fork-campus"
        },
        {
          bbox: [
            37.87,
            -122.267,
            37.8735,
            -122.2645
          ],
          flows_into: "downtown-culvert",
          name: "Below the forks, west campus",
          slug: "campus-west"
        },
        {
          bbox: [
            37.866,
            -122.286,
            37.874,
            -122.267
          ],
          flows_into: "strawberry-creek-park",
          name: "Downtown culvert",
          slug: "downtown-culvert"
        },
        {
          bbox: [
            37.8655,
            -122.2905,
            37.869,
            -122.286
          ],
          flows_into: "west-culvert",
          name: "Strawberry Creek Park",
          slug: "strawberry-creek-park"
        },
        {
          bbox: [
            37.86,
            -122.32,
            37.872,
            -122.2905
          ],
          flows_into: null,
          name: "West Berkeley culvert, to the Bay",
          slug: "west-culvert"
        }
      ],
      slug: "strawberry-creek",
      source: "Hand filled 2026-09-21 from public maps of the UC Berkeley campus and the City of Berkeley. Boxes are approximate."
    }
  ],
  fhir: {
    oah_displays: {
      LandUse: "Land use in the margins",
      absent: "Absent",
      bushes: "Bushes (height (1.5-3m)",
      foam: "Foam/colour/smell",
      herbaceous: "Herbaceous (height < 1.5m)",
      hydrology: "Hydrology of the stream",
      invasiveOrganisms: "Invasive invertebrate, plants and fish",
      morophology: "Morphology of the streams",
      present: "Present",
      riparianVegetation: "Riparian vegetation",
      trees: "Trees (height >3m)"
    },
    oah_location_profile: "http://hl7.eu/fhir/ig/oah/StructureDefinition/location-oah",
    oah_observation_profile: "http://hl7.eu/fhir/ig/oah/StructureDefinition/observation-indicators-oah",
    oah_system: "http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu",
    repo_url: "https://github.com/alejandro-publius/second-look",
    sl_displays: {
      "aquatic-vegetation": "Aquatic vegetation",
      "artificial-bank": "Artificial bank",
      "cant-tell": "Can't tell",
      dry: "Dry channel",
      "dug-out-channel": "Dug-out channel",
      example: "Example, not a real result",
      "fallen-branches": "Fallen branches",
      "fallen-trees": "Fallen trees",
      fast: "Fast flow",
      "first-rating": "First overall rating",
      flat: "Flat channel",
      good: "Good overall rating",
      "invasive-plant": "Invasive plant",
      "lab-ecoli-cfu": "Escherichia coli, colony forming units",
      "lab-enterobacteriaceae-share": "Enterobacteriaceae, share of 16S reads",
      "lab-hf183": "Human faecal marker HF183",
      "leaf-deposits": "Deposits of fallen leaves",
      moderate: "Moderate overall rating",
      "overall-rating": "Overall rating",
      "pipe-running": "Pipe running",
      poor: "Poor overall rating",
      riffles: "Riffles, rapids or falls",
      "sand-banks": "Sand banks",
      "sand-islands": "Sand islands",
      "second-look-test": "Second Look observer test",
      slow: "Slow flow",
      software: "Second Look software",
      stagnant: "Stagnant or intermittent flow",
      "stone-deposits": "Stone deposits",
      "test-pipe-outflow": "Test the water coming out of this pipe",
      "u-shape": "U shaped channel",
      "v-shape": "V shaped channel"
    },
    sl_system: "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look",
    ucum_displays: {
      "%": "percent",
      Cel: "degree Celsius",
      "[CFU]/dL": "colony forming units per 100 mL",
      cm: "centimetre",
      m: "metre",
      mL: "millilitre"
    }
  },
  followups: {
    max_questions: 2,
    rules: [
      {
        dry_rule: {
          max_mm: 2.5,
          window_hours: 72
        },
        fail_closed: "if rainfall or location is unknown, this rule does not fire",
        id: "dry_pipe",
        needs_items: [
          "draining_pipes",
          "sewage_discharge"
        ],
        priority: 1,
        question_key: "followup.dry_pipe",
        trigger: "draining_pipes or sewage_discharge answered present, and rainfall status is dry"
      },
      {
        id: "rating_check",
        needs_items: [
          "overall_rating",
          "bank_type",
          "impervious_left",
          "impervious_right",
          "invasive_species",
          "sewage_discharge"
        ],
        priority: 2,
        question_key: "followup.rating_check",
        stores: [
          "first_rating",
          "final_rating"
        ],
        trigger: "overall_rating is good, and any of bank_type present, impervious_left present, impervious_right present, invasive_species present, sewage_discharge present"
      },
      {
        feature_flag: "CHECKER_ENABLED",
        id: "checker_flag",
        needs_items: [],
        priority: 3,
        question_key: "followup.checker_flag",
        trigger: "a Flag from core.gate for a feature the model passed, shown only after the person answered"
      },
      {
        asks_for: "photo",
        id: "low_score",
        needs_items: [
          "bank_type",
          "draining_pipes",
          "invasive_species"
        ],
        priority: 4,
        question_key: "followup.low_score",
        trigger: "observer scored 2 of 4 or lower on a feature and answered absent for that feature"
      }
    ]
  },
  form_items: [
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah"
      },
      id: "channel_form",
      name: "Channel Form",
      options: [
        {
          id: "flat",
          label: "Flat",
          value: "flat"
        },
        {
          id: "u_shape",
          label: "U Shape",
          value: "u_shape"
        },
        {
          id: "v_shape",
          label: "V Shape",
          value: "v_shape"
        },
        {
          id: "not_sure",
          label: "I\u2019m not sure",
          value: "cant_tell"
        }
      ],
      section: "what_you_see",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "The channel form is...",
      type: "choice",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah",
        finding: "Artificial channel bottom"
      },
      id: "bottom_type",
      name: "Bottom Type",
      options: [
        {
          id: "natural",
          label: "Natural",
          value: "absent"
        },
        {
          id: "artificial",
          label: "Artificial (concrete or stones with concrete)",
          value: "present"
        },
        {
          id: "not_sure",
          label: "I\u2019m not sure",
          value: "cant_tell"
        }
      ],
      section: "what_you_see",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "The bottom of the wet channel is\u2026",
      type: "choice",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: "artificial_bank",
      fhir: {
        category: "morophology",
        code: "artificial-bank",
        code_system: "sl"
      },
      id: "bank_type",
      name: "Bank Type",
      options: [
        {
          id: "natural",
          label: "Natural",
          value: "absent"
        },
        {
          id: "artificial",
          label: "Artificial (concrete or stones with concrete)",
          value: "present"
        },
        {
          id: "laid_stones",
          label: "Layed stones with no concrete",
          value: "absent"
        },
        {
          id: "not_sure",
          label: "I\u2019m not sure",
          value: "cant_tell"
        }
      ],
      section: "what_you_see",
      short_label: "artificial banks",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "The banks of the channel are\u2026",
      type: "choice",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah"
      },
      id: "habitats",
      name: "Habitats",
      options: [
        {
          id: "sand_banks",
          label: "Sand banks",
          value: "sand_banks"
        },
        {
          id: "sand_islands",
          label: "Sand islands",
          value: "sand_islands"
        },
        {
          id: "stone_deposits",
          label: "Stone deposits",
          value: "stone_deposits"
        },
        {
          id: "riffles",
          label: "Riffles, rapids, falls",
          value: "riffles"
        },
        {
          id: "aquatic_vegetation",
          label: "Aquatic vegetation",
          value: "aquatic_vegetation"
        }
      ],
      section: "what_you_see",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Are there any habitats present?",
      type: "multi",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah"
      },
      id: "natural_debris",
      name: "Natural Debris",
      options: [
        {
          id: "fallen_trees",
          label: "Fallen trees",
          value: "fallen_trees"
        },
        {
          id: "fallen_branches",
          label: "Fallen branches",
          value: "fallen_branches"
        },
        {
          id: "leaf_deposits",
          label: "Deposits of fallen leaves",
          value: "leaf_deposits"
        }
      ],
      section: "what_you_see",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Are there any natural debris present?",
      type: "multi",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "hydrology",
        code_system: "oah"
      },
      id: "water_flow",
      name: "Water Flow",
      options: [
        {
          id: "fast",
          label: "Fast (with waves or high velocity)",
          value: "fast"
        },
        {
          id: "slow",
          label: "Slow",
          value: "slow"
        },
        {
          id: "stagnant",
          label: "Stagnant/intermittent",
          value: "stagnant"
        },
        {
          id: "dry",
          label: "Dry",
          value: "dry"
        },
        {
          id: "not_sure",
          label: "I\u2019m not sure",
          value: "cant_tell"
        }
      ],
      section: "what_you_see",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "How is the water flowing",
      type: "choice",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "foam",
        code_system: "oah",
        finding: "Muddy water, foam or a changed colour"
      },
      id: "water_aspect",
      name: "Water Aspect",
      options: [
        {
          id: "clear",
          label: "Clear/transparent",
          value: "absent"
        },
        {
          id: "muddy",
          label: "Muddy/turbid",
          value: "present"
        },
        {
          id: "foam",
          label: "Has foam",
          value: "present"
        },
        {
          id: "colour",
          label: "Has colors/altered color",
          value: "present"
        },
        {
          id: "not_sure",
          label: "I\u2019m not sure",
          value: "cant_tell"
        }
      ],
      section: "water",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "How is the water?",
      type: "choice",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "hydrology",
        code_system: "oah",
        finding: "Water taken from the stream"
      },
      id: "water_withdrawal",
      name: "Water Withdrawal",
      section: "water",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Is there any kind of obvious water collection, use, removal from the stream?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah",
        finding: "Dam or other barrier across the stream"
      },
      id: "barriers",
      name: "Barriers",
      section: "water",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Do you see any dams or other transversal artificial barriers?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: "pipe_running",
      fhir: {
        category: "hydrology",
        code: "pipe-running",
        code_system: "sl"
      },
      id: "draining_pipes",
      name: "Draining Pipes",
      section: "water",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Are there pipes draining polluted water into the stream?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: "pipe_running",
      fhir: {
        category: "hydrology",
        code: "pipe-running",
        code_system: "sl"
      },
      id: "sewage_discharge",
      name: "Sewage discharge",
      section: "water",
      short_label: "a sewage discharge",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Is there any kind of water entry or discharge of sewage?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah",
        finding: "Construction or works in the stream"
      },
      id: "construction",
      name: "Construction",
      section: "water",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Is there any construction/works in stream?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "hydrology",
        code_system: "oah",
        unit: "m"
      },
      id: "water_height_m",
      name: "Water height",
      section: "water",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "What is the water height?",
      type: "number",
      unit: "m",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "LandUse",
        code_system: "oah",
        finding: "Left margin more than one third paved or built on"
      },
      id: "impervious_left",
      name: "Impervious Areas (Left)",
      section: "margins",
      short_label: "a paved left margin",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Is more than one third of the left margin covered by impervious areas (such as roads, sidewalks or buildings)?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "LandUse",
        code_system: "oah",
        finding: "Right margin more than one third paved or built on"
      },
      id: "impervious_right",
      name: "Impervious Areas (Right)",
      section: "margins",
      short_label: "a paved right margin",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Is more than one third of the right margin covered by impervious areas (such as roads, sidewalks or buildings)?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah",
        finding: "Left margin covered by vegetation"
      },
      id: "vegetation_left",
      name: "Vegetation (Left)",
      section: "margins",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Is the left margin covered by vegetation?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah",
        finding: "Right margin covered by vegetation"
      },
      id: "vegetation_right",
      name: "Vegetation (Right)",
      section: "margins",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Is the right margin covered by vegetation?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah"
      },
      id: "vegetation_type_left",
      name: "Vegetation Type (Left)",
      options: [
        {
          id: "herbs",
          label: "Herbs",
          value: "herbaceous"
        },
        {
          id: "shrubs",
          label: "Shrubs",
          value: "bushes"
        },
        {
          id: "trees",
          label: "Trees",
          value: "trees"
        },
        {
          id: "not_sure",
          label: "I\u2019m not sure",
          value: "cant_tell"
        }
      ],
      section: "margins",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Which vegetation is dominant (meaning that it covers more than 50%, or half) in the left margin (first 5 meters from the channel banktop)?",
      type: "choice",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah"
      },
      id: "vegetation_type_right",
      name: "Vegetation Type (Right)",
      options: [
        {
          id: "herbs",
          label: "Herbs",
          value: "herbaceous"
        },
        {
          id: "shrubs",
          label: "Shrubs",
          value: "bushes"
        },
        {
          id: "trees",
          label: "Trees",
          value: "trees"
        },
        {
          id: "not_sure",
          label: "I\u2019m not sure",
          value: "cant_tell"
        }
      ],
      section: "margins",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Which vegetation is dominant (meaning that it covers more than 50%, or half) in the right margin (first 5 meters from the channel bank/top)?",
      type: "choice",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: "invasive_plant",
      fhir: {
        category: "invasiveOrganisms",
        code: "invasive-plant",
        code_system: "sl"
      },
      id: "invasive_species",
      name: "Invasive Species",
      section: "margins",
      short_label: "invasive plants",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Do you see any non-native or invasive plant species?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      depends_on: {
        item: "invasive_species",
        value: "present"
      },
      feature: "invasive_plant",
      fhir: {
        category: "invasiveOrganisms",
        code: "invasive-plant",
        code_system: "sl"
      },
      id: "invasive_which",
      note: "The app offers free text here. We offer the regional list plus Not sure, so no free text is stored.",
      region_list: "invasive_plants",
      section: "margins",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Which ones?",
      type: "pick_region_list",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah",
        finding: "Recent cuts of vegetation on the banks"
      },
      id: "vegetation_cuts",
      name: "Vegetation Cuts",
      section: "margins",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Have there been recent cuts if vegetation (partial or total) on the banks (or just one of the banks) of the stream?",
      type: "yesno",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      allow_not_applicable: true,
      feature: null,
      fhir: null,
      id: "feelings",
      section: "feelings",
      sliders: [
        "joy",
        "serenity",
        "anger",
        "fear"
      ],
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Which feeling(s) best describe your experience?",
      type: "sliders",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    },
    {
      feature: null,
      fhir: null,
      id: "overall_rating",
      options: [
        {
          description: "The ecosystem components are there: riparian vegetation, natural channel, good water quality, biodiversity",
          id: "good",
          label: "Good quality",
          value: "good"
        },
        {
          description: "Some alterations, still biodiverse, with vegetation in the margins, water looks good...",
          id: "moderate",
          label: "Moderate quality",
          value: "moderate"
        },
        {
          description: "Highly modified / artificialized, loss of riparian vegetation, loss of habitats, polluted",
          id: "poor",
          label: "Poor quality",
          value: "poor"
        }
      ],
      rating_check: true,
      section: "overall",
      source: "app public bundle, c5a15e8ebf91, 2026-09-26",
      text: "Provide an overall assessment of the stream ecosystem health (choose one of the below possibilities)",
      type: "choice",
      verified_against_app: true,
      wording_source: "app_public_bundle"
    }
  ],
  rules: {
    features_in_order: [
      "artificial_bank",
      "dug_out_channel",
      "invasive_plant",
      "pipe_running"
    ],
    human_pass_min: 3,
    items_per_feature: 4,
    low_score_max_correct: 2,
    measure_for_feature: {
      artificial_bank: [
        "city_replant_margins",
        "city_remove_concrete"
      ],
      barriers: [
        "city_remove_barriers"
      ],
      dug_out_channel: [
        "city_reconnect_floodplain"
      ],
      pipe_running: [
        "city_fix_sewers"
      ]
    },
    pipe_items: [
      "draining_pipes",
      "sewage_discharge"
    ],
    pipe_observers_needed: 2,
    rating_issue_items: [
      "bank_type",
      "impervious_left",
      "impervious_right",
      "invasive_species",
      "sewage_discharge"
    ],
    same_spot_metres: 30,
    score_valid_days: 90,
    test_name_words: [
      "abc",
      "asdf",
      "bar",
      "baz",
      "delete",
      "demo",
      "dummy",
      "example",
      "foo",
      "ignore",
      "placeholder",
      "qwerty",
      "sample",
      "test",
      "testing",
      "todo",
      "xxx"
    ]
  },
  sentences: [
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "city",
      id: "city_replant_margins",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "OneAquaHealth Policy Brief (2026), page 9: rehabilitation of the riparian vegetation should prioritize a diverse corridor with native species, along both stream margins, free from unnecessary clearing. https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf",
      text: "Replant both margins with native trees and shrubs, and stop cutting them back."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "city",
      id: "city_fix_sewers",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "OneAquaHealth Policy Brief (2026), page 9: improvement of sewage systems and water treatments. https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf",
      text: "Find and fix leaking or wrongly connected sewers, and improve the treatment of waste water."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "city",
      id: "city_reconnect_floodplain",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "OneAquaHealth Policy Brief (2026), page 9: creation of space for natural flooding, removal of grey infrastructure from the margins and floodplains. https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf",
      text: "Give the stream room to flood: move walls, pavement and pipes back from the banks and the floodplain."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "city",
      id: "city_remove_barriers",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "OneAquaHealth Policy Brief (2026), page 9: removal of barriers to the longitudinal connectivity (dams, weirs, grids). https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf",
      text: "Remove dams, weirs and grids that stop water, sand and animals moving along the stream."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "city",
      id: "city_remove_concrete",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "OneAquaHealth Policy Brief (2026), page 9: removal of artificial materials (e.g. concrete); renaturalization of channels and margins with natural materials. https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf",
      text: "Take the concrete out of the channel and banks and rebuild them with natural materials."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "pet",
      id: "pet_keep_out_foam",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "CDC, Preventing Illness from Harmful Algal Blooms: keep pets and livestock away from water with signs of a bloom. https://www.cdc.gov/harmful-algal-blooms/prevention/index.html",
      text: "Keep dogs out of water that smells bad, looks discoloured, or has foam, scum or mats, and do not let them drink it."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "pet",
      id: "pet_rinse_after",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "CDC, Preventing Illness from Harmful Algal Blooms: rinse them off immediately; do not let them lick their fur before you rinse them. https://www.cdc.gov/harmful-algal-blooms/prevention/index.html",
      text: "If your dog goes in, rinse it with tap water straight away and do not let it lick its fur first."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "pet",
      id: "pet_bring_water",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "CDC, Preventing Illness from Harmful Algal Blooms: keep pets away from water with signs of a bloom. https://www.cdc.gov/harmful-algal-blooms/prevention/index.html",
      text: "Bring drinking water for your dog so it does not need to drink from the creek."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "pet",
      id: "pet_call_vet",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "CDC, Preventing Illness from Harmful Algal Blooms: if your pets seem sick after going in or near water, call a veterinarian right away. https://www.cdc.gov/harmful-algal-blooms/prevention/index.html",
      text: "If your dog seems sick after being in or near the water, call a vet right away."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "person",
      id: "person_avoid_foam_scum",
      note: "Checked against the source text by the planner on 2026-09-21.",
      source: "CDC, Preventing Illness from Harmful Algal Blooms: if water looks or smells bad, stay out. https://www.cdc.gov/harmful-algal-blooms/prevention/index.html",
      text: "Stay out of water that smells bad, looks discoloured, or has foam, scum or mats on the surface."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "person",
      id: "person_rinse_hands",
      note: "Both cited pages fetched again on 2026-09-21; the matching sentences are in source_quote.",
      source: "CDC, Preventing Illness from Harmful Algal Blooms: rinse off immediately after touching water; CDC, Healthy Swimming, Steps to Take: wash your hands before eating. https://www.cdc.gov/harmful-algal-blooms/prevention/index.html and https://www.cdc.gov/healthy-swimming/prevention/index.html",
      source_quote: "If you do go in or touch water that may have a harmful algal bloom, rinse off immediately after. Use tap water from a sink, shower, hose, or outdoor spigot. (CDC, Harmful Algal Blooms, Prevention.) Wash your hands for 20 seconds before eating, especially if you have been playing in or touching sand. (CDC, Healthy Swimming, Prevention.)",
      text: "If you touch creek water, rinse your hands with tap water afterwards, and wash them before you eat."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "person",
      id: "person_avoid_pipes",
      note: "Cited page fetched again on 2026-09-21; the matching sentence is in source_quote.",
      source: "CDC, Healthy Swimming, Steps to Take: stay out if you see pipes. https://www.cdc.gov/healthy-swimming/prevention/index.html",
      source_quote: "Stay out if you see pipes. Pipes draining into or around the water could be putting germs or harmful chemicals into the water.",
      text: "Stay out of the water right below a pipe that drains into the creek."
    },
    {
      approved: true,
      approved_by: "Alex Velazquez",
      approved_on: "2026-09-21",
      audience: "person",
      id: "person_report_dry_pipe",
      note: "The PDF was fetched again on 2026-09-21 and both sentences found by text search; they are in source_quote.",
      source: "EPA, Illicit Discharge Detection and Elimination guidance manual (2004), page 337 (72 hours dry) and page 6 (testing is needed before calling a flow polluted). https://www.epa.gov/sites/default/files/2015-11/documents/idde_manualwithappendices.pdf",
      source_quote: "While the traditional definition of dry weather has been 72 hours without rainfall, some communities have shortened this window to 48 hours to make sampling more practical. (page 337) Consequently, field testing and/or water quality sampling are needed to confirm whether pollutants are actually present in dry weather flow, in order to classify them as an illicit discharge. (chapter 1, page 6, PDF page 20)",
      text: "If a pipe is running after three dry days, note the place and the date and tell the city. It is worth testing."
    }
  ]
};

// src/core/types.ts
function scoreFor(observer, feature) {
  for (const s of observer.scores) if (s.feature === feature) return s;
  return null;
}
function parseDate(day) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(day);
  if (!m) throw new Error(`not a date: ${day}`);
  return Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
}
function isoDate(ms) {
  return new Date(ms).toISOString().slice(0, 10);
}
function daysBetween(earlier, later) {
  return Math.round((parseDate(later) - parseDate(earlier)) / 864e5);
}
function addDays(day, days) {
  return isoDate(parseDate(day) + days * 864e5);
}
function parseInstant(iso) {
  let text = iso.replace(/(\.\d{3})\d+/, "$1");
  if (!/([zZ]|[+-]\d{2}:?\d{2})$/.test(text)) text += "Z";
  const ms = Date.parse(text);
  if (Number.isNaN(ms)) throw new Error(`not an instant: ${iso}`);
  return ms;
}
function instant(iso) {
  const ms = typeof iso === "number" ? iso : parseInstant(iso);
  return new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");
}
function dayOf(iso) {
  return isoDate(parseInstant(iso));
}
function compareStrings(a, b) {
  return a < b ? -1 : a > b ? 1 : 0;
}

// src/core/labels.ts
var HUMAN_PASS_MIN = core_content_default.rules.human_pass_min;
var SCORE_VALID_DAYS = core_content_default.rules.score_valid_days;
var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
var KEY_SCORE = "label.score";
var KEY_EXPIRED = "label.expired";
function shortDate(day) {
  const d = new Date(parseDate(day));
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}`;
}
function expiredOn(score, today) {
  return daysBetween(score.tested_on, today) > SCORE_VALID_DAYS;
}
function fill(template, params) {
  return template.replace(/\{(\w+)\}/g, (whole, name) => name in params ? String(params[name]) : whole);
}
function observerLabel(score, featureName2, today, locale) {
  if (score === null) return { text: "", expired: false, passed: null };
  const tested = shortDate(score.tested_on);
  const params = { correct: score.correct, total: score.total, feature: featureName2, date: tested };
  if (expiredOn(score, today)) {
    return { text: fill(locale[KEY_EXPIRED], params), expired: true, passed: null };
  }
  return { text: fill(locale[KEY_SCORE], params), expired: false, passed: score.correct >= HUMAN_PASS_MIN };
}

// src/core/regions.ts
var CREEKS = core_content_default.creeks;
function creekBySlug(slug, creeks = CREEKS) {
  for (const c of creeks) if (c.slug === slug) return c;
  return null;
}
function reachOf(creek, slug) {
  for (const r of creek.reaches) if (r.slug === slug) return r;
  return null;
}
function inBox(box, lat, lon) {
  if (box === null) return false;
  const [south, west, north, east] = box;
  return south <= lat && lat <= north && west <= lon && lon <= east;
}
function creekBbox(creek) {
  const boxes = creek.reaches.map((r) => r.bbox).filter((b) => b !== null);
  if (boxes.length === 0) return null;
  return [
    Math.min(...boxes.map((b) => b[0])),
    Math.min(...boxes.map((b) => b[1])),
    Math.max(...boxes.map((b) => b[2])),
    Math.max(...boxes.map((b) => b[3]))
  ];
}
function reachesBelow(reach, creek) {
  const out = [];
  const seen = /* @__PURE__ */ new Set([reach.slug]);
  let current = reach;
  while (current.flows_into !== null) {
    const next = reachOf(creek, current.flows_into);
    if (next === null) throw new Error(`creek ${creek.slug}: reach ${current.flows_into} does not exist`);
    if (seen.has(next.slug)) throw new Error(`creek ${creek.slug}: reaches flow in a circle at ${next.slug}`);
    seen.add(next.slug);
    out.push(next);
    current = next;
  }
  return out;
}
var named = (text, name) => text.toLowerCase().includes(name.toLowerCase());
function reachByName(spot, creek) {
  for (const reach of creek.reaches) {
    if (named(spot.reach_name, reach.name) || named(spot.spot_name, reach.name)) return reach;
  }
  return null;
}
function placeSpot(spot, creeks = CREEKS) {
  const lat = spot.latitude;
  const lon = spot.longitude;
  if (lat !== null && lon !== null) {
    if (!spot.coarse) {
      for (const creek of creeks) for (const reach of creek.reaches) if (inBox(reach.bbox, lat, lon)) return { creek, reach };
    }
    for (const creek of creeks) if (inBox(creekBbox(creek), lat, lon)) return { creek, reach: reachByName(spot, creek) };
  }
  for (const creek of creeks) {
    if (named(spot.creek_name, creek.name) || named(spot.spot_name, creek.name)) return { creek, reach: reachByName(spot, creek) };
  }
  return null;
}

// src/core/act.ts
var FEATURES = core_content_default.rules.features_in_order;
var SCORE_VALID_DAYS2 = core_content_default.rules.score_valid_days;
var MEASURE_FOR_FEATURE = core_content_default.rules.measure_for_feature;
var FINDING_KEYS = /* @__PURE__ */ new Set([...FEATURES, ...Object.keys(MEASURE_FOR_FEATURE)]);
var DRY_PIPE_RULE = "dry_pipe";
var PIPE_OBSERVERS_NEEDED = core_content_default.rules.pipe_observers_needed;
var SAME_SPOT_METRES = core_content_default.rules.same_spot_metres;
var EARTH_RADIUS_M = 6371e3;
var TEST_NAME_WORDS = new Set(core_content_default.rules.test_name_words);
function present(value) {
  return value === "present" || value === "yes" || value === true || value === 1;
}
function passedFeature(v, feature, today) {
  if (!FEATURES.includes(feature)) return false;
  const score = scoreFor(v.observer, feature);
  if (score === null || daysBetween(score.tested_on, today) > SCORE_VALID_DAYS2) return false;
  return score.correct >= HUMAN_PASS_MIN;
}
function findingsFromVisits(visits, findingKeyFor) {
  const lookup = findingKeyFor ?? {};
  const seen = /* @__PURE__ */ new Map();
  for (const v of visits) {
    for (const [answerKey, value] of Object.entries(v.answers)) {
      const feature = lookup[answerKey] ?? answerKey;
      if (!FINDING_KEYS.has(feature) || !present(value)) continue;
      const key = `${v.spot.spot_id}\0${feature}`;
      const day = dayOf(v.answered_at);
      let row = seen.get(key);
      if (!row) {
        row = { spot_id: v.spot.spot_id, feature, observers: [], visit_ids: [], first_seen: day, last_seen: day, passed_observers: [] };
        seen.set(key, row);
      }
      const token = v.observer.contributor_token;
      if (!row.observers.includes(token)) row.observers.push(token);
      if (!row.passed_observers.includes(token) && passedFeature(v, feature, day)) row.passed_observers.push(token);
      if (!row.visit_ids.includes(v.visit_id)) row.visit_ids.push(v.visit_id);
      if (day < row.first_seen) row.first_seen = day;
      if (day > row.last_seen) row.last_seen = day;
    }
  }
  return [...seen.values()].sort((a, b) => compareStrings(a.spot_id, b.spot_id) || compareStrings(a.feature, b.feature));
}
function needsFromFindings(findings, sentences) {
  const approved = /* @__PURE__ */ new Map();
  for (const s of sentences) if (s.approved === true && s.audience === "city") approved.set(String(s.id), s);
  const wanted = /* @__PURE__ */ new Map();
  for (const f of findings) {
    for (const sentenceId of MEASURE_FOR_FEATURE[f.feature] ?? []) {
      if (!approved.has(sentenceId)) continue;
      let row = wanted.get(sentenceId);
      if (!row) {
        row = { because: [], visits: [] };
        wanted.set(sentenceId, row);
      }
      if (!row.because.includes(f.feature)) row.because.push(f.feature);
      row.visits.push(...f.visit_ids);
    }
  }
  return [...wanted.entries()].sort(([a], [b]) => compareStrings(a, b)).map(([sentenceId, row]) => {
    const s = approved.get(sentenceId);
    return {
      sentence_id: sentenceId,
      text: String(s.text ?? ""),
      source: String(s.source ?? ""),
      because: row.because,
      visit_ids: [...new Set(row.visits)]
    };
  });
}
function dryPipeDays(v) {
  for (const c of v.checks) {
    if (c.rule_id !== DRY_PIPE_RULE || !c.asked || c.answer !== "yes") continue;
    const days = c.detail.days;
    if (typeof days === "number" && Number.isInteger(days) && days >= 1) return days;
  }
  return null;
}
function pipesWorthTesting(visits, today) {
  const bySpot = /* @__PURE__ */ new Map();
  for (const v of visits) {
    const days = dryPipeDays(v);
    if (days === null || !passedFeature(v, "pipe_running", today)) continue;
    const day = dayOf(v.answered_at);
    let row = bySpot.get(v.spot.spot_id);
    if (!row) {
      row = { spot_id: v.spot.spot_id, spot_name: v.spot.spot_name, observers: [], visit_ids: [], dry_days: [], last_seen: day };
      bySpot.set(v.spot.spot_id, row);
    }
    if (!row.observers.includes(v.observer.contributor_token)) row.observers.push(v.observer.contributor_token);
    row.visit_ids.push(v.visit_id);
    row.dry_days.push(days);
    if (day > row.last_seen) row.last_seen = day;
  }
  return [...bySpot.values()].sort((a, b) => compareStrings(a.spot_id, b.spot_id)).filter((row) => row.observers.length >= PIPE_OBSERVERS_NEEDED);
}
function metresBetween(lat1, lon1, lat2, lon2) {
  const rad = (d) => d * Math.PI / 180;
  const p1 = rad(lat1);
  const p2 = rad(lat2);
  const dp = rad(lat2 - lat1);
  const dl = rad(lon2 - lon1);
  const a = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(a)));
}
function nearestSpot(latitude, longitude, spots, within = SAME_SPOT_METRES) {
  let best = null;
  for (const s of spots) {
    if (s.latitude === null || s.longitude === null) continue;
    const d = metresBetween(latitude, longitude, s.latitude, s.longitude);
    if (d <= within && (best === null || d < best.metres)) best = { spot: s, metres: d };
  }
  return best;
}
function looksLikeATestName(name) {
  const cleaned = Array.from(name.toLowerCase(), (ch) => /[\p{L}\p{N}]/u.test(ch) || /\s/.test(ch) ? ch : " ").join("");
  const words = cleaned.split(/\s+/).filter((w) => w.length > 0);
  if (words.length === 0) return true;
  if (words.some((w) => TEST_NAME_WORDS.has(w))) return true;
  return !/\p{L}/u.test(name);
}
function downstreamNote(finding2, featureName2, reachSlugs) {
  const n = finding2.observers.length;
  const people = n === 1 ? "one person" : `${n} people`;
  const line = `Upstream of here, ${people} reported ${featureName2} on ${shortDate(finding2.last_seen)}.`;
  return Object.fromEntries(reachSlugs.map((slug) => [slug, line]));
}
function notesBelow(findings, reachOfSpot, creek, labels) {
  const out = [];
  for (const f of findings) {
    const reach = reachOfSpot[f.spot_id];
    if (!reach) continue;
    if (!creek.reaches.some((r) => r.slug === reach.slug)) continue;
    const below = reachesBelow(reach, creek);
    if (below.length === 0) continue;
    const label = labels[f.feature] ?? f.feature.replace(/_/g, " ");
    const lines = downstreamNote(f, label, below.map((r) => r.slug));
    for (const r of below) {
      out.push({
        reach_slug: r.slug,
        reach_name: r.name,
        from_reach_slug: reach.slug,
        from_reach_name: reach.name,
        feature: f.feature,
        line: lines[r.slug],
        observers: f.observers.length,
        visit_ids: f.visit_ids
      });
    }
  }
  return out;
}

// src/core/assist.ts
var ANSWERS = ["yes", "no", "cant_tell"];
var SIDES = ["present", "absent"];
var QUESTION = "The checker noticed something here. Look again?";
var AssistError = class extends Error {
};
var sideAnswer = (side) => side === "present" ? "yes" : "no";
var isMapping = (v) => typeof v === "object" && v !== null && !Array.isArray(v);
function flagSide(flags, itemId) {
  if (!isMapping(flags) || typeof itemId !== "string") return null;
  const items = flags.items;
  if (!Array.isArray(items)) return null;
  for (const entry3 of items) {
    if (!isMapping(entry3) || entry3.item_id !== itemId) continue;
    const flag = entry3.flag;
    if (isMapping(flag) && typeof flag.points_to === "string" && SIDES.includes(flag.points_to)) return flag.points_to;
    return null;
  }
  return null;
}
function questionNeeded(arm, side, first) {
  if (arm !== "assisted" || typeof side !== "string" || !SIDES.includes(side)) return false;
  if (typeof first !== "string" || !ANSWERS.includes(first)) return false;
  return first !== sideAnswer(side);
}
var blank = (v) => v === null || v === void 0 || v === "";
function settle(first, asked, choice2 = null, changedTo = null) {
  if (typeof first !== "string" || !ANSWERS.includes(first)) throw new AssistError("We do not know that answer.");
  if (!asked) {
    if (!blank(choice2) || !blank(changedTo)) throw new AssistError("No question was asked for this photo, so there is nothing to choose.");
    return { first_answer: first, final_answer: first, question_shown: false, choice: "" };
  }
  if (choice2 === "keep") {
    if (!blank(changedTo) && changedTo !== first) throw new AssistError("Keep keeps the first answer.");
    return { first_answer: first, final_answer: first, question_shown: true, choice: "keep" };
  }
  if (choice2 === "change") {
    if (typeof changedTo !== "string" || !ANSWERS.includes(changedTo)) throw new AssistError("We do not know that answer.");
    return { first_answer: first, final_answer: changedTo, question_shown: true, choice: "change" };
  }
  throw new AssistError("Choose Keep or Change.");
}

// src/core/pyround.ts
function pyRound(x, digits) {
  if (!Number.isFinite(x)) return x;
  const sign = x < 0 ? -1 : 1;
  const magnitude = Math.abs(x);
  const extra = 30;
  const long = magnitude.toFixed(digits + extra);
  const [whole, fraction = ""] = long.split(".");
  const kept = fraction.slice(0, digits);
  const rest = fraction.slice(digits);
  const tie = rest === "5" + "0".repeat(extra - 1);
  let result;
  if (!tie) {
    result = Number(magnitude.toFixed(digits));
  } else {
    const keptDigits = whole + kept;
    const last = Number(keptDigits[keptDigits.length - 1]);
    let asInteger = BigInt(keptDigits);
    if (last % 2 === 1) asInteger += 1n;
    const text = asInteger.toString().padStart(digits + 1, "0");
    const cut = text.length - digits;
    result = Number(digits === 0 ? text : `${text.slice(0, cut)}.${text.slice(cut)}`);
  }
  return sign * result === 0 ? 0 : sign * result;
}

// src/core/sha256.ts
var K = new Uint32Array([
  1116352408,
  1899447441,
  3049323471,
  3921009573,
  961987163,
  1508970993,
  2453635748,
  2870763221,
  3624381080,
  310598401,
  607225278,
  1426881987,
  1925078388,
  2162078206,
  2614888103,
  3248222580,
  3835390401,
  4022224774,
  264347078,
  604807628,
  770255983,
  1249150122,
  1555081692,
  1996064986,
  2554220882,
  2821834349,
  2952996808,
  3210313671,
  3336571891,
  3584528711,
  113926993,
  338241895,
  666307205,
  773529912,
  1294757372,
  1396182291,
  1695183700,
  1986661051,
  2177026350,
  2456956037,
  2730485921,
  2820302411,
  3259730800,
  3345764771,
  3516065817,
  3600352804,
  4094571909,
  275423344,
  430227734,
  506948616,
  659060556,
  883997877,
  958139571,
  1322822218,
  1537002063,
  1747873779,
  1955562222,
  2024104815,
  2227730452,
  2361852424,
  2428436474,
  2756734187,
  3204031479,
  3329325298
]);
var rotr = (x, n) => x >>> n | x << 32 - n;
function sha256Bytes(input) {
  const data = typeof input === "string" ? new TextEncoder().encode(input) : input;
  const bitLength = data.length * 8;
  const padded = new Uint8Array(data.length + 9 + 63 >> 6 << 6);
  padded.set(data);
  padded[data.length] = 128;
  const view = new DataView(padded.buffer);
  view.setUint32(padded.length - 8, Math.floor(bitLength / 4294967296), false);
  view.setUint32(padded.length - 4, bitLength >>> 0, false);
  const h = new Uint32Array([1779033703, 3144134277, 1013904242, 2773480762, 1359893119, 2600822924, 528734635, 1541459225]);
  const w = new Uint32Array(64);
  for (let offset = 0; offset < padded.length; offset += 64) {
    for (let i = 0; i < 16; i++) w[i] = view.getUint32(offset + i * 4, false);
    for (let i = 16; i < 64; i++) {
      const s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ w[i - 15] >>> 3;
      const s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ w[i - 2] >>> 10;
      w[i] = w[i - 16] + s0 + w[i - 7] + s1 >>> 0;
    }
    let [a, b, c, d, e, f, g, hh] = h;
    for (let i = 0; i < 64; i++) {
      const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      const ch = e & f ^ ~e & g;
      const t1 = hh + S1 + ch + K[i] + w[i] >>> 0;
      const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      const maj = a & b ^ a & c ^ b & c;
      const t2 = S0 + maj >>> 0;
      hh = g;
      g = f;
      f = e;
      e = d + t1 >>> 0;
      d = c;
      c = b;
      b = a;
      a = t1 + t2 >>> 0;
    }
    h[0] = h[0] + a >>> 0;
    h[1] = h[1] + b >>> 0;
    h[2] = h[2] + c >>> 0;
    h[3] = h[3] + d >>> 0;
    h[4] = h[4] + e >>> 0;
    h[5] = h[5] + f >>> 0;
    h[6] = h[6] + g >>> 0;
    h[7] = h[7] + hh >>> 0;
  }
  const out = new Uint8Array(32);
  const outView = new DataView(out.buffer);
  for (let i = 0; i < 8; i++) outView.setUint32(i * 4, h[i], false);
  return out;
}
function sha256Hex(input) {
  return Array.from(sha256Bytes(input), (b) => b.toString(16).padStart(2, "0")).join("");
}

// src/core/fhir_emit.ts
var FHIR = core_content_default.fhir;
var REPO_URL = FHIR.repo_url;
var FHIR_BASE = `${REPO_URL}/fhir`;
var SL_SYSTEM = FHIR.sl_system;
var OAH_SYSTEM = FHIR.oah_system;
var OAH_LOCATION_PROFILE = FHIR.oah_location_profile;
var OAH_OBSERVATION_PROFILE = FHIR.oah_observation_profile;
var UCUM_SYSTEM = "http://unitsofmeasure.org";
var SNOMED_SYSTEM = "http://snomed.info/sct";
var PROVENANCE_TYPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/provenance-participant-type";
var QUESTIONNAIRE_TEST_URL = `${FHIR_BASE}/Questionnaire/sl-questionnaire-test`;
var QUESTIONNAIRE_CHECK_URL = `${FHIR_BASE}/Questionnaire/sl-questionnaire-check`;
var ID_SYSTEM_ORG = `${FHIR_BASE}/org`;
var ID_SYSTEM_DEVICE = `${FHIR_BASE}/device`;
var ID_SYSTEM_LOCATION = `${FHIR_BASE}/location-id`;
var ID_SYSTEM_CONTRIBUTOR = `${FHIR_BASE}/contributor-token`;
var ID_SYSTEM_QR = `${FHIR_BASE}/qr`;
var ID_SYSTEM_OBSERVATION = `${FHIR_BASE}/observation`;
var ORG_ID = "sl-org";
var DEVICE_ID = "sl-device";
var SL_DISPLAYS = FHIR.sl_displays;
var OAH_DISPLAYS = FHIR.oah_displays;
var UCUM_DISPLAYS = FHIR.ucum_displays;
var FEATURES2 = core_content_default.rules.features_in_order;
var SCORE_VALID_DAYS3 = core_content_default.rules.score_valid_days;
var FORM_ITEMS = core_content_default.form_items;
var FhirEmitError = class extends Error {
};
function fhirId(...parts) {
  const raw = parts.join("-");
  const cleaned = raw.replace(/[^A-Za-z0-9.-]/g, "-").replace(/^-+|-+$/g, "");
  if (cleaned.length <= 64) return cleaned;
  return `${cleaned.slice(0, 51)}-${sha256Hex(raw).slice(0, 12)}`;
}
function coding(system, code, display) {
  const out = { system, code };
  if (display !== void 0) out.display = display;
  return out;
}
function slCoding(code) {
  if (!(code in SL_DISPLAYS)) throw new FhirEmitError(`no Second Look display for ${code}`);
  return coding(SL_SYSTEM, code, SL_DISPLAYS[code]);
}
function oahCoding(code) {
  if (!(code in OAH_DISPLAYS)) throw new FhirEmitError(`no OneAquaHealth display for ${code}`);
  return coding(OAH_SYSTEM, code, OAH_DISPLAYS[code]);
}
function concept(c, text) {
  const out = { coding: [c] };
  if (text) out.text = text;
  return out;
}
var ref = (type, id) => ({ reference: `${type}/${id}` });
var identifier = (system, value) => ({ system, value });
function escapeXml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function narrative(text, lang = null) {
  const attrs = lang ? ` lang="${lang}" xml:lang="${lang}"` : "";
  return { status: "generated", div: `<div xmlns="http://www.w3.org/1999/xhtml"${attrs}><p>${escapeXml(text)}</p></div>` };
}
function pyFloat(value) {
  if (Number.isInteger(value) && Math.abs(value) < 1e16) return `${value}.0`;
  return String(value);
}
function fullUrl(resource) {
  return `${FHIR_BASE}/${resource.resourceType}/${resource.id}`;
}
var entry = (resource) => ({ fullUrl: fullUrl(resource), resource });
function codeForAnswer(value) {
  if (value === "cant_tell") return slCoding("cant-tell");
  if (value in OAH_DISPLAYS) return oahCoding(value);
  const hyphenated = value.replace(/_/g, "-");
  if (hyphenated in SL_DISPLAYS) return slCoding(hyphenated);
  return null;
}
function valueConcept(value) {
  const c = codeForAnswer(value);
  return c ? concept(c) : { text: value };
}
function itemCode(item) {
  const fhir = item.fhir;
  if (fhir.code_system === "sl") return slCoding(fhir.code);
  if (fhir.code_system === "oah") return oahCoding(fhir.code);
  throw new FhirEmitError(`item ${item.id}: unknown code_system ${JSON.stringify(fhir.code_system)}`);
}
function itemCategory(item) {
  return oahCoding(item.fhir.category || item.fhir.code);
}
function finding(item) {
  const fhir = item.fhir;
  if (fhir.code_system === "sl") return String(slCoding(fhir.code).display);
  const phrase = fhir.finding;
  return typeof phrase === "string" ? phrase.trim() : "";
}
function itemLabel(item) {
  const name = String(item.name || item.text || item.id);
  const found = finding(item);
  return found ? `${found} (${name})` : name;
}
function valueWords(value) {
  const c = typeof value === "string" ? codeForAnswer(value) : null;
  return c ? String(c.display) : String(value).replace(/_/g, " ");
}
function quantity(value, unit) {
  return { value, unit: UCUM_DISPLAYS[unit] ?? unit, system: UCUM_SYSTEM, code: unit };
}
function organization() {
  return {
    resourceType: "Organization",
    id: ORG_ID,
    text: narrative("Second Look project. Issues the observer test and keeps the record."),
    identifier: [identifier(ID_SYSTEM_ORG, "second-look")],
    name: "Second Look project",
    active: true
  };
}
function device(version) {
  return {
    resourceType: "Device",
    id: DEVICE_ID,
    text: narrative(`Second Look web app, version ${version}. Assembled this record.`),
    identifier: [identifier(ID_SYSTEM_DEVICE, "second-look-web")],
    status: "active",
    type: concept(slCoding("software")),
    deviceName: [{ name: "Second Look web app", type: "user-friendly-name" }],
    version: [{ value: version }]
  };
}
function location(opts) {
  const out = {
    resourceType: "Location",
    id: opts.locationId,
    meta: { profile: [OAH_LOCATION_PROFILE] },
    text: narrative(`${opts.name}. A ${opts.kind} used in Second Look creek checks.`),
    identifier: [identifier(ID_SYSTEM_LOCATION, opts.identifier)],
    name: opts.name,
    mode: "instance",
    type: [concept(coding(SNOMED_SYSTEM, "420531007", "River"))]
  };
  if (opts.description) out.description = opts.description;
  if (opts.position) out.position = { latitude: opts.position[0], longitude: opts.position[1] };
  if (opts.partOf) out.partOf = ref("Location", opts.partOf);
  return out;
}
function locations(visit) {
  const spot = visit.spot;
  const creekId = fhirId("sl-loc", spot.creek_id);
  const reachId = fhirId("sl-loc", spot.reach_id);
  const spotId = fhirId("sl-loc", spot.spot_id);
  let position = null;
  if (spot.latitude !== null && spot.longitude !== null) {
    const digits = spot.coarse ? 2 : 5;
    position = [pyRound(spot.latitude, digits), pyRound(spot.longitude, digits)];
  }
  const creek = location({ locationId: creekId, identifier: spot.creek_id, name: spot.creek_name, kind: "creek" });
  const reach = location({ locationId: reachId, identifier: spot.reach_id, name: spot.reach_name, kind: "reach", partOf: creekId });
  const point = location({
    locationId: spotId,
    identifier: spot.spot_id,
    name: spot.spot_name,
    kind: "spot",
    partOf: reachId,
    position,
    description: position && spot.coarse ? "Coarse position, about 1 km." : null
  });
  return [creek, reach, point];
}
function practitionerId(contributorToken) {
  return `sl-practitioner-${sha256Hex(contributorToken).slice(0, 12)}`;
}
function testedOn(visit, sitting) {
  const scores = sitting ? sitting.scores : visit.observer.scores;
  if (scores.length === 0) return null;
  return scores.map((s) => s.tested_on).reduce((a, b) => b > a ? b : a);
}
function practitioner(visit, tested) {
  const token = visit.observer.contributor_token;
  let words = "Volunteer observer, known only by a random contributor token.";
  const qualification = [];
  if (tested !== null) {
    const validUntil = addDays(tested, SCORE_VALID_DAYS3);
    words += ` Took the Second Look test on ${tested}.`;
    words += ` The score counts until ${validUntil}.`;
    qualification.push({
      code: concept(slCoding("second-look-test")),
      period: { start: tested, end: validUntil },
      issuer: ref("Organization", ORG_ID)
    });
  }
  const out = {
    resourceType: "Practitioner",
    id: practitionerId(token),
    text: narrative(words),
    identifier: [identifier(ID_SYSTEM_CONTRIBUTOR, practitionerId(token))],
    active: true
  };
  if (qualification.length) out.qualification = qualification;
  return out;
}
function testResponse(sitting, pid) {
  const byFeature = new Map(sitting.scores.map((s) => [s.feature, s]));
  const items = [];
  const words = [];
  for (const feature of FEATURES2) {
    const score = byFeature.get(feature);
    if (!score) continue;
    items.push({ linkId: feature, item: [{ linkId: `${feature}.score`, answer: [{ valueInteger: score.correct }] }] });
    words.push(`${feature.replace(/_/g, " ")} ${score.correct} of ${score.total}`);
  }
  return {
    resourceType: "QuestionnaireResponse",
    id: fhirId("sl-qr-test", sitting.sitting_id),
    text: narrative(`Observer test sitting, scored by code: ${words.join(", ")}.`),
    identifier: identifier(ID_SYSTEM_QR, sitting.sitting_id),
    questionnaire: QUESTIONNAIRE_TEST_URL,
    status: "completed",
    authored: instant(sitting.completed_at),
    author: ref("Practitioner", pid),
    item: items
  };
}
function qrAnswers(value) {
  if (typeof value === "boolean") return [{ valueBoolean: value }];
  if (typeof value === "number") return [{ valueDecimal: value }];
  if (typeof value === "string") {
    const c = codeForAnswer(value);
    return c ? [{ valueCoding: c }] : [{ valueString: value }];
  }
  const out = [];
  for (const element of value) out.push(...qrAnswers(element));
  return out;
}
function visitResponse(visit, pid, items) {
  const qrItems = [];
  for (const item of items) {
    if (!(item.id in visit.answers) || item.type === "sliders") continue;
    const answers = qrAnswers(visit.answers[item.id]);
    if (answers.length) qrItems.push({ linkId: item.id, answer: answers });
  }
  return {
    resourceType: "QuestionnaireResponse",
    id: fhirId("sl-qr-visit", visit.visit_id),
    // The language the volunteer saw the questions in (UPDATE_32 section 2).
    language: visit.language ?? "en",
    text: narrative(
      `Creek check at ${visit.spot.spot_name} on ${instant(visit.answered_at)}, ${qrItems.length} items answered.` + ((visit.language ?? "en") === "en" ? "" : ` The questions were shown in language ${visit.language}.`),
      "en"
    ),
    identifier: identifier(ID_SYSTEM_QR, visit.visit_id),
    questionnaire: QUESTIONNAIRE_CHECK_URL,
    status: "completed",
    authored: instant(visit.answered_at),
    author: ref("Practitioner", pid),
    item: qrItems
  };
}
function components(item, values) {
  const out = [];
  if (item.type === "multi") {
    for (const value of values) {
      const c = codeForAnswer(value);
      const code = c ? concept(c) : concept(itemCode(item), value);
      out.push({ code, valueCodeableConcept: concept(oahCoding("present")) });
    }
    return out;
  }
  for (const value of values) out.push({ code: concept(itemCode(item)), valueCodeableConcept: valueConcept(value) });
  return out;
}
function observation(visit, item, value, pid, spotLocationId, visitQrId, score) {
  const fhir = item.fhir;
  const label = itemLabel(item);
  let words = `${label} at ${visit.spot.spot_name}: `;
  let valuePart;
  if (typeof value === "boolean") {
    throw new FhirEmitError(`item ${item.id}: boolean answers are not allowed, use present/absent`);
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return null;
    valuePart = { component: components(item, value) };
    words += value.map((v) => valueWords(v)).join("; ") + ".";
  } else if (typeof value === "number") {
    const unit = fhir.unit || item.unit;
    if (!unit) throw new FhirEmitError(`item ${item.id}: a number needs a UCUM unit in form.yaml`);
    valuePart = { valueQuantity: quantity(value, unit) };
    words += `${pyFloat(value)} ${UCUM_DISPLAYS[unit] ?? unit}.`;
  } else {
    valuePart = { valueCodeableConcept: valueConcept(value) };
    words += valueWords(value) + ".";
  }
  if (score !== null) {
    words += ` The observer scored ${score.correct} of ${score.total} on this feature, tested ${score.tested_on}.`;
  }
  const out = {
    resourceType: "Observation",
    id: fhirId("sl-obs", visit.visit_id, item.id),
    meta: { profile: [OAH_OBSERVATION_PROFILE] },
    text: narrative(words),
    identifier: [identifier(ID_SYSTEM_OBSERVATION, `${visit.visit_id}-${item.id}`)],
    status: "final",
    category: [concept(itemCategory(item))],
    code: concept(itemCode(item), label),
    subject: ref("Location", spotLocationId),
    effectiveDateTime: instant(visit.answered_at),
    performer: [ref("Practitioner", pid)],
    ...valuePart,
    derivedFrom: [ref("QuestionnaireResponse", visitQrId)]
  };
  return out;
}
var RATING_ITEM = "overall_rating";
function ratingChange(visit, items) {
  const item = items.find((i) => i.id === RATING_ITEM);
  const given = visit.answers[RATING_ITEM];
  if (item === void 0 || typeof given !== "string") return null;
  const first = visit.first_rating || given;
  const kept = visit.final_rating || given;
  return first !== kept ? { first, kept, item } : null;
}
function ratingObservation(visit, item, first, kept, pid, spotLocationId, visitQrId) {
  if (item.fhir) throw new FhirEmitError(`item ${item.id}: a changed rating needs the item mapped to none`);
  const label = String(slCoding("overall-rating").display);
  const words = `${label} at ${visit.spot.spot_name}: ${valueWords(kept)}. The first answer was ${valueWords(first)}. On the rating check the volunteer changed it to ${valueWords(kept)}.`;
  return {
    resourceType: "Observation",
    id: fhirId("sl-obs", visit.visit_id, item.id),
    meta: { profile: [OAH_OBSERVATION_PROFILE] },
    text: narrative(words),
    identifier: [identifier(ID_SYSTEM_OBSERVATION, `${visit.visit_id}-${item.id}`)],
    status: "final",
    code: concept(slCoding("overall-rating"), label),
    subject: ref("Location", spotLocationId),
    effectiveDateTime: instant(visit.answered_at),
    performer: [ref("Practitioner", pid)],
    valueCodeableConcept: valueConcept(kept),
    component: [{ code: concept(slCoding("first-rating")), valueCodeableConcept: valueConcept(first) }],
    derivedFrom: [ref("QuestionnaireResponse", visitQrId)]
  };
}
function provenance(visit, observations2, pid, visitQrId, testQrId, emittedAt) {
  const entities = [{ role: "source", what: ref("QuestionnaireResponse", visitQrId) }];
  let sources = "The source is the visit.";
  if (testQrId) {
    entities.push({ role: "source", what: ref("QuestionnaireResponse", testQrId) });
    sources = "The sources are the visit and the observer test sitting.";
  }
  return {
    resourceType: "Provenance",
    id: fhirId("sl-provenance", visit.visit_id),
    text: narrative(
      `${observations2.length} observations from one creek check, answered by the volunteer and assembled by the Second Look software. ${sources}`
    ),
    target: observations2.map((o) => ref("Observation", String(o.id))),
    recorded: instant(emittedAt),
    agent: [
      { type: concept(coding(PROVENANCE_TYPE_SYSTEM, "author")), who: ref("Practitioner", pid) },
      { type: concept(coding(PROVENANCE_TYPE_SYSTEM, "assembler")), who: ref("Device", DEVICE_ID) }
    ],
    entity: entities
  };
}
function emitVisit(visit, testSitting, emittedAt, items = FORM_ITEMS) {
  const change = ratingChange(visit, items);
  if (change !== null) visit = { ...visit, answers: { ...visit.answers, [RATING_ITEM]: change.kept } };
  const [creek, reach, spot] = locations(visit);
  const tested = testedOn(visit, testSitting);
  const person = practitioner(visit, tested);
  const pid = String(person.id);
  const testQr = testSitting ? testResponse(testSitting, pid) : null;
  const visitQr = visitResponse(visit, pid, items);
  const scores = /* @__PURE__ */ new Map();
  for (const s of testSitting ? testSitting.scores : visit.observer.scores) scores.set(s.feature, s);
  const observations2 = [];
  for (const item of items) {
    if (!item.fhir || !(item.id in visit.answers)) continue;
    const obs = observation(visit, item, visit.answers[item.id], pid, String(spot.id), String(visitQr.id), scores.get(String(item.feature ?? "")) ?? null);
    if (obs !== null) observations2.push(obs);
  }
  if (change !== null) observations2.push(ratingObservation(visit, change.item, change.first, change.kept, pid, String(spot.id), String(visitQr.id)));
  const prov = provenance(visit, observations2, pid, String(visitQr.id), testQr ? String(testQr.id) : null, emittedAt);
  const resources2 = [organization(), device(visit.software_version), creek, reach, spot, person];
  if (testQr) resources2.push(testQr);
  resources2.push(visitQr, ...observations2, prov);
  return {
    resourceType: "Bundle",
    id: fhirId("sl-visit", visit.visit_id),
    type: "collection",
    timestamp: instant(emittedAt),
    entry: resources2.map(entry)
  };
}
function checkBundle(bundle) {
  const problems = [];
  if (bundle.resourceType !== "Bundle") return ["not a Bundle"];
  const entries = bundle.entry ?? [];
  const seenUrls = /* @__PURE__ */ new Set();
  entries.forEach((e, i) => {
    const url = String(e.fullUrl ?? "");
    const r = e.resource ?? {};
    if (url && seenUrls.has(url)) problems.push(`entry[${i}] ${String(r.resourceType)}/${r.id ?? e.fullUrl ?? "?"}: fullUrl ${url} appears twice`);
    seenUrls.add(url);
  });
  const keys = /* @__PURE__ */ new Set();
  for (const e of entries) {
    const r = e.resource ?? {};
    if (bundle.type === "transaction") keys.add(String(e.fullUrl ?? ""));
    else {
      keys.add(`${r.resourceType}/${r.id}`);
      keys.add(String(e.fullUrl ?? ""));
    }
  }
  const walk = (node, path) => {
    if (Array.isArray(node)) node.forEach((v, i) => walk(v, `${path}[${i}]`));
    else if (node && typeof node === "object") {
      for (const [key, value] of Object.entries(node)) {
        if (key === "reference" && typeof value === "string") {
          if (!keys.has(value)) problems.push(`${path}: reference ${value} does not resolve in the Bundle`);
        } else walk(value, `${path}.${key}`);
      }
    }
  };
  const observations2 = [];
  const provenances = [];
  entries.forEach((e, i) => {
    const r = e.resource ?? {};
    const rtype = String(r.resourceType);
    const label = `entry[${i}] ${rtype}/${r.id ?? e.fullUrl ?? "?"}`;
    walk(r, label);
    if (rtype === "Observation") {
      observations2.push(bundle.type !== "transaction" ? `Observation/${r.id}` : String(e.fullUrl ?? ""));
      for (const field of ["subject", "performer", "effectiveDateTime"]) if (!(field in r)) problems.push(`${label}: missing ${field}`);
      const profiles = r.meta?.profile ?? [];
      if (!profiles.includes(OAH_OBSERVATION_PROFILE)) problems.push(`${label}: missing the OneAquaHealth indicator profile`);
      if (!Object.keys(r).some((k) => k.startsWith("value")) && !r.component) problems.push(`${label}: no value and no component`);
    } else if (rtype === "Provenance") provenances.push(r);
    else if (!["Organization", "Device", "Location", "Practitioner", "QuestionnaireResponse"].includes(rtype)) {
      problems.push(`${label}: unexpected resource type`);
    }
    if (rtype !== "Bundle" && !("text" in r)) problems.push(`${label}: no narrative`);
  });
  if (provenances.length !== 1) problems.push(`expected one Provenance, found ${provenances.length}`);
  else {
    const targets = new Set((provenances[0].target ?? []).map((t) => t.reference));
    for (const obs of observations2) if (!targets.has(obs)) problems.push(`Provenance does not target ${obs}`);
  }
  return problems;
}

// src/core/fhir_referral.ts
var OAH_SPECIMEN_PROFILE = "http://hl7.eu/fhir/ig/oah/StructureDefinition/specimen-oah";
var OBSERVATION_CATEGORY_SYSTEM = "http://terminology.hl7.org/CodeSystem/observation-category";
var SNOMED_SYSTEM2 = "http://snomed.info/sct";
var UCUM_SYSTEM2 = "http://unitsofmeasure.org";
var ID_SYSTEM_REFERRAL = `${FHIR_BASE}/referral`;
var ID_SYSTEM_EXAMPLE = `${FHIR_BASE}/example`;
var EXAMPLE_TAG_CODE = "example";
var EXAMPLE_WORD = "EXAMPLE";
var EXAMPLE_LAB_ID = "sl-example-lab";
var EXAMPLE_LAB_ROLE_ID = "sl-example-lab-role";
var SPECIMEN_TYPE_CODE = "11713004";
var SPECIMEN_TYPE_DISPLAY = "Water";
var SAMPLE_ML = 500;
var PIPE_ITEMS = core_content_default.rules.pipe_items;
var UCUM_DISPLAYS2 = core_content_default.fhir.ucum_displays;
var EXAMPLE_PANEL = [
  ["lab-enterobacteriaceae-share", "quantity", 1.8, "%"],
  ["lab-hf183", "coded", "absent", null],
  ["lab-ecoli-cfu", "quantity", 120, "[CFU]/dL"]
];
var ReferralError = class extends Error {
};
var ref2 = (type, id) => ({ reference: `${type}/${id}` });
var identifier2 = (system, value) => ({ system, value });
var concept2 = (c, text) => text ? { coding: [c], text } : { coding: [c] };
var narrative2 = (text) => ({ status: "generated", div: `<div xmlns="http://www.w3.org/1999/xhtml"><p>${escapeXml(text)}</p></div>` });
var entry2 = (r) => ({ fullUrl: `${FHIR_BASE}/${r.resourceType}/${r.id}`, resource: r });
var quantity2 = (value, unit) => ({ value, unit: UCUM_DISPLAYS2[unit] ?? unit, system: UCUM_SYSTEM2, code: unit });
function exampleTag() {
  return slCoding(EXAMPLE_TAG_CODE);
}
function isExample(resource) {
  const tags = resource.meta?.tag ?? [];
  return tags.some((t) => t.system === SL_SYSTEM && t.code === EXAMPLE_TAG_CODE);
}
function resources(bundle, type) {
  return (bundle.entry ?? []).map((e) => e.resource).filter((r) => r && r.resourceType === type);
}
function identifierValue(resource) {
  let ident = resource.identifier;
  if (Array.isArray(ident)) ident = ident[0] ?? {};
  return ident && typeof ident === "object" ? String(ident.value ?? "") : "";
}
function valueCode(observation2) {
  const value = observation2.valueCodeableConcept;
  const codings = value?.coding ?? [];
  return codings.length ? String(codings[0].code) : null;
}
function pipeObservations(bundle) {
  return resources(bundle, "Observation").filter((obs) => {
    const ident = identifierValue(obs);
    return PIPE_ITEMS.some((item) => ident.endsWith(`-${item}`)) && valueCode(obs) === "present";
  });
}
function dedupe(list) {
  const seen = /* @__PURE__ */ new Set();
  const out = [];
  for (const r of list) {
    const key = `${r.resourceType}/${r.id}`;
    if (!seen.has(key)) {
      seen.add(key);
      out.push(structuredClone(r));
    }
  }
  return out;
}
function referralBundle(pipe, bundles, emittedAt) {
  let shared = [];
  const people = [];
  const responses = [];
  const reasons = [];
  for (const visitId of pipe.visit_ids) {
    const bundle = bundles[visitId];
    if (!bundle) continue;
    const found = pipeObservations(bundle);
    if (found.length === 0) continue;
    if (shared.length === 0) shared = [...resources(bundle, "Organization"), ...resources(bundle, "Location")];
    people.push(...resources(bundle, "Practitioner"));
    const visitQrId = fhirId("sl-qr-visit", visitId);
    responses.push(...resources(bundle, "QuestionnaireResponse").filter((qr) => qr.id === visitQrId));
    reasons.push(...found);
  }
  if (reasons.length === 0) throw new ReferralError(`pipe ${pipe.spot_id}: no stored pipe Observation to refer to`);
  const spotLocationId = fhirId("sl-loc", pipe.spot_id);
  if (!shared.some((loc) => loc.id === spotLocationId)) throw new ReferralError(`pipe ${pipe.spot_id}: the spot Location is not in the stored record`);
  const words = `Referral to test the water coming out of the pipe at ${pipe.spot_name}. Reported running after dry weather by ${pipe.observers.length} people who both passed the pipe feature, last on ${pipe.last_seen}.`;
  const serviceRequest = {
    resourceType: "ServiceRequest",
    id: fhirId("sl-referral", pipe.spot_id),
    text: narrative2(words),
    identifier: [identifier2(ID_SYSTEM_REFERRAL, pipe.spot_id)],
    status: "active",
    intent: "proposal",
    priority: "routine",
    code: concept2(slCoding("test-pipe-outflow")),
    subject: ref2("Location", spotLocationId),
    authoredOn: instant(emittedAt),
    requester: ref2("Organization", ORG_ID),
    reasonReference: reasons.map((o) => ref2("Observation", String(o.id)))
  };
  const all = [...dedupe([...shared, ...people, ...responses, ...reasons]), serviceRequest];
  return { resourceType: "Bundle", id: fhirId("sl-referral-bundle", pipe.spot_id), type: "collection", timestamp: instant(emittedAt), entry: all.map(entry2) };
}
function exampleMeta(profile) {
  const meta = { tag: [exampleTag()] };
  if (profile) meta.profile = [profile];
  return meta;
}
function exampleLab() {
  return {
    resourceType: "Organization",
    id: EXAMPLE_LAB_ID,
    meta: exampleMeta(),
    text: narrative2(`${EXAMPLE_WORD}. A made up laboratory, standing in for a real one.`),
    identifier: [identifier2(ID_SYSTEM_EXAMPLE, "example-lab")],
    name: "Example laboratory (not a real laboratory)",
    active: true
  };
}
function exampleLabRole() {
  return {
    resourceType: "PractitionerRole",
    id: EXAMPLE_LAB_ROLE_ID,
    meta: exampleMeta(),
    text: narrative2(`${EXAMPLE_WORD}. The sampling role at the made up laboratory. Their Specimen profile asks for a PractitionerRole as the collector.`),
    identifier: [identifier2(ID_SYSTEM_EXAMPLE, "example-lab-role")],
    active: true,
    organization: ref2("Organization", EXAMPLE_LAB_ID)
  };
}
function exampleSpecimen(spotId, spotLocationId, requestId, collectedAt) {
  return {
    resourceType: "Specimen",
    id: fhirId("sl-example-specimen", spotId),
    meta: exampleMeta(OAH_SPECIMEN_PROFILE),
    text: narrative2(`${EXAMPLE_WORD}. A water sample taken at the pipe, ${SAMPLE_ML} mL, for the referral. No sample has been taken.`),
    identifier: [identifier2(ID_SYSTEM_EXAMPLE, `specimen-${spotId}`)],
    status: "available",
    type: concept2({ system: SNOMED_SYSTEM2, code: SPECIMEN_TYPE_CODE, display: SPECIMEN_TYPE_DISPLAY }),
    subject: ref2("Location", spotLocationId),
    request: [ref2("ServiceRequest", requestId)],
    collection: { collector: ref2("PractitionerRole", EXAMPLE_LAB_ROLE_ID), collectedDateTime: instant(collectedAt), quantity: quantity2(SAMPLE_ML, "mL") }
  };
}
function gFormat(value) {
  return String(Number(value.toPrecision(6)));
}
function exampleObservation(spotId, spotName, spotLocationId, requestId, specimenId, code, kind, value, unit, reportedAt) {
  const display = String(slCoding(code).display);
  const out = {
    resourceType: "Observation",
    id: fhirId("sl-example-obs", spotId, code),
    meta: exampleMeta(OAH_OBSERVATION_PROFILE),
    identifier: [identifier2(ID_SYSTEM_EXAMPLE, `obs-${spotId}-${code}`)],
    basedOn: [ref2("ServiceRequest", requestId)],
    status: "final",
    category: [concept2({ system: OBSERVATION_CATEGORY_SYSTEM, code: "laboratory", display: "Laboratory" })],
    code: concept2(slCoding(code)),
    subject: ref2("Location", spotLocationId),
    effectiveDateTime: instant(reportedAt),
    performer: [ref2("PractitionerRole", EXAMPLE_LAB_ROLE_ID)],
    specimen: ref2("Specimen", specimenId)
  };
  let shown;
  if (kind === "quantity") {
    if (unit === null || typeof value !== "number") throw new ReferralError(`example ${code}: a quantity needs a number and a UCUM unit`);
    const q = quantity2(value, unit);
    out.valueQuantity = q;
    shown = `${gFormat(value)} ${q.unit}`;
  } else {
    if (typeof value !== "string") throw new ReferralError(`example ${code}: a coded value needs a code`);
    out.valueCodeableConcept = concept2(oahCoding(value));
    shown = value;
  }
  out.text = narrative2(`${EXAMPLE_WORD}. ${display} at ${spotName}: ${shown}. A made up number showing the shape of a laboratory result coming back to the same record.`);
  return out;
}
function exampleLabResult(referral, collectedAt, reportedAt) {
  const requests = resources(referral, "ServiceRequest");
  if (requests.length !== 1) throw new ReferralError("a referral Bundle holds exactly one ServiceRequest");
  const request = requests[0];
  const spotId = identifierValue(request);
  const spotLocationId = String(request.subject.reference).split("/", 2)[1];
  const spotName = String(resources(referral, "Location").find((loc) => loc.id === spotLocationId)?.name ?? spotId);
  const specimen = exampleSpecimen(spotId, spotLocationId, String(request.id), collectedAt);
  const panel = EXAMPLE_PANEL.map(
    ([code, kind, value, unit]) => exampleObservation(spotId, spotName, spotLocationId, String(request.id), String(specimen.id), code, kind, value, unit, reportedAt)
  );
  const entries = (referral.entry ?? []).map((e) => structuredClone(e));
  for (const r of [exampleLab(), exampleLabRole(), specimen, ...panel]) entries.push(entry2(r));
  return { resourceType: "Bundle", id: fhirId("sl-example-result", spotId), meta: exampleMeta(), type: "collection", timestamp: instant(reportedAt), entry: entries };
}

// src/core/followups.ts
var DEFAULT_MAX_QUESTIONS = 2;
var LOW_SCORE_MAX_CORRECT = core_content_default.rules.low_score_max_correct;
var FEATURES3 = core_content_default.rules.features_in_order;
var PIPE_ITEMS2 = core_content_default.rules.pipe_items;
var RATING_ISSUE_ITEMS = core_content_default.rules.rating_issue_items;
var PRESENT = "present";
var ABSENT = "absent";
var BEST_RATING = "good";
var RATING_ITEM2 = "overall_rating";
function itemById(formItems, id) {
  for (const item of formItems) if (item.id === id) return item;
  return null;
}
function issueLabel(item, itemId, value) {
  if (item === null) return itemId.replace(/_/g, " ");
  const short = item.short_label;
  if (typeof short === "string" && short.trim()) return short.trim();
  for (const option of item.options ?? []) {
    if (option && option.value === value) {
      const label = option.label;
      if (typeof label === "string" && label.trim()) return label.trim();
    }
  }
  const text = item.text;
  if (typeof text === "string" && text.trim()) return text.trim();
  return itemId.replace(/_/g, " ");
}
function joined(parts) {
  const rest = parts.slice(0, -1);
  const last = parts[parts.length - 1];
  return rest.length > 0 ? `${rest.join(", ")} and ${last}` : last;
}
function dryPipe(rule, answers, site) {
  if (site.rain !== "dry") return null;
  if (site.dry_days === null || site.dry_days === void 0 || site.dry_days < 1) return null;
  if (!PIPE_ITEMS2.some((item) => answers[item] === PRESENT)) return null;
  return {
    rule_id: "dry_pipe",
    kind: "yesno",
    question_key: String(rule.question_key ?? "followup.dry_pipe"),
    params: { days: Math.trunc(site.dry_days) }
  };
}
function ratingCheck(rule, answers, formItems) {
  if (answers[RATING_ITEM2] !== BEST_RATING) return null;
  const issues = [];
  for (const itemId of RATING_ISSUE_ITEMS) {
    const value = answers[itemId];
    if (value === PRESENT) issues.push(issueLabel(itemById(formItems, itemId), itemId, value));
  }
  if (issues.length === 0) return null;
  return {
    rule_id: "rating_check",
    kind: "keep_rating",
    question_key: String(rule.question_key ?? "followup.rating_check"),
    params: { issues: joined(issues), first_rating: BEST_RATING }
  };
}
function askedFeatures(formItems) {
  const asked = /* @__PURE__ */ new Set();
  for (const item of formItems) if (typeof item.feature === "string" && FEATURES3.includes(item.feature)) asked.add(item.feature);
  return asked;
}
function checkerFlag(rule, flags, checkerEnabled, formItems) {
  if (!checkerEnabled) return null;
  const asked = askedFeatures(formItems);
  let chosen = null;
  for (const flag of flags) {
    if (!asked.has(flag.feature)) continue;
    if (chosen === null || flag.confidence > chosen.confidence) chosen = flag;
  }
  if (chosen === null) return null;
  return {
    rule_id: "checker_flag",
    kind: "look_again",
    question_key: String(rule.question_key ?? "followup.checker_flag"),
    params: { note: chosen.note, feature: chosen.feature }
  };
}
function lowScore(rule, answers, observer, formItems) {
  if (observer === null) return null;
  let best = null;
  formItems.forEach((item, position) => {
    const feature2 = item.feature;
    const itemId2 = item.id;
    if (typeof feature2 !== "string" || !FEATURES3.includes(feature2) || typeof itemId2 !== "string") return;
    if (answers[itemId2] !== ABSENT) return;
    const score = scoreFor(observer, feature2);
    if (score === null || score.correct > LOW_SCORE_MAX_CORRECT) return;
    const key = [score.correct, position, itemId2, feature2];
    if (best === null || lessThan(key, best)) best = key;
  });
  if (best === null) return null;
  const [correct, , itemId, feature] = best;
  return {
    rule_id: "low_score",
    kind: "photo",
    question_key: String(rule.question_key ?? "followup.low_score"),
    params: { feature: feature.replace(/_/g, " "), feature_id: feature, item_id: itemId, correct }
  };
}
function lessThan(a, b) {
  for (let i = 0; i < 4; i++) {
    if (a[i] === b[i]) continue;
    return a[i] < b[i];
  }
  return false;
}
function rulesInPriority(table) {
  const rules = table.rules;
  if (!Array.isArray(rules)) return [];
  const typed = rules.filter((r) => r !== null && typeof r === "object" && typeof r.id === "string");
  return typed.sort((a, b) => {
    const pa = Math.trunc(Number(a.priority ?? 0));
    const pb = Math.trunc(Number(b.priority ?? 0));
    if (pa !== pb) return pa - pb;
    return String(a.id) < String(b.id) ? -1 : String(a.id) > String(b.id) ? 1 : 0;
  });
}
function selectFollowups(answers, site, observer, flags, table, formItems, checkerEnabled = false) {
  const cap = Math.trunc(Number(table.max_questions ?? DEFAULT_MAX_QUESTIONS));
  if (cap <= 0) return [];
  const chosen = [];
  for (const rule of rulesInPriority(table)) {
    if (chosen.length >= cap) break;
    let followup = null;
    switch (rule.id) {
      case "dry_pipe":
        followup = dryPipe(rule, answers, site);
        break;
      case "rating_check":
        followup = ratingCheck(rule, answers, formItems);
        break;
      case "checker_flag":
        followup = checkerFlag(rule, flags, checkerEnabled, formItems);
        break;
      case "low_score":
        followup = lowScore(rule, answers, observer, formItems);
        break;
      default:
        followup = null;
    }
    if (followup !== null && chosen.every((f) => f.rule_id !== followup.rule_id)) chosen.push(followup);
  }
  return chosen.slice(0, cap);
}

// src/core/healthcard.ts
var AUDIENCES = ["person", "pet", "city"];
function eligible(s) {
  const text = s.text;
  const source = s.source;
  return s.approved === true && typeof text === "string" && text.trim().length > 0 && typeof source === "string" && source.trim().length > 0 && AUDIENCES.includes(String(s.audience));
}
function pickIndex(seed, audience, count) {
  const digest = sha256Bytes(`${seed}:${audience}`);
  let value = 0n;
  for (let i = 0; i < 8; i++) value = value << 8n | BigInt(digest[i]);
  return Number(value % BigInt(count));
}
function pickActions(sentences, seed) {
  const chosen = {};
  for (const audience of AUDIENCES) {
    const pool = sentences.filter((s) => eligible(s) && s.audience === audience).sort((a, b) => compareStrings(String(a.id ?? ""), String(b.id ?? "")) || compareStrings(String(a.text), String(b.text)));
    if (pool.length === 0) return null;
    const pick = pool[pickIndex(seed, audience, pool.length)];
    chosen[audience] = [String(pick.text).trim(), String(pick.source).trim()];
  }
  return {
    person: chosen.person[0],
    pet: chosen.pet[0],
    city: chosen.city[0],
    sources: [chosen.person[1], chosen.pet[1], chosen.city[1]]
  };
}

// src/core/walks.ts
var DEMO_TAG_SYSTEM = `${REPO_URL}/tags`;
var DEMO_TAG_CODE = "demo-walk";
var DEMO_TAG_DISPLAY = "Demo visit from a video walk. Never counted and never sent to the sandbox.";
var WALK_PREFIX = "walk-";
var RATING_ITEM3 = "overall_rating";
var WALK_KEEP_DAYS = 30;
var WALK_PAST_DAYS = 7;
var WALK_FUTURE_SECONDS = 300;
var WALK_DAILY_CAP = 200;
var WALK_MAX_BYTES = 4096;
var ANSWERED_AT_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$/;
var DAY_MS = 864e5;
function walkSpot(walk) {
  const wid = `${WALK_PREFIX}${walk.id}`;
  return {
    spot_id: `${wid}-spot`,
    spot_name: walk.spot_name,
    reach_id: `${wid}-reach`,
    reach_name: walk.spot_name,
    creek_id: wid,
    creek_name: walk.creek_name,
    latitude: null,
    longitude: null,
    coarse: true
  };
}
function walkVisitId(walkId, answeredAt) {
  return WALK_PREFIX + sha256Hex(`${walkId}|${instant(answeredAt)}`).slice(0, 16);
}
function walkVisit(walk, answers, answeredAt, language = "en") {
  return {
    visit_id: walkVisitId(walk.id, answeredAt),
    spot: walkSpot(walk),
    observer: { contributor_token: `demo-walk-${walk.id}`, scores: [], test_sitting_id: null },
    answered_at: instant(answeredAt),
    answers: { ...answers },
    first_rating: null,
    final_rating: null,
    checks: [],
    photo_ids: [],
    software_version: "0.1.0",
    language
  };
}
function tagDemo(bundle) {
  const out = JSON.parse(JSON.stringify(bundle));
  const tag = { system: DEMO_TAG_SYSTEM, code: DEMO_TAG_CODE, display: DEMO_TAG_DISPLAY };
  const nodes = [out, ...(out.entry ?? []).map((e) => e.resource)];
  for (const node of nodes) {
    const meta = node.meta ?? {};
    const kept = (meta.tag ?? []).filter((t) => t.system !== DEMO_TAG_SYSTEM);
    meta.tag = [...kept, { ...tag }];
    node.meta = meta;
  }
  return out;
}
function ratingChangedNote(first, final) {
  return `The first overall rating was ${first}. On the rating check the volunteer changed it to ${final}.`;
}
function walkBundle(walk, answers, answeredAt, finalRating = null, language = "en") {
  const first = answers[RATING_ITEM3];
  const changed = typeof first === "string" && finalRating !== null && finalRating !== first;
  const rated = changed ? { ...answers, [RATING_ITEM3]: finalRating } : answers;
  const bundle = emitVisit(walkVisit(walk, rated, answeredAt, language), null, instant(answeredAt));
  if (changed) {
    for (const entry3 of bundle.entry) {
      const resource = entry3.resource;
      if (resource.resourceType !== "QuestionnaireResponse") continue;
      const text = resource.text;
      const note = escapeXml(ratingChangedNote(first, finalRating));
      text.div = String(text.div).replace("</p></div>", `</p><p>${note}</p></div>`);
    }
  }
  return tagDemo(bundle);
}
function isDemo(bundle) {
  const tags = bundle.meta?.tag ?? [];
  return tags.some((t) => t.system === DEMO_TAG_SYSTEM && t.code === DEMO_TAG_CODE);
}
var WalkRecordError = class extends Error {
};
function walkAnsweredAt(text, now) {
  if (typeof text !== "string" || !ANSWERED_AT_RE.test(text)) throw new WalkRecordError("answered_at must be a time like 2026-09-25T10:00:00Z.");
  const at = parseInstant(text);
  const clock = parseInstant(now);
  if (at > clock + WALK_FUTURE_SECONDS * 1e3) throw new WalkRecordError("That walk is dated in the future. Check the phone's clock.");
  if (at < clock - WALK_PAST_DAYS * DAY_MS) throw new WalkRecordError(`That walk is more than ${WALK_PAST_DAYS} days old, so it is not stored.`);
  return instant(at);
}
function walkRecord(walk, answers, answeredAt, now, finalRating = null, language = "en") {
  const at = walkAnsweredAt(answeredAt, now);
  const clock = parseInstant(now);
  return {
    record_id: walkVisitId(walk.id, at),
    walk_id: walk.id,
    answered_at: at,
    created_at: instant(clock),
    delete_after: instant(clock + WALK_KEEP_DAYS * DAY_MS),
    bundle: walkBundle(walk, answers, at, finalRating, language)
  };
}
var WALK_SITE = { rain: "unknown" };
var WALK_FOLLOWUP_ANSWERS = {
  yesno: ["yes", "no", "cant_tell", "skipped"],
  keep_rating: ["keep", "change", "skipped"],
  look_again: ["looked", "skipped"],
  photo: ["skipped"]
};
function walkFollowups(answers, table, formItems) {
  return selectFollowups(answers, WALK_SITE, null, [], table, formItems, false);
}
function walkChecks(answers, followups, questionTexts, given, finalRating) {
  if (questionTexts.length !== followups.length) throw new WalkRecordError("Every follow-up needs its question.");
  const asked = new Set(followups.map((f) => f.rule_id));
  for (const ruleId of Object.keys(given)) {
    if (!asked.has(ruleId)) throw new WalkRecordError(`No follow-up called '${ruleId}' was asked in this walk.`);
  }
  const first = answers[RATING_ITEM3];
  const firstRating = typeof first === "string" ? first : null;
  let final = firstRating;
  const checks = followups.map((f, i) => {
    const raw = given[f.rule_id];
    let answer2 = null;
    if (raw !== void 0 && raw !== null) {
      const allowed = WALK_FOLLOWUP_ANSWERS[f.kind] ?? [];
      if (typeof raw !== "string" || !allowed.includes(raw)) throw new WalkRecordError(`${f.rule_id}: answer ${allowed.join(", ")}.`);
      answer2 = raw;
    }
    if (f.kind === "keep_rating" && answer2 === "change") {
      if (finalRating === null) throw new WalkRecordError("A changed rating needs the new rating.");
      final = finalRating;
    }
    const detail = {};
    for (const [k, v] of Object.entries(f.params)) detail[k] = typeof v === "string" || typeof v === "number" ? v : String(v);
    detail.kind = f.kind;
    return { rule_id: f.rule_id, asked: true, question_text: questionTexts[i], answer: answer2, detail };
  });
  if (finalRating !== null && finalRating !== final) throw new WalkRecordError("The final rating can differ from the first only when the rating check says change.");
  return { checks, final_rating: final };
}

// src/fhir_http.ts
var FHIR_JSON = "application/fhir+json; charset=utf-8";
var PLAIN_JSON = "application/json; charset=utf-8";
var ISSUE_CODES = {
  404: "not-found",
  409: "conflict",
  413: "too-long",
  422: "invalid",
  429: "throttled"
};
function operationOutcome(status, sentence) {
  return {
    resourceType: "OperationOutcome",
    text: { status: "generated", div: `<div xmlns="http://www.w3.org/1999/xhtml"><p>${escapeXml(sentence)}</p></div>` },
    issue: [{ severity: "error", code: ISSUE_CODES[status] ?? "exception", details: { text: sentence } }]
  };
}
function fhirMediaType(accept) {
  return (accept ?? "").toLowerCase().includes("text/html") ? PLAIN_JSON : FHIR_JSON;
}

// ../results/fhir_validation.json
var fhir_validation_default = {
  ran_at_utc: "2026-09-27T05:08:56+00:00",
  validator_version: "6.10.4",
  ig_commit: "b907cf0",
  fhir_version: "4.0.1",
  terminology_checks_ran: true,
  terminology_server: "https://tx.fhir.org",
  files: [
    "fhir/build/ig/fsh-generated/resources/Bundle-sl-city-heraklion-bundle.json",
    "fhir/build/ig/fsh-generated/resources/Bundle-sl-visit-1-bundle.json",
    "fhir/golden/example-lab-result-strawberry-creek-1.json",
    "fhir/golden/library-second-look.json",
    "fhir/golden/referral-strawberry-creek-1.json",
    "fhir/golden/visit-strawberry-creek-1.json",
    "fhir/golden/visit-strawberry-creek-1.transaction.json",
    "fhir/build/instances/ts-sl-example-result-spot-1.json",
    "fhir/build/instances/ts-sl-referral-bundle-spot-1.json",
    "fhir/build/instances/ts-sl-visit-7c1e2d3f-4a5b-4c6d-8e9f-0a1b2c3d4e5f.json",
    "fhir/build/instances/ts-sl-visit-visit-0001.json",
    "fhir/build/instances/ts-sl-visit-visit-rating-changed.json",
    "fhir/build/instances/ts-sl-visit-visit-rating-kept.json",
    "fhir/build/instances/ts-sl-visit-visit-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-ac87f97c923d.json",
    "fhir/build/instances/ts-sl-visit-walk-4116f9ddf7b8b451.json",
    "fhir/build/instances/ts-sl-visit-walk-757a5b9a10482fc9.json",
    "fhir/build/instances/ts-sl-visit-walk-d2ef0549e6f251c4.json"
  ],
  errors: 0,
  warnings: 70,
  files_validated: 17,
  walk_records_validated: 3,
  by_file: {
    "Bundle-sl-city-heraklion-bundle.json": {
      error: 0,
      warning: 8,
      information: 0
    },
    "Bundle-sl-visit-1-bundle.json": {
      error: 0,
      warning: 17,
      information: 4
    },
    "example-lab-result-strawberry-creek-1.json": {
      error: 0,
      warning: 3,
      information: 5
    },
    "library-second-look.json": {
      error: 0,
      warning: 0,
      information: 1
    },
    "referral-strawberry-creek-1.json": {
      error: 0,
      warning: 3,
      information: 2
    },
    "visit-strawberry-creek-1.json": {
      error: 0,
      warning: 3,
      information: 5
    },
    "visit-strawberry-creek-1.transaction.json": {
      error: 0,
      warning: 3,
      information: 20
    },
    "ts-sl-example-result-spot-1.json": {
      error: 0,
      warning: 3,
      information: 5
    },
    "ts-sl-referral-bundle-spot-1.json": {
      error: 0,
      warning: 3,
      information: 2
    },
    "ts-sl-visit-7c1e2d3f-4a5b-4c6d-8e9f-0a1b2c3d4e5f.json": {
      error: 0,
      warning: 4,
      information: 5
    },
    "ts-sl-visit-visit-0001.json": {
      error: 0,
      warning: 3,
      information: 5
    },
    "ts-sl-visit-visit-rating-changed.json": {
      error: 0,
      warning: 4,
      information: 7
    },
    "ts-sl-visit-visit-rating-kept.json": {
      error: 0,
      warning: 4,
      information: 5
    },
    "ts-sl-visit-visit-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-ac87f97c923d.json": {
      error: 0,
      warning: 3,
      information: 2
    },
    "ts-sl-visit-walk-4116f9ddf7b8b451.json": {
      error: 0,
      warning: 3,
      information: 11
    },
    "ts-sl-visit-walk-757a5b9a10482fc9.json": {
      error: 0,
      warning: 3,
      information: 13
    },
    "ts-sl-visit-walk-d2ef0549e6f251c4.json": {
      error: 0,
      warning: 3,
      information: 14
    }
  },
  messages: [
    {
      file: "Bundle-sl-city-heraklion-bundle.json",
      severity: "warning",
      location: "Bundle.entry[0].resource/*Location/sl-city-heraklion*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "Bundle-sl-city-heraklion-bundle.json",
      severity: "warning",
      location: "Bundle.entry[0].resource/*Location/sl-city-heraklion*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "Bundle-sl-city-heraklion-bundle.json",
      severity: "warning",
      location: "Bundle.entry[1].resource/*Location/sl-city-heraklion-creek-1*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "Bundle-sl-city-heraklion-bundle.json",
      severity: "warning",
      location: "Bundle.entry[1].resource/*Location/sl-city-heraklion-creek-1*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "Bundle-sl-city-heraklion-bundle.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/sl-city-heraklion-creek-1-reach-1*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "Bundle-sl-city-heraklion-bundle.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/sl-city-heraklion-creek-1-reach-1*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "Bundle-sl-city-heraklion-bundle.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/sl-city-heraklion-creek-1-reach-1-spot-1*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "Bundle-sl-city-heraklion-bundle.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/sl-city-heraklion-creek-1-reach-1-spot-1*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "Bundle-sl-visit-1-bundle.json",
      severity: "warning",
      location: "Bundle.entry[0].resource/*Organization/sl-org*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "Bundle-sl-visit-1-bundle.json",
      severity: "warning",
      location: "Bundle.entry[1].resource/*Device/sl-device*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "Bundle-sl-visit-1-bundle.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/sl-loc-strawberry-creek*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "Bundle-sl-visit-1-bundle.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/sl-loc-strawberry-creek*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "Bundle-sl-visit-1-bundle.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/sl-loc-campus-reach*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "Bundle-sl-visit-1-bundle.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/sl-loc-campus-reach*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "Bundle-sl-visit-1-bundle.json",
      severity: "warning",
      location: "Bundle.entry[4].resource/*Location/sl-loc-spot-1*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "Bundle-sl-visit-1-bundle.json",
      severity: "warning",
      location: "Bundle.entry[4].resource/*Location/sl-loc-spot-1*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "Bundle-sl-visit-1-bundle.json",
      severity: "warning",
      location: "Bundle.entry[5].resource/*Practitioner/sl-practitioner-1*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "Bundle-sl-visit-1-bundle.json",
      severity: "warning",
      location: "Bundle.entry[6].resource/*QuestionnaireResponse/sl-qr-test-1*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "Bundle-sl-visit-1-bundle.json",
      severity: "warning",
      location: "Bundle.entry[7].resource/*QuestionnaireResponse/sl-qr-visit-1*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "Bundle-sl-visit-1-bundle.json",
      severity: "warning",
      location: "Bundle.entry[8].resource/*Observation/sl-obs-bank-1*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "Bundle-sl-visit-1-bundle.json",
      severity: "warning",
      location: "Bundle.entry[9].resource/*Observation/sl-obs-channel-1*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "Bundle-sl-visit-1-bundle.json",
      severity: "warning",
      location: "Bundle.entry[10].resource/*Observation/sl-obs-invasive-1*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "Bundle-sl-visit-1-bundle.json",
      severity: "warning",
      location: "Bundle.entry[11].resource/*Observation/sl-obs-pipe-1*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "Bundle-sl-visit-1-bundle.json",
      severity: "warning",
      location: "Bundle.entry[12].resource/*Observation/sl-obs-water-height-1*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "Bundle-sl-visit-1-bundle.json",
      severity: "warning",
      location: "Bundle.entry[13].resource/*Provenance/sl-provenance-visit-1*/",
      text: "Constraint failed: dom-6: 'A resource should have narrative for robust management' (defined in http://hl7.org/fhir/StructureDefinition/DomainResource) (Best Practice Recommendation)"
    },
    {
      file: "example-lab-result-strawberry-creek-1.json",
      severity: "warning",
      location: "Bundle.entry[1].resource/*Location/sl-loc-strawberry-creek*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "example-lab-result-strawberry-creek-1.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/sl-loc-campus-reach*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "example-lab-result-strawberry-creek-1.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/sl-loc-spot-1*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "referral-strawberry-creek-1.json",
      severity: "warning",
      location: "Bundle.entry[1].resource/*Location/sl-loc-strawberry-creek*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "referral-strawberry-creek-1.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/sl-loc-campus-reach*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "referral-strawberry-creek-1.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/sl-loc-spot-1*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "visit-strawberry-creek-1.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/sl-loc-strawberry-creek*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "visit-strawberry-creek-1.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/sl-loc-campus-reach*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "visit-strawberry-creek-1.json",
      severity: "warning",
      location: "Bundle.entry[4].resource/*Location/sl-loc-spot-1*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "visit-strawberry-creek-1.transaction.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/null*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "visit-strawberry-creek-1.transaction.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/null*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "visit-strawberry-creek-1.transaction.json",
      severity: "warning",
      location: "Bundle.entry[4].resource/*Location/null*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-example-result-spot-1.json",
      severity: "warning",
      location: "Bundle.entry[1].resource/*Location/sl-loc-strawberry-creek*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-example-result-spot-1.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/sl-loc-campus-reach*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-example-result-spot-1.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/sl-loc-spot-1*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-referral-bundle-spot-1.json",
      severity: "warning",
      location: "Bundle.entry[1].resource/*Location/sl-loc-strawberry-creek*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-referral-bundle-spot-1.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/sl-loc-campus-reach*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-referral-bundle-spot-1.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/sl-loc-spot-1*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-7c1e2d3f-4a5b-4c6d-8e9f-0a1b2c3d4e5f.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/sl-loc-codornices-creek*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-7c1e2d3f-4a5b-4c6d-8e9f-0a1b2c3d4e5f.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/sl-loc-codornices-lower*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-7c1e2d3f-4a5b-4c6d-8e9f-0a1b2c3d4e5f.json",
      severity: "warning",
      location: "Bundle.entry[4].resource/*Location/sl-loc-codornices-lower-2*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-7c1e2d3f-4a5b-4c6d-8e9f-0a1b2c3d4e5f.json",
      severity: "warning",
      location: "Bundle.entry[6].resource/*QuestionnaireResponse/sl-qr-visit-7c1e2d3f-4a5b-4c6d-8e9f-0a1b2c3d4e5f*/",
      text: "Resource has a language (it), and the XHTML has a lang (en), but they differ"
    },
    {
      file: "ts-sl-visit-visit-0001.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/sl-loc-strawberry-creek*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-visit-0001.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/sl-loc-campus-reach*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-visit-0001.json",
      severity: "warning",
      location: "Bundle.entry[4].resource/*Location/sl-loc-spot-1*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-visit-rating-changed.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/sl-loc-codornices-creek*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-visit-rating-changed.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/sl-loc-codornices-lower*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-visit-rating-changed.json",
      severity: "warning",
      location: "Bundle.entry[4].resource/*Location/sl-loc-codornices-lower-2*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-visit-rating-changed.json",
      severity: "warning",
      location: "Bundle.entry[6].resource/*QuestionnaireResponse/sl-qr-visit-visit-rating-changed*/",
      text: "Resource has a language (it), and the XHTML has a lang (en), but they differ"
    },
    {
      file: "ts-sl-visit-visit-rating-kept.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/sl-loc-codornices-creek*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-visit-rating-kept.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/sl-loc-codornices-lower*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-visit-rating-kept.json",
      severity: "warning",
      location: "Bundle.entry[4].resource/*Location/sl-loc-codornices-lower-2*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-visit-rating-kept.json",
      severity: "warning",
      location: "Bundle.entry[6].resource/*QuestionnaireResponse/sl-qr-visit-visit-rating-kept*/",
      text: "Resource has a language (it), and the XHTML has a lang (en), but they differ"
    },
    {
      file: "ts-sl-visit-visit-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-ac87f97c923d.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/sl-loc-strawberry-creek*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-visit-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-ac87f97c923d.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/sl-loc-campus-reach*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-visit-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-ac87f97c923d.json",
      severity: "warning",
      location: "Bundle.entry[4].resource/*Location/sl-loc-spot-with-spaces---odd-chars*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-walk-4116f9ddf7b8b451.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/sl-loc-walk-v03*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-walk-4116f9ddf7b8b451.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/sl-loc-walk-v03-reach*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-walk-4116f9ddf7b8b451.json",
      severity: "warning",
      location: "Bundle.entry[4].resource/*Location/sl-loc-walk-v03-spot*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-walk-757a5b9a10482fc9.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/sl-loc-walk-v03*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-walk-757a5b9a10482fc9.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/sl-loc-walk-v03-reach*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-walk-757a5b9a10482fc9.json",
      severity: "warning",
      location: "Bundle.entry[4].resource/*Location/sl-loc-walk-v03-spot*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-walk-d2ef0549e6f251c4.json",
      severity: "warning",
      location: "Bundle.entry[2].resource/*Location/sl-loc-walk-v03*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-walk-d2ef0549e6f251c4.json",
      severity: "warning",
      location: "Bundle.entry[3].resource/*Location/sl-loc-walk-v03-reach*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    },
    {
      file: "ts-sl-visit-walk-d2ef0549e6f251c4.json",
      severity: "warning",
      location: "Bundle.entry[4].resource/*Location/sl-loc-walk-v03-spot*/.type[0]",
      text: "None of the codings provided are in the value set 'ServiceDeliveryLocationRoleType' (http://terminology.hl7.org/ValueSet/v3-ServiceDeliveryLocationRoleType|3.0.0), and a coding should come from this value set unless it has no suitable code (note that the validator cannot judge what is suitable) (cod"
    }
  ]
};

// src/core/rainfall.ts
var OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast";
var SOURCE_OPEN_METEO = "open-meteo";
var SOURCE_UNKNOWN = "unknown";
var PAST_DAYS = 4;
var FORECAST_DAYS = 1;
var DEFAULT_DRY_MM = 2.5;
var DEFAULT_WINDOW_HOURS = 72;
var DRY_HOUR_MAX_MM = 0.1;
var HOURS_PER_DAY = 24;
var HOUR_MS = 36e5;
var UNKNOWN = { status: "unknown", mm_in_window: null, dry_days: null, source: SOURCE_UNKNOWN };
function buildUrl(latitude, longitude) {
  const query = new URLSearchParams({
    latitude: latitude.toFixed(4),
    longitude: longitude.toFixed(4),
    hourly: "precipitation",
    past_days: String(PAST_DAYS),
    forecast_days: String(FORECAST_DAYS),
    timezone: "UTC"
  });
  return `${OPEN_METEO_URL}?${query.toString()}`;
}
function hours(payload) {
  if (!payload || typeof payload !== "object") throw new Error("payload is not an object");
  const hourly = payload.hourly;
  if (!hourly || typeof hourly !== "object") throw new Error("hourly is not an object");
  const times = hourly.time;
  const values = hourly.precipitation;
  if (!Array.isArray(times) || !Array.isArray(values) || times.length !== values.length) {
    throw new Error("time and precipitation lists do not line up");
  }
  const out = [];
  for (let i = 0; i < times.length; i++) {
    const text = times[i];
    const value = values[i];
    if (typeof text !== "string") throw new Error("time is not text");
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0) throw new Error("precipitation is not a finite non-negative number");
    const ms = Date.parse(`${text}Z`);
    if (Number.isNaN(ms)) throw new Error(`bad hour ${text}`);
    out.push([ms, value]);
  }
  return out;
}
function window(list, start, end) {
  const picked = list.filter(([hourEnd]) => start < hourEnd && hourEnd <= end).map(([, mm]) => mm);
  const needed = Math.trunc((end - start) / HOUR_MS);
  return picked.length < needed ? null : picked;
}
function dryDays(list, now) {
  let days = 0;
  for (; ; ) {
    const end = now - HOURS_PER_DAY * days * HOUR_MS;
    const start = end - HOURS_PER_DAY * HOUR_MS;
    const values = window(list, start, end);
    if (values === null || values.some((mm) => mm > DRY_HOUR_MAX_MM)) return days;
    days += 1;
  }
}
function statusFromPayload(payload, nowMs, dryMm = DEFAULT_DRY_MM, windowHours = DEFAULT_WINDOW_HOURS) {
  const list = hours(payload);
  const values = window(list, nowMs - windowHours * HOUR_MS, nowMs);
  if (values === null) return UNKNOWN;
  const total = Math.round(values.reduce((a, b) => a + b, 0) * 100) / 100;
  return { status: total <= dryMm ? "dry" : "wet", mm_in_window: total, dry_days: dryDays(list, nowMs), source: SOURCE_OPEN_METEO };
}
async function dryStatus(latitude, longitude, nowMs, fetchJson, dryMm = DEFAULT_DRY_MM, windowHours = DEFAULT_WINDOW_HOURS) {
  try {
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || Math.abs(latitude) > 90 || Math.abs(longitude) > 180 || windowHours <= 0) {
      return UNKNOWN;
    }
    const payload = await fetchJson(buildUrl(latitude, longitude));
    return statusFromPayload(payload, nowMs, dryMm, windowHours);
  } catch {
    return UNKNOWN;
  }
}
async function fetchOpenMeteo(url) {
  let last = null;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(5e3) });
      if (!response.ok) throw new Error(`open-meteo ${response.status}`);
      return await response.json();
    } catch (err) {
      last = err;
    }
  }
  throw last;
}

// src/check.ts
var Invalid = class extends Error {
};
var NotFound = class extends Error {
};
var COARSE_DECIMALS = 2;
var FOLLOWUP_ANSWERS = /* @__PURE__ */ new Set(["yes", "no", "cant_tell", "keep", "change", "skipped"]);
var QUICK_TEXT = {
  colour: "What colour is the water?",
  smell: "Does it smell?",
  pipe_running: "Is anything coming out of the pipe?"
};
var SLIDER_RE = /^(joy|serenity|anger|fear):([0-5]|not_applicable)$/;
var YESNO_LABEL_KEYS = { present: "test.yes", absent: "test.no", cant_tell: "test.cant_tell" };
var LOCALE = content_default.locale;
var REGION_PLANTS = /* @__PURE__ */ new Set([...content_default.region_plants, "cant_tell"]);
var SOFTWARE_VERSION = "0.1.0";
var NAME_RE = /^[A-Za-z0-9 .,'()/-]+$/;
var randomHex = (bytes) => Array.from(crypto.getRandomValues(new Uint8Array(bytes)), (b) => b.toString(16).padStart(2, "0")).join("");
function spotFromRow(row) {
  return {
    spot_id: row.spot_id,
    spot_name: row.spot_name,
    reach_id: row.reach_id,
    reach_name: row.reach_name,
    creek_id: row.creek_id,
    creek_name: row.creek_name,
    latitude: row.latitude,
    longitude: row.longitude,
    coarse: Boolean(row.coarse)
  };
}
async function getSpot(db, spotId) {
  return db.prepare("SELECT * FROM spot WHERE spot_id = ?").bind(spotId).first();
}
async function allSpots(db) {
  return (await db.prepare("SELECT * FROM spot ORDER BY created_at").all()).results ?? [];
}
async function observerFromToken(db, token) {
  if (!token) return null;
  const row = await db.prepare("SELECT contributor_token, scores_json, tested_on FROM observer WHERE contributor_token = ?").bind(token).first();
  if (row === null) throw new NotFound("We do not know that contributor token. Check it and try again.");
  return observerFromRow(row);
}
function observerFromRow(row) {
  const raw = JSON.parse(row.scores_json);
  return {
    contributor_token: row.contributor_token,
    scores: raw.map((s) => ({ feature: s.feature, correct: Math.trunc(Number(s.correct)), total: Math.trunc(Number(s.total)), tested_on: row.tested_on.slice(0, 10) }))
  };
}
async function sittingFor(db, token) {
  if (!token) return null;
  const row = await db.prepare("SELECT contributor_token, scores_json, tested_on FROM observer WHERE contributor_token = ?").bind(token).first();
  if (row === null) return null;
  const observer = observerFromRow(row);
  if (observer.scores.length === 0) return null;
  return {
    sitting_id: `sitting-${sha256Hex(token).slice(0, 12)}`,
    contributor_token: token,
    completed_at: `${row.tested_on.slice(0, 10)}T00:00:00Z`,
    scores: observer.scores
  };
}
function formItem(itemId) {
  for (const item of FORM_ITEMS) if (item.id === itemId) return item;
  return null;
}
function optionValues(item) {
  return new Set((item.options ?? []).map((o) => String(o.value)));
}
function validateAnswers(answers) {
  const clean = {};
  for (const [itemId, value] of Object.entries(answers)) {
    const item = formItem(itemId);
    if (item === null) throw new Invalid(`We do not have a question called '${itemId}'.`);
    const kind = item.type;
    if (kind === "choice") {
      if (typeof value !== "string" || !optionValues(item).has(value)) throw new Invalid(`${itemId}: pick one of the listed options.`);
      clean[itemId] = value;
    } else if (kind === "yesno") {
      if (value !== "present" && value !== "absent" && value !== "cant_tell") throw new Invalid(`${itemId}: answer present, absent or cant_tell.`);
      clean[itemId] = value;
    } else if (kind === "multi") {
      const allowed = optionValues(item);
      if (!Array.isArray(value) || value.some((v) => typeof v !== "string" || !allowed.has(v))) throw new Invalid(`${itemId}: choose only from the listed options.`);
      clean[itemId] = value;
    } else if (kind === "number") {
      if (typeof value !== "number" || !Number.isFinite(value)) throw new Invalid(`${itemId}: send a number.`);
      if (value < 0 || value > 100) throw new Invalid(`${itemId}: that number is out of range.`);
      clean[itemId] = value;
    } else if (kind === "pick_region_list") {
      if (!Array.isArray(value) || value.some((v) => typeof v !== "string" || !REGION_PLANTS.has(v))) throw new Invalid(`${itemId}: choose plants from the regional list, or cant_tell.`);
      clean[itemId] = value;
    } else if (kind === "sliders") {
      if (!Array.isArray(value) || value.some((v) => typeof v !== "string" || !SLIDER_RE.test(v))) throw new Invalid(`${itemId}: send entries like joy:3 or fear:not_applicable.`);
      clean[itemId] = value;
    } else {
      throw new Invalid(`${itemId}: this question cannot be answered here.`);
    }
  }
  return clean;
}
function validateLanguage(value) {
  if (value === void 0 || value === null) return "en";
  if (typeof value !== "string" || !content_default.check_languages.includes(value)) throw new Invalid("The creek check is not offered in that language.");
  return value;
}
function validateRating(value) {
  if (value === null || value === void 0) return null;
  const item = formItem("overall_rating");
  if (item === null || typeof value !== "string" || !optionValues(item).has(value)) throw new Invalid("The overall rating must be good, moderate or poor.");
  return value;
}
function plainPlaceName(raw, what) {
  if (raw === null || raw === void 0) return null;
  if (typeof raw !== "string") throw new Invalid(`${what} must be text.`);
  const v = raw.split(/\s+/).filter(Boolean).join(" ");
  if (!v) throw new Invalid("A name is needed.");
  if (v.length > 80) throw new Invalid(`${what} is too long.`);
  if (!NAME_RE.test(v)) throw new Invalid("Use letters, numbers, spaces and . , ' - ( ) / only.");
  if (/\d{5,}/.test(v)) throw new Invalid("That looks like an address or a code, not a place name.");
  if (v.includes("@")) throw new Invalid("A place name cannot hold an email address.");
  return v;
}
function parseSpotRef(raw) {
  if (!raw || typeof raw !== "object") throw new Invalid("Say which spot this is, or describe a new one.");
  const r = raw;
  if (typeof r.spot_id === "string" && r.spot_id) {
    if (r.spot_id.length > 32) throw new Invalid("That spot id is too long.");
    return { spot_id: r.spot_id };
  }
  if (r.new && typeof r.new === "object") {
    const n = r.new;
    const name = plainPlaceName(n.name, "The spot name");
    if (name === null) throw new Invalid("A name is needed.");
    const num = (v, lo, hi, what) => {
      if (v === null || v === void 0) return null;
      if (typeof v !== "number" || !Number.isFinite(v) || v < lo || v > hi) throw new Invalid(`${what} is out of range.`);
      return v;
    };
    return {
      new: {
        name,
        latitude: num(n.latitude, -90, 90, "Latitude"),
        longitude: num(n.longitude, -180, 180, "Longitude"),
        coarse: n.coarse === void 0 ? true : Boolean(n.coarse),
        creek_name: plainPlaceName(n.creek_name, "The creek name"),
        reach_name: plainPlaceName(n.reach_name, "The reach name")
      }
    };
  }
  throw new Invalid("Say which spot this is, or describe a new one.");
}
function roundCoarse(value, coarse) {
  if (value === null) return null;
  return coarse ? pyRound(value, COARSE_DECIMALS) : pyRound(value, 6);
}
async function nearbyExistingSpot(db, ref3) {
  if (ref3.spot_id || !ref3.new) return null;
  if (ref3.new.latitude === null || ref3.new.longitude === null) return null;
  if (ref3.new.coarse) return null;
  const rows = (await db.prepare("SELECT * FROM spot WHERE coarse = 0").all()).results ?? [];
  const near = nearestSpot(ref3.new.latitude, ref3.new.longitude, rows.map(spotFromRow));
  if (near === null) return null;
  return { spot_id: near.spot.spot_id, spot_name: near.spot.spot_name, metres: Math.round(near.metres) };
}
async function resolveSpot(db, ref3, now) {
  if (ref3.spot_id) {
    const row2 = await getSpot(db, ref3.spot_id);
    if (row2 === null) throw new NotFound("We do not know that spot. Add it as a new spot.");
    return row2;
  }
  const n = ref3.new;
  const tail = randomHex(6);
  const row = {
    spot_id: `spot-${tail}`,
    spot_name: n.name.trim(),
    reach_id: `reach-${tail}`,
    reach_name: (n.reach_name ?? n.name).trim(),
    creek_id: `creek-${tail}`,
    creek_name: (n.creek_name ?? n.name).trim(),
    latitude: roundCoarse(n.latitude, n.coarse),
    longitude: roundCoarse(n.longitude, n.coarse),
    coarse: n.coarse ? 1 : 0,
    created_at: now
  };
  await db.prepare("INSERT INTO spot (spot_id, spot_name, reach_id, reach_name, creek_id, creek_name, latitude, longitude, coarse, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)").bind(row.spot_id, row.spot_name, row.reach_id, row.reach_name, row.creek_id, row.creek_name, row.latitude, row.longitude, row.coarse, row.created_at).run();
  return row;
}
function featureNameForParam(value) {
  const raw = String(value).trim();
  const fid = raw.replace(/ /g, "_");
  for (const f of content_default.feature_list) if (f.id === fid || f.id === raw) return f.name;
  return raw;
}
function questionText(f) {
  const params = { ...f.params };
  if ("feature" in params) params.feature = featureNameForParam(params.feature);
  return fill(LOCALE[f.question_key] ?? f.question_key, params);
}
var apiKind = (kind) => kind === "look_again" ? "yesno" : kind;
async function photoExists(db, photoId) {
  return await db.prepare("SELECT photo_id FROM upload WHERE photo_id = ?").bind(photoId).first() !== null;
}
async function checkPhotoIds(db, ids) {
  if (ids === void 0 || ids === null) return [];
  if (!Array.isArray(ids) || ids.length > 8 || ids.some((p) => typeof p !== "string")) throw new Invalid("photo_ids must be a short list of photo ids.");
  for (const pid of ids) if (!await photoExists(db, pid)) throw new Invalid(`We do not have a photo called '${pid}'. Upload it first.`);
  return [...new Set(ids)];
}
async function createDraft(env, body, now) {
  const token = typeof body.contributor_token === "string" && body.contributor_token ? body.contributor_token : null;
  if (token !== null && (token.length < 8 || token.length > 32)) throw new Invalid("That contributor token does not look right.");
  const observer = await observerFromToken(env.DB, token);
  const answers = validateAnswers(body.answers ?? {});
  const firstRating = validateRating(body.first_rating);
  const language = validateLanguage(body.language);
  const photoIds = await checkPhotoIds(env.DB, body.photo_ids);
  const ref3 = parseSpotRef(body.spot);
  const nearby = await nearbyExistingSpot(env.DB, ref3);
  const spot = await resolveSpot(env.DB, ref3, now);
  const rain = spot.latitude !== null && spot.longitude !== null ? await dryStatus(spot.latitude, spot.longitude, Date.parse(now), env.RAIN_FETCH ?? fetchOpenMeteo) : UNKNOWN;
  const chosen = selectFollowups(answers, { rain: rain.status, dry_days: rain.dry_days, mm_in_window: rain.mm_in_window }, observer, [], content_default.followups, FORM_ITEMS, false).slice(
    0,
    Math.trunc(Number(content_default.followups.max_questions ?? 2))
  );
  const followups = chosen.map((f) => ({ rule_id: f.rule_id, kind: f.kind, question_key: f.question_key, question_text: questionText(f), params: f.params }));
  const visitId = `visit-${randomHex(8)}`;
  await env.DB.prepare(
    `INSERT INTO visit (visit_id, spot_id, kind, contributor_token, answered_at, answers_json, first_rating, language, photo_ids_json, followups_json, site_json, software_version)
     VALUES (?, ?, 'check', ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  ).bind(visitId, spot.spot_id, token, now, JSON.stringify(answers), firstRating, language, JSON.stringify(photoIds), JSON.stringify(followups), JSON.stringify(rain), SOFTWARE_VERSION).run();
  return {
    draft_id: visitId,
    // Not a merge: the app offers this spot first and the person decides.
    nearby_spot: nearby,
    followups: followups.map((f) => ({ rule_id: f.rule_id, question_text: f.question_text, kind: apiKind(f.kind) }))
  };
}
async function cleanFollowupAnswer(db, followup, value) {
  const text = String(typeof value === "boolean" ? value ? "yes" : "no" : value).trim().slice(0, 64);
  if (followup.kind === "photo") {
    if (FOLLOWUP_ANSWERS.has(text)) return text;
    if (!await photoExists(db, text)) throw new Invalid(`${followup.rule_id}: send the photo id from the upload, or skipped.`);
    return text;
  }
  if (!FOLLOWUP_ANSWERS.has(text)) throw new Invalid(`${followup.rule_id}: answer yes, no, cant_tell, keep, change or skipped.`);
  return text;
}
function buildRecord(opts) {
  const copied = {};
  for (const [key, value] of Object.entries(opts.answers)) copied[String(key)] = Array.isArray(value) ? value.map(String) : value;
  return {
    visit_id: opts.visit_id,
    spot: opts.spot,
    observer: opts.observer,
    answered_at: opts.answered_at,
    answers: copied,
    first_rating: opts.first_rating,
    final_rating: opts.final_rating,
    checks: [...opts.checks],
    photo_ids: opts.photo_ids.map(String),
    software_version: opts.software_version,
    language: opts.language || "en"
  };
}
async function finalize(env, body, now) {
  const draftId = String(body.draft_id ?? "");
  const row = await env.DB.prepare("SELECT * FROM visit WHERE visit_id = ?").bind(draftId).first();
  if (row === null || row.kind !== "check") throw new NotFound("We do not know that draft. Start the check again.");
  if (row.finalized_at !== null) return { visit_id: row.visit_id, spot_id: row.spot_id, fhir_saved: null };
  const followups = JSON.parse(row.followups_json);
  const byRule = new Map(followups.map((f) => [f.rule_id, f]));
  const given = body.followup_answers ?? {};
  for (const ruleId of Object.keys(given)) if (!byRule.has(ruleId)) throw new Invalid(`No follow-up called '${ruleId}' was asked in this check.`);
  const finalRating = validateRating(body.final_rating);
  const photoIds = JSON.parse(row.photo_ids_json);
  const checks = [];
  for (const f of followups) {
    const raw = given[f.rule_id];
    const answer2 = raw !== void 0 && raw !== null ? await cleanFollowupAnswer(env.DB, f, raw) : null;
    if (f.kind === "photo" && answer2 && !FOLLOWUP_ANSWERS.has(answer2)) photoIds.push(answer2);
    const detail = {};
    for (const [k, v] of Object.entries(f.params)) detail[k] = typeof v === "string" || typeof v === "number" ? v : String(v);
    detail.kind = f.kind;
    checks.push({ rule_id: f.rule_id, asked: true, question_text: f.question_text, answer: answer2, detail });
  }
  const spotRow = await getSpot(env.DB, row.spot_id);
  if (spotRow === null) throw new NotFound("The spot for this draft is gone.");
  const observer = await observerFromToken(env.DB, row.contributor_token) ?? { contributor_token: `anon${row.visit_id.slice(-12)}`, scores: [] };
  const record = buildRecord({
    visit_id: row.visit_id,
    spot: spotFromRow(spotRow),
    observer,
    answered_at: row.answered_at,
    answers: JSON.parse(row.answers_json),
    first_rating: row.first_rating,
    final_rating: finalRating,
    checks,
    photo_ids: photoIds,
    software_version: row.software_version || SOFTWARE_VERSION,
    language: row.language
  });
  const statements = checks.map(
    (c) => env.DB.prepare("INSERT INTO check_result (visit_id, rule_id, asked, question_text, answer, detail_json) VALUES (?, ?, ?, ?, ?, ?)").bind(
      row.visit_id,
      c.rule_id,
      c.asked ? 1 : 0,
      c.question_text ?? null,
      c.answer ?? null,
      JSON.stringify(c.detail)
    )
  );
  statements.push(
    env.DB.prepare("UPDATE visit SET final_rating = ?, photo_ids_json = ?, finalized_at = ? WHERE visit_id = ?").bind(finalRating, JSON.stringify([...new Set(photoIds)]), now, row.visit_id)
  );
  await env.DB.batch(statements);
  const saved = await saveVisitBundle(env.DB, record, await sittingFor(env.DB, row.contributor_token), now);
  return { visit_id: row.visit_id, spot_id: row.spot_id, fhir_saved: saved };
}
async function saveVisitBundle(db, record, sitting, now) {
  const bundle = emitVisit(record, sitting, now);
  if (checkBundle(bundle).length > 0) return false;
  await db.prepare("INSERT OR REPLACE INTO fhir_bundle (visit_id, spot_id, bundle_json, created_at) VALUES (?, ?, ?, ?)").bind(record.visit_id, record.spot.spot_id, JSON.stringify(bundle), now).run();
  return true;
}
async function loadVisitBundle(db, visitId) {
  const row = await db.prepare("SELECT bundle_json FROM fhir_bundle WHERE visit_id = ?").bind(visitId).first();
  return row === null ? null : JSON.parse(row.bundle_json);
}
async function latestBundleForSpot(db, spotId) {
  const row = await db.prepare("SELECT bundle_json FROM fhir_bundle WHERE spot_id = ? ORDER BY rowid DESC LIMIT 1").bind(spotId).first();
  return row === null ? null : JSON.parse(row.bundle_json);
}
async function latestBundle(db) {
  const row = await db.prepare("SELECT bundle_json FROM fhir_bundle ORDER BY rowid DESC LIMIT 1").first();
  return row === null ? null : JSON.parse(row.bundle_json);
}
var QUICK = {
  colour: ["clear", "muddy", "foam", "coloured", "cant_tell"],
  smell: ["none", "bad", "cant_tell"],
  pipe_running: ["present", "absent", "cant_tell"]
};
async function quickCheck(env, spotId, body, now) {
  const spot = await getSpot(env.DB, spotId);
  if (spot === null) throw new NotFound("We do not know that spot.");
  const token = typeof body.contributor_token === "string" && body.contributor_token ? body.contributor_token : null;
  await observerFromToken(env.DB, token);
  for (const [key, allowed] of Object.entries(QUICK)) {
    if (typeof body[key] !== "string" || !allowed.includes(body[key])) throw new Invalid(`${key}: pick one of ${allowed.join(", ")}.`);
  }
  const photoIds = await checkPhotoIds(env.DB, typeof body.photo_id === "string" ? [body.photo_id] : []);
  const visitId = `visit-${randomHex(8)}`;
  await env.DB.prepare(
    `INSERT INTO visit (visit_id, spot_id, kind, contributor_token, answered_at, answers_json, photo_ids_json, followups_json, site_json, finalized_at, software_version)
     VALUES (?, ?, 'quick', ?, ?, ?, ?, '[]', '{}', ?, ?)`
  ).bind(visitId, spotId, token, now, JSON.stringify({ colour: body.colour, smell: body.smell, pipe_running: body.pipe_running }), JSON.stringify(photoIds), now, SOFTWARE_VERSION).run();
  return { visit_id: visitId, spot_id: spotId };
}
function valueLabel(item, value) {
  const values = Array.isArray(value) ? value : [value];
  return values.map((v) => {
    if (item !== null && item.type === "yesno" && String(v) in YESNO_LABEL_KEYS) return LOCALE[YESNO_LABEL_KEYS[String(v)]] ?? String(v);
    for (const option of item?.options ?? []) if (String(option.value) === String(v)) return String(option.label ?? v);
    return String(v).replace(/_/g, " ");
  }).join(", ");
}
function featureName(featureId) {
  for (const f of content_default.feature_list) if (f.id === featureId) return f.name;
  return featureId;
}
function answerViews(row, observer, today) {
  const answers = JSON.parse(row.answers_json);
  return Object.entries(answers).map(([itemId, value]) => {
    const item = row.kind === "check" ? formItem(itemId) : null;
    let text;
    let feature;
    if (row.kind === "quick") {
      text = QUICK_TEXT[itemId] ?? itemId.replace(/_/g, " ");
      feature = itemId === "pipe_running" ? "pipe_running" : null;
    } else {
      text = item ? String(item.text ?? itemId) : itemId;
      feature = item && item.feature ? String(item.feature) : null;
    }
    let labelText = null;
    let passed = null;
    if (observer !== null && feature !== null) {
      const score = observer.scores.find((s) => s.feature === feature) ?? null;
      if (score !== null) {
        const label = observerLabel(score, featureName(feature), today, LOCALE);
        labelText = label.text;
        passed = label.passed;
      }
    }
    return { item_id: itemId, text, value, label: valueLabel(item, value), feature, observer_label: labelText, observer_passed: passed };
  });
}
async function checksFor(db, visitId) {
  const rows = (await db.prepare("SELECT * FROM check_result WHERE visit_id = ? ORDER BY id").bind(visitId).all()).results ?? [];
  return rows.map((c) => ({ rule_id: c.rule_id, asked: Boolean(c.asked), question_text: c.question_text, answer: c.answer, detail: JSON.parse(c.detail_json) }));
}
async function spotView(env, spotId, today) {
  const spot = await getSpot(env.DB, spotId);
  if (spot === null) throw new NotFound("We do not know that spot.");
  const visits = (await env.DB.prepare("SELECT * FROM visit WHERE spot_id = ? AND finalized_at IS NOT NULL ORDER BY answered_at DESC").bind(spotId).all()).results ?? [];
  const observers = /* @__PURE__ */ new Map();
  const views = [];
  for (const v of visits) {
    const token = v.contributor_token;
    if (token && !observers.has(token)) {
      const row = await env.DB.prepare("SELECT contributor_token, scores_json, tested_on FROM observer WHERE contributor_token = ?").bind(token).first();
      observers.set(token, row ? observerFromRow(row) : null);
    }
    const observer = token ? observers.get(token) ?? null : null;
    views.push({
      visit_id: v.visit_id,
      kind: v.kind,
      answered_at: instant(v.answered_at),
      answers: answerViews(v, observer, today),
      checks: await checksFor(env.DB, v.visit_id),
      first_rating: v.first_rating,
      final_rating: v.final_rating,
      photo_count: JSON.parse(v.photo_ids_json).length,
      observer_scored: observer !== null
    });
  }
  return {
    spot: { ...spotFromRow(spot) },
    visits: views,
    health_card: pickActions(content_default.sentences, spotId)
  };
}
var todayOf = (now) => isoDate(Date.parse(now));

// src/city.ts
var DAY_MS2 = 864e5;
var EXAMPLE_SAMPLE_AFTER = 1 * DAY_MS2;
var EXAMPLE_REPORT_AFTER = 4 * DAY_MS2;
var referralPath = (spotId) => `/api/fhir/referral/${spotId}`;
var exampleResultPath = (spotId) => `${referralPath(spotId)}/example-result`;
var bundleLinks = (ids) => ids.map((v) => `/api/fhir/Bundle/${v}`);
var FEATURE_NAMES = Object.fromEntries(content_default.feature_list.map((f) => [f.id, f.name]));
for (const item of FORM_ITEMS) if (!(item.id in FEATURE_NAMES)) FEATURE_NAMES[item.id] = String(item.text ?? item.id);
var FINDING_KEY_FOR = Object.fromEntries(FORM_ITEMS.filter((i) => i.feature).map((i) => [i.id, String(i.feature)]));
var NOTE_LABELS = (() => {
  const labels = {};
  for (const item of FORM_ITEMS) labels[item.id] = item.short_label ? String(item.short_label) : String(item.id).replace(/_/g, " ");
  for (const f of content_default.feature_list) labels[f.id] = f.name.slice(0, 1).toLowerCase() + f.name.slice(1);
  return labels;
})();
async function recordsFor(env, spots) {
  if (spots.length === 0) return [];
  const byId = new Map(spots.map((s) => [s.spot_id, s]));
  const placeholders = spots.map(() => "?").join(",");
  const rows = (await env.DB.prepare(`SELECT * FROM visit WHERE spot_id IN (${placeholders}) AND finalized_at IS NOT NULL ORDER BY answered_at`).bind(...spots.map((s) => s.spot_id)).all()).results ?? [];
  const observers = /* @__PURE__ */ new Map();
  const out = [];
  for (const v of rows) {
    let observer;
    if (!v.contributor_token) {
      observer = { contributor_token: "anonymous000", scores: [] };
    } else {
      if (!observers.has(v.contributor_token)) {
        const row = await env.DB.prepare("SELECT contributor_token, scores_json, tested_on FROM observer WHERE contributor_token = ?").bind(v.contributor_token).first();
        observers.set(v.contributor_token, row ? observerFromRow(row) : { contributor_token: v.contributor_token, scores: [] });
      }
      observer = observers.get(v.contributor_token);
    }
    out.push({
      visit_id: v.visit_id,
      spot: spotFromRow(byId.get(v.spot_id)),
      observer,
      answered_at: v.answered_at,
      answers: JSON.parse(v.answers_json),
      first_rating: v.first_rating,
      final_rating: v.final_rating,
      checks: await checksFor(env.DB, v.visit_id),
      photo_ids: JSON.parse(v.photo_ids_json),
      software_version: v.software_version
    });
  }
  return out;
}
function placementsFor(spots) {
  const out = /* @__PURE__ */ new Map();
  for (const row of spots) {
    const placed = placeSpot(spotFromRow(row), CREEKS);
    if (placed) out.set(row.spot_id, placed);
  }
  return out;
}
async function placeForSpot(env, spotId) {
  const row = await getSpot(env.DB, spotId);
  if (row === null) throw new NotFound("We do not know that spot.");
  const placed = placeSpot(spotFromRow(row), CREEKS);
  if (placed === null) return null;
  return { creek_slug: placed.creek.slug, creek_name: placed.creek.name, reach_slug: placed.reach?.slug ?? null, reach_name: placed.reach?.name ?? null };
}
function findingView(f, spotNames) {
  return {
    spot_id: f.spot_id,
    spot_name: spotNames.get(f.spot_id) ?? f.spot_id,
    feature: f.feature,
    feature_name: FEATURE_NAMES[f.feature] ?? f.feature,
    observers: f.observers.length,
    passed_observers: f.passed_observers.length,
    first_seen: f.first_seen,
    last_seen: f.last_seen,
    visit_ids: f.visit_ids,
    fhir: bundleLinks(f.visit_ids)
  };
}
function noteView(n) {
  return {
    reach_slug: n.reach_slug,
    reach_name: n.reach_name,
    from_reach_slug: n.from_reach_slug,
    from_reach_name: n.from_reach_name,
    feature: n.feature,
    feature_name: FEATURE_NAMES[n.feature] ?? n.feature,
    line: n.line,
    observers: n.observers,
    visit_ids: n.visit_ids,
    fhir: bundleLinks(n.visit_ids)
  };
}
async function cityView(env, creekRef, today) {
  let creek = creekBySlug(creekRef);
  const all = await allSpots(env.DB);
  const placements = placementsFor(all);
  let spots;
  if (creek !== null) {
    const slug = creek.slug;
    spots = all.filter((s) => placements.get(s.spot_id)?.creek.slug === slug);
  } else {
    spots = all.filter((s) => s.creek_id === creekRef);
    if (spots.length === 0) throw new NotFound("We have no record for that creek yet.");
    const placedOn = new Set(spots.map((s) => placements.get(s.spot_id)?.creek.slug).filter((x) => Boolean(x)));
    creek = placedOn.size === 1 ? creekBySlug([...placedOn][0]) : null;
  }
  const flagged = spots.filter((s) => looksLikeATestName(s.spot_name));
  const real = spots.filter((s) => !flagged.includes(s));
  const spotNames = new Map(spots.map((s) => [s.spot_id, s.spot_name]));
  const visits = await recordsFor(env, real);
  const findings = findingsFromVisits(visits, FINDING_KEY_FOR);
  const needs = needsFromFindings(findings, content_default.sentences);
  const pipes = pipesWorthTesting(visits, today);
  let notes = [];
  const reaches = [];
  let unplaced = 0;
  if (creek !== null) {
    const reachOfSpot = {};
    for (const s of real) if (placements.has(s.spot_id)) reachOfSpot[s.spot_id] = placements.get(s.spot_id).reach;
    notes = notesBelow(findings, reachOfSpot, creek, NOTE_LABELS);
    const visitsAt = /* @__PURE__ */ new Map();
    for (const v of visits) visitsAt.set(v.spot.spot_id, (visitsAt.get(v.spot.spot_id) ?? 0) + 1);
    for (const reach of creek.reaches) {
      const here2 = real.filter((s) => reachOfSpot[s.spot_id] === reach);
      reaches.push({
        slug: reach.slug,
        name: reach.name,
        flows_into: reach.flows_into,
        flows_into_name: reach.flows_into ? reachOf(creek, reach.flows_into)?.name ?? null : null,
        spots: here2.length,
        visits: here2.reduce((n, s) => n + (visitsAt.get(s.spot_id) ?? 0), 0),
        notes: notes.filter((n) => n.reach_slug === reach.slug).map(noteView)
      });
    }
    unplaced = real.filter((s) => !reachOfSpot[s.spot_id]).length;
  }
  const sentences = content_default.sentences;
  return {
    creek_id: creekRef,
    creek_slug: creek?.slug ?? null,
    creek_name: creek ? creek.name : real.length ? real[0].creek_name : creekRef,
    visits: visits.length,
    visit_ids: visits.map((v) => v.visit_id),
    fhir: bundleLinks(visits.map((v) => v.visit_id)),
    spots: real.length,
    findings: findings.map((f) => findingView(f, spotNames)),
    needs: needs.map((n) => ({ sentence_id: n.sentence_id, text: n.text, source: n.source, because: n.because.map((b) => FEATURE_NAMES[b] ?? b), visit_ids: n.visit_ids, fhir: bundleLinks(n.visit_ids) })),
    pipes_worth_testing: pipes.map((p) => ({
      spot_id: p.spot_id,
      spot_name: p.spot_name,
      observers: p.observers.length,
      dry_days: p.dry_days,
      last_seen: p.last_seen,
      visit_ids: p.visit_ids,
      fhir: bundleLinks(p.visit_ids),
      referral: referralPath(p.spot_id),
      example_result: exampleResultPath(p.spot_id)
    })),
    flagged_spots: flagged.map((s) => ({ spot_id: s.spot_id, spot_name: s.spot_name, why: "the name reads like a test" })),
    measures_waiting_for_approval: sentences.length === 0 || sentences.every((s) => s.approved !== true),
    reaches,
    downstream_notes: notes.map(noteView),
    unplaced_spots: unplaced
  };
}
async function notesForSpot(env, spotId, today) {
  const place = await placeForSpot(env, spotId);
  if (place === null || place.reach_slug === null) return [];
  const view = await cityView(env, place.creek_slug, today);
  return view.downstream_notes.filter((n) => n.reach_slug === place.reach_slug);
}
async function creeksView(env) {
  const all = await allSpots(env.DB);
  const placements = placementsFor(all);
  const groups = /* @__PURE__ */ new Map();
  for (const row of all) {
    if (looksLikeATestName(row.spot_name)) continue;
    const placed = placements.get(row.spot_id);
    const key = placed ? placed.creek.slug : row.creek_id;
    if (!groups.has(key)) groups.set(key, { creek: key, creek_slug: placed ? placed.creek.slug : null, name: placed ? placed.creek.name : row.creek_name, spots: [] });
    groups.get(key).spots.push(row);
  }
  const out = [];
  for (const group of groups.values()) {
    const visits = await recordsFor(env, group.spots);
    out.push({
      creek: group.creek,
      creek_slug: group.creek_slug,
      name: group.name,
      spots: group.spots.length,
      visits: visits.length,
      visit_ids: visits.map((v) => v.visit_id),
      fhir: bundleLinks(visits.map((v) => v.visit_id)),
      record: `/api/city/${group.creek}`
    });
  }
  out.sort((a, b) => Number(a.creek_slug === null) - Number(b.creek_slug === null) || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
  return { creeks: out };
}
async function realSpotsOnTheCreekOf(env, spotId) {
  const spot = await getSpot(env.DB, spotId);
  if (spot === null) throw new NotFound("We do not know that spot.");
  const all = await allSpots(env.DB);
  const placements = placementsFor(all);
  const mine = placements.get(spotId);
  const spots = mine ? all.filter((s) => placements.get(s.spot_id)?.creek.slug === mine.creek.slug) : all.filter((s) => s.creek_id === spot.creek_id);
  return spots.filter((s) => !looksLikeATestName(s.spot_name));
}
async function pipeCaseFor(env, spotId, today) {
  const visits = await recordsFor(env, await realSpotsOnTheCreekOf(env, spotId));
  for (const pipe of pipesWorthTesting(visits, today)) if (pipe.spot_id === spotId) return pipe;
  throw new NotFound("No referral: this pipe is not on the list. Two different people who both passed the pipe feature have to report it running in dry weather.");
}
async function referralView(env, spotId, now) {
  const pipe = await pipeCaseFor(env, spotId, now.slice(0, 10));
  const bundles = {};
  for (const visitId of pipe.visit_ids) {
    const bundle = await loadVisitBundle(env.DB, visitId);
    if (bundle) bundles[visitId] = bundle;
  }
  try {
    return referralBundle(pipe, bundles, now);
  } catch (err) {
    if (err instanceof ReferralError) throw new NotFound(`No referral could be built: ${err.message}`);
    throw err;
  }
}
async function exampleResultView(env, spotId, now) {
  const referral = await referralView(env, spotId, now);
  const at = Date.parse(now);
  return exampleLabResult(referral, new Date(at + EXAMPLE_SAMPLE_AFTER).toISOString(), new Date(at + EXAMPLE_REPORT_AFTER).toISOString());
}

// src/uploads.ts
var MAX_UPLOAD_BYTES = 8 * 1024 * 1024;
var KEEP_DAYS = 30;
var KEEP_SECONDS = KEEP_DAYS * 24 * 3600;
var TooLarge = class extends Error {
};
function sniffImage(head) {
  if (head[0] === 255 && head[1] === 216 && head[2] === 255) return "image/jpeg";
  if (head[0] === 137 && head[1] === 80 && head[2] === 78 && head[3] === 71 && head[4] === 13 && head[5] === 10 && head[6] === 26 && head[7] === 10) return "image/png";
  if (String.fromCharCode(...head.slice(0, 4)) === "RIFF" && String.fromCharCode(...head.slice(8, 12)) === "WEBP") return "image/webp";
  return null;
}
function stripJpeg(bytes) {
  const damaged = () => new Invalid("That photo could not be read. Send it again, or another one.");
  const out = [bytes.slice(0, 2)];
  let i = 2;
  while (i < bytes.length) {
    if (bytes[i] !== 255) throw damaged();
    let m = i + 1;
    while (m < bytes.length && bytes[m] === 255) m += 1;
    if (m >= bytes.length) throw damaged();
    const marker = bytes[m];
    i = m + 1;
    if (marker === 217) {
      out.push(Uint8Array.of(255, 217));
      return concat(out);
    }
    if (marker === 216 || marker >= 208 && marker <= 215 || marker === 1) {
      out.push(Uint8Array.of(255, marker));
      continue;
    }
    if (marker === 0 || i + 2 > bytes.length) throw damaged();
    const length = bytes[i] << 8 | bytes[i + 1];
    const end = i + length;
    if (length < 2 || end > bytes.length) throw damaged();
    const metadata = marker >= 225 && marker <= 239 || marker === 254;
    if (!metadata) out.push(Uint8Array.of(255, marker), bytes.slice(i, end));
    i = end;
    if (marker === 218) {
      let j = i;
      while (j + 1 < bytes.length && !(bytes[j] === 255 && bytes[j + 1] !== 0 && !(bytes[j + 1] >= 208 && bytes[j + 1] <= 215))) j += 1;
      if (j + 1 >= bytes.length) throw damaged();
      out.push(bytes.slice(i, j));
      i = j;
    }
  }
  throw damaged();
}
var PNG_DROP = /* @__PURE__ */ new Set(["tEXt", "zTXt", "iTXt", "eXIf", "tIME"]);
function stripPng(bytes) {
  const out = [bytes.slice(0, 8)];
  let i = 8;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  while (i + 12 <= bytes.length) {
    const length = view.getUint32(i, false);
    const type = String.fromCharCode(...bytes.slice(i + 4, i + 8));
    const end = i + 12 + length;
    if (!PNG_DROP.has(type)) out.push(bytes.slice(i, Math.min(end, bytes.length)));
    i = end;
  }
  return concat(out);
}
function stripWebp(bytes) {
  const kept = [];
  let i = 12;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  while (i + 8 <= bytes.length) {
    const fourcc = String.fromCharCode(...bytes.slice(i, i + 4));
    const size = view.getUint32(i + 4, true);
    const end = i + 8 + size + size % 2;
    if (fourcc !== "EXIF" && fourcc !== "XMP ") kept.push(bytes.slice(i, Math.min(end, bytes.length)));
    i = end;
  }
  const body = concat(kept);
  const header = new Uint8Array(12);
  header.set(bytes.slice(0, 4));
  new DataView(header.buffer).setUint32(4, 4 + body.length, true);
  header.set(bytes.slice(8, 12), 8);
  return concat([header, body]);
}
function concat(parts) {
  const total = parts.reduce((n, p) => n + p.length, 0);
  const out = new Uint8Array(total);
  let at = 0;
  for (const p of parts) {
    out.set(p, at);
    at += p.length;
  }
  return out;
}
function stripMetadata(bytes, type) {
  if (type === "image/jpeg") return stripJpeg(bytes);
  if (type === "image/png") return stripPng(bytes);
  return stripWebp(bytes);
}
function urlSafeToken(bytes) {
  const raw = crypto.getRandomValues(new Uint8Array(bytes));
  return btoa(String.fromCharCode(...raw)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
async function storeUpload(env, request, now) {
  const form = await request.formData().catch(() => null);
  const file = form?.get("file");
  if (!(file instanceof File)) throw new Invalid("Send the photo as a form field called file.");
  if (file.size > MAX_UPLOAD_BYTES) throw new TooLarge("That photo is over 8 MB. Send a smaller one.");
  const bytes = new Uint8Array(await file.arrayBuffer());
  if (bytes.length > MAX_UPLOAD_BYTES) throw new TooLarge("That photo is over 8 MB. Send a smaller one.");
  const type = sniffImage(bytes.slice(0, 16));
  if (type === null) throw new Invalid("Only JPEG, PNG or WebP photos can be uploaded.");
  const clean = stripMetadata(bytes, type);
  const photoId = `up-${randomHex(8)}`;
  const token = urlSafeToken(24);
  await env.PHOTOS.put(`photo:${photoId}`, clean, { expirationTtl: KEEP_SECONDS, metadata: { contentType: type } });
  await env.DB.prepare("INSERT INTO upload (photo_id, token_hash, content_type, size_bytes, created_at) VALUES (?, ?, ?, ?, ?)").bind(photoId, sha256Hex(token), type, clean.length, now).run();
  return { photo_id: photoId, token };
}
function uploadCutoff(now) {
  return new Date(Date.parse(now) - KEEP_SECONDS * 1e3).toISOString().replace(/\.\d{3}Z$/, "Z");
}
async function purgeUploads(db, now) {
  const gone = await db.prepare("DELETE FROM upload WHERE created_at <= ?").bind(uploadCutoff(now)).run();
  return Number(gone.meta.changes ?? 0);
}
function sameDigest(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}
async function photoResponse(env, photoId, token) {
  const row = await env.DB.prepare("SELECT token_hash, content_type FROM upload WHERE photo_id = ?").bind(photoId).first();
  if (row === null || !token || !sameDigest(sha256Hex(token), row.token_hash)) throw new NotFound("Not found.");
  const stored2 = await env.PHOTOS.get(`photo:${photoId}`, "arrayBuffer");
  if (stored2 === null) throw new NotFound("Not found.");
  return new Response(stored2, {
    status: 200,
    headers: { "content-type": row.content_type, "cache-control": "private, no-store", "content-disposition": "inline", "x-content-type-options": "nosniff" }
  });
}

// ../fhir/golden/visit-strawberry-creek-1.json
var visit_strawberry_creek_1_default = {
  entry: [
    {
      fullUrl: "https://github.com/alejandro-publius/second-look/fhir/Organization/sl-org",
      resource: {
        active: true,
        id: "sl-org",
        identifier: [
          {
            system: "https://github.com/alejandro-publius/second-look/fhir/org",
            value: "second-look"
          }
        ],
        name: "Second Look project",
        resourceType: "Organization",
        text: {
          div: '<div xmlns="http://www.w3.org/1999/xhtml"><p>Second Look project. Issues the observer test and keeps the record.</p></div>',
          status: "generated"
        }
      }
    },
    {
      fullUrl: "https://github.com/alejandro-publius/second-look/fhir/Device/sl-device",
      resource: {
        deviceName: [
          {
            name: "Second Look web app",
            type: "user-friendly-name"
          }
        ],
        id: "sl-device",
        identifier: [
          {
            system: "https://github.com/alejandro-publius/second-look/fhir/device",
            value: "second-look-web"
          }
        ],
        resourceType: "Device",
        status: "active",
        text: {
          div: '<div xmlns="http://www.w3.org/1999/xhtml"><p>Second Look web app, version 0.1.0. Assembled this record.</p></div>',
          status: "generated"
        },
        type: {
          coding: [
            {
              code: "software",
              display: "Second Look software",
              system: "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look"
            }
          ]
        },
        version: [
          {
            value: "0.1.0"
          }
        ]
      }
    },
    {
      fullUrl: "https://github.com/alejandro-publius/second-look/fhir/Location/sl-loc-strawberry-creek",
      resource: {
        id: "sl-loc-strawberry-creek",
        identifier: [
          {
            system: "https://github.com/alejandro-publius/second-look/fhir/location-id",
            value: "strawberry-creek"
          }
        ],
        meta: {
          profile: [
            "http://hl7.eu/fhir/ig/oah/StructureDefinition/location-oah"
          ]
        },
        mode: "instance",
        name: "Strawberry Creek",
        resourceType: "Location",
        text: {
          div: '<div xmlns="http://www.w3.org/1999/xhtml"><p>Strawberry Creek. A creek used in Second Look creek checks.</p></div>',
          status: "generated"
        },
        type: [
          {
            coding: [
              {
                code: "420531007",
                display: "River",
                system: "http://snomed.info/sct"
              }
            ]
          }
        ]
      }
    },
    {
      fullUrl: "https://github.com/alejandro-publius/second-look/fhir/Location/sl-loc-campus-reach",
      resource: {
        id: "sl-loc-campus-reach",
        identifier: [
          {
            system: "https://github.com/alejandro-publius/second-look/fhir/location-id",
            value: "campus-reach"
          }
        ],
        meta: {
          profile: [
            "http://hl7.eu/fhir/ig/oah/StructureDefinition/location-oah"
          ]
        },
        mode: "instance",
        name: "Strawberry Creek, campus reach",
        partOf: {
          reference: "Location/sl-loc-strawberry-creek"
        },
        resourceType: "Location",
        text: {
          div: '<div xmlns="http://www.w3.org/1999/xhtml"><p>Strawberry Creek, campus reach. A reach used in Second Look creek checks.</p></div>',
          status: "generated"
        },
        type: [
          {
            coding: [
              {
                code: "420531007",
                display: "River",
                system: "http://snomed.info/sct"
              }
            ]
          }
        ]
      }
    },
    {
      fullUrl: "https://github.com/alejandro-publius/second-look/fhir/Location/sl-loc-spot-1",
      resource: {
        id: "sl-loc-spot-1",
        identifier: [
          {
            system: "https://github.com/alejandro-publius/second-look/fhir/location-id",
            value: "spot-1"
          }
        ],
        meta: {
          profile: [
            "http://hl7.eu/fhir/ig/oah/StructureDefinition/location-oah"
          ]
        },
        mode: "instance",
        name: "Strawberry Creek, campus reach, spot 1",
        partOf: {
          reference: "Location/sl-loc-campus-reach"
        },
        position: {
          latitude: 37.8719,
          longitude: -122.2585
        },
        resourceType: "Location",
        text: {
          div: '<div xmlns="http://www.w3.org/1999/xhtml"><p>Strawberry Creek, campus reach, spot 1. A spot used in Second Look creek checks.</p></div>',
          status: "generated"
        },
        type: [
          {
            coding: [
              {
                code: "420531007",
                display: "River",
                system: "http://snomed.info/sct"
              }
            ]
          }
        ]
      }
    },
    {
      fullUrl: "https://github.com/alejandro-publius/second-look/fhir/Practitioner/sl-practitioner-20d03d930b1b",
      resource: {
        active: true,
        id: "sl-practitioner-20d03d930b1b",
        identifier: [
          {
            system: "https://github.com/alejandro-publius/second-look/fhir/contributor-token",
            value: "sl-practitioner-20d03d930b1b"
          }
        ],
        qualification: [
          {
            code: {
              coding: [
                {
                  code: "second-look-test",
                  display: "Second Look observer test",
                  system: "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look"
                }
              ]
            },
            issuer: {
              reference: "Organization/sl-org"
            },
            period: {
              end: "2026-12-22",
              start: "2026-09-23"
            }
          }
        ],
        resourceType: "Practitioner",
        text: {
          div: '<div xmlns="http://www.w3.org/1999/xhtml"><p>Volunteer observer, known only by a random contributor token. Took the Second Look test on 2026-09-23. The score counts until 2026-12-22.</p></div>',
          status: "generated"
        }
      }
    },
    {
      fullUrl: "https://github.com/alejandro-publius/second-look/fhir/QuestionnaireResponse/sl-qr-test-test-sitting-0001",
      resource: {
        author: {
          reference: "Practitioner/sl-practitioner-20d03d930b1b"
        },
        authored: "2026-09-23T17:05:00Z",
        id: "sl-qr-test-test-sitting-0001",
        identifier: {
          system: "https://github.com/alejandro-publius/second-look/fhir/qr",
          value: "test-sitting-0001"
        },
        item: [
          {
            item: [
              {
                answer: [
                  {
                    valueInteger: 4
                  }
                ],
                linkId: "artificial_bank.score"
              }
            ],
            linkId: "artificial_bank"
          },
          {
            item: [
              {
                answer: [
                  {
                    valueInteger: 2
                  }
                ],
                linkId: "dug_out_channel.score"
              }
            ],
            linkId: "dug_out_channel"
          },
          {
            item: [
              {
                answer: [
                  {
                    valueInteger: 3
                  }
                ],
                linkId: "invasive_plant.score"
              }
            ],
            linkId: "invasive_plant"
          },
          {
            item: [
              {
                answer: [
                  {
                    valueInteger: 4
                  }
                ],
                linkId: "pipe_running.score"
              }
            ],
            linkId: "pipe_running"
          }
        ],
        questionnaire: "https://github.com/alejandro-publius/second-look/fhir/Questionnaire/sl-questionnaire-test",
        resourceType: "QuestionnaireResponse",
        status: "completed",
        text: {
          div: '<div xmlns="http://www.w3.org/1999/xhtml"><p>Observer test sitting, scored by code: artificial bank 4 of 4, dug out channel 2 of 4, invasive plant 3 of 4, pipe running 4 of 4.</p></div>',
          status: "generated"
        }
      }
    },
    {
      fullUrl: "https://github.com/alejandro-publius/second-look/fhir/QuestionnaireResponse/sl-qr-visit-visit-0001",
      resource: {
        author: {
          reference: "Practitioner/sl-practitioner-20d03d930b1b"
        },
        authored: "2026-09-24T16:40:00Z",
        id: "sl-qr-visit-visit-0001",
        identifier: {
          system: "https://github.com/alejandro-publius/second-look/fhir/qr",
          value: "visit-0001"
        },
        item: [
          {
            answer: [
              {
                valueCoding: {
                  code: "u-shape",
                  display: "U shaped channel",
                  system: "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look"
                }
              }
            ],
            linkId: "channel_form"
          },
          {
            answer: [
              {
                valueCoding: {
                  code: "present",
                  display: "Present",
                  system: "http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu"
                }
              }
            ],
            linkId: "bank_type"
          },
          {
            answer: [
              {
                valueCoding: {
                  code: "cant-tell",
                  display: "Can't tell",
                  system: "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look"
                }
              }
            ],
            linkId: "draining_pipes"
          },
          {
            answer: [
              {
                valueDecimal: 0.2
              }
            ],
            linkId: "water_height_m"
          },
          {
            answer: [
              {
                valueCoding: {
                  code: "present",
                  display: "Present",
                  system: "http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu"
                }
              }
            ],
            linkId: "invasive_species"
          },
          {
            answer: [
              {
                valueCoding: {
                  code: "moderate",
                  display: "Moderate overall rating",
                  system: "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look"
                }
              }
            ],
            linkId: "overall_rating"
          }
        ],
        language: "en",
        questionnaire: "https://github.com/alejandro-publius/second-look/fhir/Questionnaire/sl-questionnaire-check",
        resourceType: "QuestionnaireResponse",
        status: "completed",
        text: {
          div: '<div xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en"><p>Creek check at Strawberry Creek, campus reach, spot 1 on 2026-09-24T16:40:00Z, 6 items answered.</p></div>',
          status: "generated"
        }
      }
    },
    {
      fullUrl: "https://github.com/alejandro-publius/second-look/fhir/Observation/sl-obs-visit-0001-channel-form",
      resource: {
        category: [
          {
            coding: [
              {
                code: "morophology",
                display: "Morphology of the streams",
                system: "http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu"
              }
            ]
          }
        ],
        code: {
          coding: [
            {
              code: "morophology",
              display: "Morphology of the streams",
              system: "http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu"
            }
          ],
          text: "Channel Form"
        },
        derivedFrom: [
          {
            reference: "QuestionnaireResponse/sl-qr-visit-visit-0001"
          }
        ],
        effectiveDateTime: "2026-09-24T16:40:00Z",
        id: "sl-obs-visit-0001-channel-form",
        identifier: [
          {
            system: "https://github.com/alejandro-publius/second-look/fhir/observation",
            value: "visit-0001-channel_form"
          }
        ],
        meta: {
          profile: [
            "http://hl7.eu/fhir/ig/oah/StructureDefinition/observation-indicators-oah"
          ]
        },
        performer: [
          {
            reference: "Practitioner/sl-practitioner-20d03d930b1b"
          }
        ],
        resourceType: "Observation",
        status: "final",
        subject: {
          reference: "Location/sl-loc-spot-1"
        },
        text: {
          div: '<div xmlns="http://www.w3.org/1999/xhtml"><p>Channel Form at Strawberry Creek, campus reach, spot 1: U shaped channel.</p></div>',
          status: "generated"
        },
        valueCodeableConcept: {
          coding: [
            {
              code: "u-shape",
              display: "U shaped channel",
              system: "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look"
            }
          ]
        }
      }
    },
    {
      fullUrl: "https://github.com/alejandro-publius/second-look/fhir/Observation/sl-obs-visit-0001-bank-type",
      resource: {
        category: [
          {
            coding: [
              {
                code: "morophology",
                display: "Morphology of the streams",
                system: "http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu"
              }
            ]
          }
        ],
        code: {
          coding: [
            {
              code: "artificial-bank",
              display: "Artificial bank",
              system: "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look"
            }
          ],
          text: "Artificial bank (Bank Type)"
        },
        derivedFrom: [
          {
            reference: "QuestionnaireResponse/sl-qr-visit-visit-0001"
          }
        ],
        effectiveDateTime: "2026-09-24T16:40:00Z",
        id: "sl-obs-visit-0001-bank-type",
        identifier: [
          {
            system: "https://github.com/alejandro-publius/second-look/fhir/observation",
            value: "visit-0001-bank_type"
          }
        ],
        meta: {
          profile: [
            "http://hl7.eu/fhir/ig/oah/StructureDefinition/observation-indicators-oah"
          ]
        },
        performer: [
          {
            reference: "Practitioner/sl-practitioner-20d03d930b1b"
          }
        ],
        resourceType: "Observation",
        status: "final",
        subject: {
          reference: "Location/sl-loc-spot-1"
        },
        text: {
          div: '<div xmlns="http://www.w3.org/1999/xhtml"><p>Artificial bank (Bank Type) at Strawberry Creek, campus reach, spot 1: Present. The observer scored 4 of 4 on this feature, tested 2026-09-23.</p></div>',
          status: "generated"
        },
        valueCodeableConcept: {
          coding: [
            {
              code: "present",
              display: "Present",
              system: "http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu"
            }
          ]
        }
      }
    },
    {
      fullUrl: "https://github.com/alejandro-publius/second-look/fhir/Observation/sl-obs-visit-0001-draining-pipes",
      resource: {
        category: [
          {
            coding: [
              {
                code: "hydrology",
                display: "Hydrology of the stream",
                system: "http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu"
              }
            ]
          }
        ],
        code: {
          coding: [
            {
              code: "pipe-running",
              display: "Pipe running",
              system: "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look"
            }
          ],
          text: "Pipe running (Draining Pipes)"
        },
        derivedFrom: [
          {
            reference: "QuestionnaireResponse/sl-qr-visit-visit-0001"
          }
        ],
        effectiveDateTime: "2026-09-24T16:40:00Z",
        id: "sl-obs-visit-0001-draining-pipes",
        identifier: [
          {
            system: "https://github.com/alejandro-publius/second-look/fhir/observation",
            value: "visit-0001-draining_pipes"
          }
        ],
        meta: {
          profile: [
            "http://hl7.eu/fhir/ig/oah/StructureDefinition/observation-indicators-oah"
          ]
        },
        performer: [
          {
            reference: "Practitioner/sl-practitioner-20d03d930b1b"
          }
        ],
        resourceType: "Observation",
        status: "final",
        subject: {
          reference: "Location/sl-loc-spot-1"
        },
        text: {
          div: `<div xmlns="http://www.w3.org/1999/xhtml"><p>Pipe running (Draining Pipes) at Strawberry Creek, campus reach, spot 1: Can't tell. The observer scored 4 of 4 on this feature, tested 2026-09-23.</p></div>`,
          status: "generated"
        },
        valueCodeableConcept: {
          coding: [
            {
              code: "cant-tell",
              display: "Can't tell",
              system: "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look"
            }
          ]
        }
      }
    },
    {
      fullUrl: "https://github.com/alejandro-publius/second-look/fhir/Observation/sl-obs-visit-0001-water-height-m",
      resource: {
        category: [
          {
            coding: [
              {
                code: "hydrology",
                display: "Hydrology of the stream",
                system: "http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu"
              }
            ]
          }
        ],
        code: {
          coding: [
            {
              code: "hydrology",
              display: "Hydrology of the stream",
              system: "http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu"
            }
          ],
          text: "Water height"
        },
        derivedFrom: [
          {
            reference: "QuestionnaireResponse/sl-qr-visit-visit-0001"
          }
        ],
        effectiveDateTime: "2026-09-24T16:40:00Z",
        id: "sl-obs-visit-0001-water-height-m",
        identifier: [
          {
            system: "https://github.com/alejandro-publius/second-look/fhir/observation",
            value: "visit-0001-water_height_m"
          }
        ],
        meta: {
          profile: [
            "http://hl7.eu/fhir/ig/oah/StructureDefinition/observation-indicators-oah"
          ]
        },
        performer: [
          {
            reference: "Practitioner/sl-practitioner-20d03d930b1b"
          }
        ],
        resourceType: "Observation",
        status: "final",
        subject: {
          reference: "Location/sl-loc-spot-1"
        },
        text: {
          div: '<div xmlns="http://www.w3.org/1999/xhtml"><p>Water height at Strawberry Creek, campus reach, spot 1: 0.2 metre.</p></div>',
          status: "generated"
        },
        valueQuantity: {
          code: "m",
          system: "http://unitsofmeasure.org",
          unit: "metre",
          value: 0.2
        }
      }
    },
    {
      fullUrl: "https://github.com/alejandro-publius/second-look/fhir/Observation/sl-obs-visit-0001-invasive-species",
      resource: {
        category: [
          {
            coding: [
              {
                code: "invasiveOrganisms",
                display: "Invasive invertebrate, plants and fish",
                system: "http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu"
              }
            ]
          }
        ],
        code: {
          coding: [
            {
              code: "invasive-plant",
              display: "Invasive plant",
              system: "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look"
            }
          ],
          text: "Invasive plant (Invasive Species)"
        },
        derivedFrom: [
          {
            reference: "QuestionnaireResponse/sl-qr-visit-visit-0001"
          }
        ],
        effectiveDateTime: "2026-09-24T16:40:00Z",
        id: "sl-obs-visit-0001-invasive-species",
        identifier: [
          {
            system: "https://github.com/alejandro-publius/second-look/fhir/observation",
            value: "visit-0001-invasive_species"
          }
        ],
        meta: {
          profile: [
            "http://hl7.eu/fhir/ig/oah/StructureDefinition/observation-indicators-oah"
          ]
        },
        performer: [
          {
            reference: "Practitioner/sl-practitioner-20d03d930b1b"
          }
        ],
        resourceType: "Observation",
        status: "final",
        subject: {
          reference: "Location/sl-loc-spot-1"
        },
        text: {
          div: '<div xmlns="http://www.w3.org/1999/xhtml"><p>Invasive plant (Invasive Species) at Strawberry Creek, campus reach, spot 1: Present. The observer scored 3 of 4 on this feature, tested 2026-09-23.</p></div>',
          status: "generated"
        },
        valueCodeableConcept: {
          coding: [
            {
              code: "present",
              display: "Present",
              system: "http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu"
            }
          ]
        }
      }
    },
    {
      fullUrl: "https://github.com/alejandro-publius/second-look/fhir/Observation/sl-obs-visit-0001-overall-rating",
      resource: {
        code: {
          coding: [
            {
              code: "overall-rating",
              display: "Overall rating",
              system: "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look"
            }
          ],
          text: "Overall rating"
        },
        component: [
          {
            code: {
              coding: [
                {
                  code: "first-rating",
                  display: "First overall rating",
                  system: "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look"
                }
              ]
            },
            valueCodeableConcept: {
              coding: [
                {
                  code: "good",
                  display: "Good overall rating",
                  system: "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look"
                }
              ]
            }
          }
        ],
        derivedFrom: [
          {
            reference: "QuestionnaireResponse/sl-qr-visit-visit-0001"
          }
        ],
        effectiveDateTime: "2026-09-24T16:40:00Z",
        id: "sl-obs-visit-0001-overall-rating",
        identifier: [
          {
            system: "https://github.com/alejandro-publius/second-look/fhir/observation",
            value: "visit-0001-overall_rating"
          }
        ],
        meta: {
          profile: [
            "http://hl7.eu/fhir/ig/oah/StructureDefinition/observation-indicators-oah"
          ]
        },
        performer: [
          {
            reference: "Practitioner/sl-practitioner-20d03d930b1b"
          }
        ],
        resourceType: "Observation",
        status: "final",
        subject: {
          reference: "Location/sl-loc-spot-1"
        },
        text: {
          div: '<div xmlns="http://www.w3.org/1999/xhtml"><p>Overall rating at Strawberry Creek, campus reach, spot 1: Moderate overall rating. The first answer was Good overall rating. On the rating check the volunteer changed it to Moderate overall rating.</p></div>',
          status: "generated"
        },
        valueCodeableConcept: {
          coding: [
            {
              code: "moderate",
              display: "Moderate overall rating",
              system: "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look"
            }
          ]
        }
      }
    },
    {
      fullUrl: "https://github.com/alejandro-publius/second-look/fhir/Provenance/sl-provenance-visit-0001",
      resource: {
        agent: [
          {
            type: {
              coding: [
                {
                  code: "author",
                  system: "http://terminology.hl7.org/CodeSystem/provenance-participant-type"
                }
              ]
            },
            who: {
              reference: "Practitioner/sl-practitioner-20d03d930b1b"
            }
          },
          {
            type: {
              coding: [
                {
                  code: "assembler",
                  system: "http://terminology.hl7.org/CodeSystem/provenance-participant-type"
                }
              ]
            },
            who: {
              reference: "Device/sl-device"
            }
          }
        ],
        entity: [
          {
            role: "source",
            what: {
              reference: "QuestionnaireResponse/sl-qr-visit-visit-0001"
            }
          },
          {
            role: "source",
            what: {
              reference: "QuestionnaireResponse/sl-qr-test-test-sitting-0001"
            }
          }
        ],
        id: "sl-provenance-visit-0001",
        recorded: "2026-09-24T16:41:00Z",
        resourceType: "Provenance",
        target: [
          {
            reference: "Observation/sl-obs-visit-0001-channel-form"
          },
          {
            reference: "Observation/sl-obs-visit-0001-bank-type"
          },
          {
            reference: "Observation/sl-obs-visit-0001-draining-pipes"
          },
          {
            reference: "Observation/sl-obs-visit-0001-water-height-m"
          },
          {
            reference: "Observation/sl-obs-visit-0001-invasive-species"
          },
          {
            reference: "Observation/sl-obs-visit-0001-overall-rating"
          }
        ],
        text: {
          div: '<div xmlns="http://www.w3.org/1999/xhtml"><p>6 observations from one creek check, answered by the volunteer and assembled by the Second Look software. The sources are the visit and the observer test sitting.</p></div>',
          status: "generated"
        }
      }
    }
  ],
  id: "sl-visit-visit-0001",
  resourceType: "Bundle",
  timestamp: "2026-09-24T16:41:00Z",
  type: "collection"
};

// src/two.ts
var THEIRS_LOCATION = "Location/Loc-Almyros";
var THEIRS_CODE = "dissolved-oxygen";
function theirsQuery(env) {
  return { subject: THEIRS_LOCATION, code: `${OAH_SYSTEM}|${env.SANDBOX_THEIRS_CODE ?? THEIRS_CODE}`, _sort: "-date", _count: "1" };
}
function observations(bundle) {
  return (bundle.entry ?? []).map((e) => e.resource).filter((r) => r && r.resourceType === "Observation");
}
function placeOf(bundle, obs) {
  const reference = String((obs?.subject ?? {}).reference ?? "");
  if (!reference.startsWith("Location/")) return null;
  const id = reference.slice("Location/".length);
  for (const e of bundle.entry ?? []) {
    const r = e.resource;
    if (r && r.resourceType === "Location" && r.id === id && typeof r.name === "string") return r.name;
  }
  return null;
}
async function ours(env) {
  const stored2 = await latestBundle(env.DB);
  const bundle = stored2 ?? visit_strawberry_creek_1_default;
  const list = observations(bundle);
  let pick = list[0] ?? null;
  for (const obs of list) {
    const coding2 = (obs.code?.coding ?? [])[0];
    if (coding2 && coding2.system === SL_SYSTEM) {
      pick = obs;
      break;
    }
  }
  return { observation: pick, example: stored2 === null, place: placeOf(bundle, pick) };
}
function theirsCacheKey(env) {
  return `theirs-${sha256Hex(JSON.stringify(theirsQuery(env))).slice(0, 16)}`;
}
async function theirs(env) {
  const cached = await env.DB.prepare("SELECT body, fetched_at FROM sandbox_cache WHERE cache_key = ?").bind(theirsCacheKey(env)).first();
  if (cached === null) return { observation: null, status: "down", fetched_at: "" };
  return { observation: JSON.parse(cached.body), status: "cached", fetched_at: cached.fetched_at };
}
async function two(env) {
  const t = await theirs(env);
  const o = await ours(env);
  return { ours: o.observation, ours_example: o.example, ours_place: o.place, theirs: t.observation, theirs_status: t.status, fetched_at: t.fetched_at };
}

// src/part2.ts
var ok = (body) => ({ status: 200, body });
var no = (status, detail) => ({ status, body: { detail } });
var ITEMS = content_default.part2_items;
var FLAGS = content_default.part2_flags;
var GOLD = Object.fromEntries(ITEMS.map((i) => [i.id, i.gold]));
var PART2_ITEM_IDS = ITEMS.map((i) => i.id);
var PART2_ARMS = ["unassisted", "assisted"];
var STRATA = ["untrained", "trained"];
var UNKNOWN2 = "We do not know that second look. Start it again from your score screen.";
var nowIso = () => (/* @__PURE__ */ new Date()).toISOString().replace(/\.\d{3}Z$/, "Z");
var isRight = (answer2, gold) => answer2 === sideAnswer(gold);
function randomHex2(bytes) {
  const a = new Uint8Array(bytes);
  crypto.getRandomValues(a);
  return Array.from(a, (b) => b.toString(16).padStart(2, "0")).join("");
}
function shuffled(items) {
  const out = items.slice();
  for (let i = out.length - 1; i > 0; i--) {
    const r = new Uint32Array(1);
    crypto.getRandomValues(r);
    const j = r[0] % (i + 1);
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}
async function part2For(env, part2Id) {
  return env.DB.prepare("SELECT id, session_id, arm, item_order, declined, completed_at FROM part2_session WHERE id = ?").bind(part2Id).first();
}
async function state(env, row) {
  const rows = await env.DB.prepare(
    "SELECT item_id, final_answer, question_shown FROM part2_response WHERE part2_id = ? ORDER BY position"
  ).bind(row.id).all();
  const all = rows.results ?? [];
  const out = {
    part2_id: row.id,
    arm: row.arm,
    item_order: row.item_order ? JSON.parse(row.item_order) : [],
    answered: all.filter((r) => r.final_answer !== null).map((r) => r.item_id),
    pending: all.find((r) => r.final_answer === null)?.item_id ?? null,
    completed: row.completed_at !== null,
    total: ITEMS.length
  };
  if (row.completed_at !== null) out.correct_total = all.filter((r) => r.final_answer !== null && isRight(r.final_answer, GOLD[r.item_id])).length;
  return out;
}
async function offer(env, body, qa) {
  const sessionId = String(body.session_id ?? "");
  const decision = body.decision === "decline" ? "decline" : body.decision === "start" ? "start" : null;
  if (decision === null) return no(422, "Choose to start the second look or to skip it.");
  const part1 = await env.DB.prepare("SELECT arm, is_test, completed_at, client_token_hash FROM session WHERE id = ?").bind(sessionId).first();
  if (part1 === null) return no(404, "We do not know that session. Start again from the first screen.");
  if (part1.completed_at === null) return no(409, "The second look opens after the score screen of the first test.");
  const existing = await env.DB.prepare(
    "SELECT id, session_id, arm, item_order, declined, completed_at FROM part2_session WHERE session_id = ?"
  ).bind(sessionId).first();
  if (existing !== null && (existing.declined === 0 || decision === "decline")) {
    return ok(existing.declined ? { declined: true } : await state(env, existing));
  }
  const at = nowIso();
  const isTest = part1.is_test === 1 || qa ? 1 : 0;
  const postLock = Date.now() >= Date.parse("2026-09-28T01:00:00Z") ? 1 : 0;
  if (decision === "decline") {
    await env.DB.prepare(
      `INSERT OR IGNORE INTO part2_session (id, session_id, part1_arm, offered_at, declined, client_token_hash, is_test, post_lock)
       VALUES (?, ?, ?, ?, 1, ?, ?, ?)`
    ).bind(randomHex2(16), sessionId, part1.arm, at, part1.client_token_hash, isTest, postLock).run();
    return ok({ declined: true });
  }
  const qaArm = qa && typeof body.qa_arm === "string" && PART2_ARMS.includes(body.qa_arm) ? body.qa_arm : null;
  const picked = qaArm ? { arm: qaArm, block_id: -1 } : await takeSlot(env, part1.arm);
  if ("detail" in picked) return no(500, picked.detail);
  const arm = picked.arm;
  const slot = picked;
  const order = shuffled(PART2_ITEM_IDS);
  const id = existing?.id ?? randomHex2(16);
  if (existing !== null) {
    await env.DB.prepare(
      "UPDATE part2_session SET declined = 0, arm = ?, block_id = ?, item_order = ?, started_at = ? WHERE id = ? AND declined = 1"
    ).bind(arm, slot.block_id, JSON.stringify(order), at, id).run();
  } else {
    await env.DB.prepare(
      `INSERT INTO part2_session (id, session_id, part1_arm, arm, block_id, item_order, offered_at, declined,
         started_at, client_token_hash, is_test, post_lock)
       VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)`
    ).bind(id, sessionId, part1.arm, arm, slot.block_id, JSON.stringify(order), at, at, part1.client_token_hash, isTest, postLock).run();
  }
  const row = await part2For(env, id);
  return ok(row ? await state(env, row) : { part2_id: id, arm, item_order: order });
}
async function takeSlot(env, part1Arm) {
  const stratum = STRATA.includes(part1Arm) ? part1Arm : "untrained";
  const taken = await env.DB.prepare(
    "UPDATE part2_counter SET next_position = next_position + 1 WHERE stratum = ? RETURNING next_position"
  ).bind(stratum).first();
  if (taken === null) return { detail: "The randomization counter for the second look is missing." };
  const slot = await env.DB.prepare("SELECT arm, block_id FROM part2_slot WHERE stratum = ? AND position = ?").bind(stratum, Number(taken.next_position) - 1).first();
  if (slot === null) return { detail: "The randomization sequence for the second look has run out." };
  return slot;
}
async function answer(env, body) {
  const part2Id = String(body.part2_id ?? "");
  const itemId = String(body.item_id ?? "");
  const first = String(body.answer ?? "");
  if (!ANSWERS.includes(first)) return no(422, "We do not know that answer.");
  if (!(itemId in GOLD)) return no(404, "We do not know that photo.");
  const row = await part2For(env, part2Id);
  if (row === null || row.declined) return no(404, UNKNOWN2);
  const existing = await env.DB.prepare(
    "SELECT first_answer, question_shown FROM part2_response WHERE part2_id = ? AND item_id = ?"
  ).bind(part2Id, itemId).first();
  if (existing !== null) {
    if (existing.first_answer !== first) return no(409, "This photo already has an answer. The first answer stays.");
    return ok({ ask: existing.question_shown === 1 });
  }
  const ask2 = questionNeeded(row.arm, FLAGS[itemId] ?? null, first);
  const t = Number(body.t_first_ms ?? 0);
  const settled = ask2 ? null : settle(first, false);
  await env.DB.prepare(
    `INSERT OR IGNORE INTO part2_response (part2_id, item_id, position, first_answer, final_answer, question_shown,
       choice, t_first_ms, t_final_ms, received_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  ).bind(part2Id, itemId, Number(body.position ?? 0), first, settled?.final_answer ?? null, ask2 ? 1 : 0, "", t, ask2 ? null : t, nowIso()).run();
  return ok({ ask: ask2 });
}
async function choice(env, body) {
  const part2Id = String(body.part2_id ?? "");
  const itemId = String(body.item_id ?? "");
  const row = await env.DB.prepare(
    "SELECT first_answer, final_answer, question_shown, choice FROM part2_response WHERE part2_id = ? AND item_id = ?"
  ).bind(part2Id, itemId).first();
  if (row === null) return no(404, "That photo has no first answer yet.");
  if (row.question_shown !== 1) return no(409, "No question was asked for this photo, so there is nothing to choose.");
  let got;
  try {
    got = settle(row.first_answer, true, body.choice ?? null, body.changed_to ?? null);
  } catch (e) {
    if (e instanceof AssistError) return no(422, e.message);
    throw e;
  }
  if (row.final_answer !== null) {
    if (row.final_answer === got.final_answer && row.choice === got.choice) return ok({ ok: true });
    return no(409, "This photo already has a final answer. The first one stays.");
  }
  await env.DB.prepare(
    "UPDATE part2_response SET final_answer = ?, choice = ?, t_final_ms = ? WHERE part2_id = ? AND item_id = ? AND final_answer IS NULL"
  ).bind(got.final_answer, got.choice, Number(body.t_final_ms ?? 0), part2Id, itemId).run();
  return ok({ ok: true });
}
async function complete(env, body) {
  const part2Id = String(body.part2_id ?? "");
  const row = await part2For(env, part2Id);
  if (row === null || row.declined) return no(404, UNKNOWN2);
  const held = await env.DB.prepare("SELECT item_id, final_answer FROM part2_response WHERE part2_id = ?").bind(part2Id).all();
  const settledIds = new Set((held.results ?? []).filter((r) => r.final_answer !== null).map((r) => r.item_id));
  const gap = PART2_ITEM_IDS.filter((id) => !settledIds.has(id));
  const answeredCount = Number(body.answered_count ?? 0);
  if (gap.length > 0 && body.final !== true && row.completed_at === null && answeredCount > settledIds.size) {
    return ok({ need_resend: gap, stored_count: settledIds.size });
  }
  if (row.completed_at === null) {
    await env.DB.prepare("UPDATE part2_session SET completed_at = ? WHERE id = ? AND completed_at IS NULL").bind(nowIso(), part2Id).run();
  }
  const correct = (held.results ?? []).filter((r) => r.final_answer !== null && isRight(r.final_answer, GOLD[r.item_id])).length;
  return ok({ correct_total: correct, total: ITEMS.length });
}
async function resume(env, part2Id) {
  const row = await part2For(env, part2Id);
  if (row === null || row.declined) return no(404, UNKNOWN2);
  return ok(await state(env, row));
}
async function counts(env) {
  const byArm = {};
  for (const arm of PART2_ARMS) {
    const r = await env.DB.prepare(
      "SELECT COUNT(*) AS n, SUM(CASE WHEN completed_at IS NOT NULL THEN 1 ELSE 0 END) AS done FROM part2_session WHERE arm = ? AND declined = 0 AND is_test = 0"
    ).bind(arm).first();
    byArm[arm] = { randomized: Number(r?.n ?? 0), completed: Number(r?.done ?? 0) };
  }
  const d = await env.DB.prepare("SELECT COUNT(*) AS n FROM part2_session WHERE declined = 1 AND is_test = 0").first();
  return ok({ by_arm: byArm, declined: Number(d?.n ?? 0) });
}
function demo(body) {
  const itemId = String(body.item_id ?? "");
  const given = String(body.answer ?? "");
  if (!(itemId in GOLD)) return no(404, "We do not know that photo.");
  if (!ANSWERS.includes(given)) return no(422, "We do not know that answer.");
  return ok({ ask: questionNeeded("assisted", FLAGS[itemId] ?? null, given), correct: isRight(given, GOLD[itemId]) });
}
async function exportFiles(env, csvRow2) {
  const sessions = await env.DB.prepare("SELECT * FROM part2_session ORDER BY offered_at").all();
  const responses = await env.DB.prepare("SELECT * FROM part2_response ORDER BY part2_id, position").all();
  const firstAt = {};
  for (const r of responses.results ?? []) {
    const id = String(r.part2_id);
    const at = String(r.received_at);
    if (!firstAt[id] || at < firstAt[id]) firstAt[id] = at;
  }
  const sLines = [csvRow2(PART2_SESSION_COLUMNS)];
  for (const s of sessions.results ?? []) {
    const first = firstAt[String(s.id)];
    const seconds = s.completed_at && first ? Math.round((Date.parse(String(s.completed_at)) - Date.parse(first)) / 1e3 * 10) / 10 : "";
    sLines.push(
      csvRow2([
        s.id,
        s.session_id,
        s.part1_arm,
        s.arm ?? "",
        s.block_id ?? "",
        s.offered_at,
        s.declined,
        s.started_at ?? "",
        s.completed_at ?? "",
        seconds,
        s.client_token_hash,
        s.is_test,
        s.post_lock
      ])
    );
  }
  const feature = Object.fromEntries(ITEMS.map((i) => [i.id, i.feature]));
  const rLines = [csvRow2(PART2_RESPONSE_COLUMNS)];
  for (const r of responses.results ?? []) {
    const id = String(r.item_id);
    const final = r.final_answer === null ? "" : String(r.final_answer);
    rLines.push(
      csvRow2([
        r.part2_id,
        id,
        feature[id] ?? "",
        GOLD[id] ?? "",
        r.position,
        r.first_answer,
        final,
        r.question_shown,
        r.choice ?? "",
        r.t_first_ms ?? "",
        r.t_final_ms ?? "",
        final && GOLD[id] && isRight(final, GOLD[id]) ? 1 : 0
      ])
    );
  }
  return [
    { name: "part2_sessions.csv", text: sLines.join("\r\n") + "\r\n" },
    { name: "part2_responses.csv", text: rLines.join("\r\n") + "\r\n" }
  ];
}
var PART2_SESSION_COLUMNS = [
  "part2_id",
  "session_id",
  "part1_arm",
  "arm",
  "block_id",
  "offered_at_utc",
  "declined",
  "started_at_utc",
  "completed_at_utc",
  "test_seconds",
  "client_token_hash",
  "is_test",
  "post_lock"
];
var PART2_RESPONSE_COLUMNS = [
  "part2_id",
  "item_id",
  "feature",
  "gold",
  "position",
  "first_answer",
  "final_answer",
  "question_shown",
  "choice",
  "t_first_ms",
  "t_final_ms",
  "correct"
];

// src/walk_store.ts
var Conflict = class extends Error {
};
var TooMany = class extends Error {
};
var WALKS = new Map(content_default.walks.map((w) => [w.id, { id: w.id, spot_name: w.spot_name, creek_name: w.creek_name }]));
var BODY_KEYS = /* @__PURE__ */ new Set(["walk_id", "answers", "answered_at", "followup_answers", "final_rating", "language"]);
var RECORD_ID_RE = /^walk-[0-9a-f]{16}$/;
function answersText(answers) {
  return JSON.stringify(Object.fromEntries(Object.keys(answers).sort().map((k) => [k, answers[k]])));
}
function stored(row) {
  return { record_id: row.record_id, walk_id: row.walk_id, answered_at: row.answered_at, delete_after: row.delete_after };
}
async function purgeWalks(db, now) {
  const [, records] = await db.batch([
    db.prepare("DELETE FROM walk_checks WHERE record_id IN (SELECT record_id FROM walk_record WHERE delete_after <= ?)").bind(now),
    db.prepare("DELETE FROM walk_record WHERE delete_after <= ?").bind(now)
  ]);
  return Number(records.meta.changes ?? 0);
}
function followupsOf(body, answers) {
  if (!("followup_answers" in body) && !("final_rating" in body)) return null;
  const given = body.followup_answers ?? {};
  if (given === null || typeof given !== "object" || Array.isArray(given)) throw new Invalid("followup_answers must be an object of follow-up ids and answers.");
  const finalRating = validateRating(body.final_rating);
  const chosen = walkFollowups(answers, content_default.followups, FORM_ITEMS);
  try {
    return walkChecks(answers, chosen, chosen.map(questionText), given, finalRating);
  } catch (err) {
    if (err instanceof WalkRecordError) throw new Invalid(err.message);
    throw err;
  }
}
function keptOf(row, answers) {
  const first = typeof answers.overall_rating === "string" ? answers.overall_rating : null;
  if (row === null) return { checks: [], first_rating: first, final_rating: first };
  return { checks: JSON.parse(row.checks_json), first_rating: first, final_rating: row.final_rating };
}
async function readBody(request) {
  const declared = Number(request.headers.get("content-length") ?? "0");
  if (declared > WALK_MAX_BYTES) throw new TooLarge("That walk is too large to store.");
  const raw = new Uint8Array(await request.arrayBuffer());
  if (raw.length > WALK_MAX_BYTES) throw new TooLarge("That walk is too large to store.");
  let body;
  try {
    body = JSON.parse(new TextDecoder().decode(raw));
  } catch {
    throw new Invalid("That was not JSON.");
  }
  if (!body || typeof body !== "object" || Array.isArray(body)) throw new Invalid("Send the walk as one JSON object.");
  for (const key of Object.keys(body)) if (!BODY_KEYS.has(key)) throw new Invalid(`A walk has no field called '${key}'.`);
  return body;
}
async function storeWalk(db, request, now) {
  const body = await readBody(request);
  const walk = typeof body.walk_id === "string" ? WALKS.get(body.walk_id) : void 0;
  if (walk === void 0) throw new NotFound("We do not know that walk.");
  if (!body.answers || typeof body.answers !== "object" || Array.isArray(body.answers)) throw new Invalid("answers must be an object of question ids and answers.");
  const answers = validateAnswers(body.answers);
  const kept = followupsOf(body, answers);
  if (body.language !== void 0 && body.language !== null && typeof body.language !== "string") throw new Invalid("language must be a language code.");
  const language = validateLanguage(body.language);
  let row;
  try {
    row = walkRecord(walk, answers, body.answered_at, now, kept === null ? null : kept.final_rating, language);
  } catch (err) {
    if (err instanceof WalkRecordError) throw new Invalid(err.message);
    throw err;
  }
  if (checkBundle(row.bundle).length > 0) throw new Invalid("That walk would make a record with a broken link inside it.");
  const text = answersText(answers);
  const keptText = kept === null ? null : JSON.stringify(kept.checks);
  await purgeWalks(db, now);
  const same2 = async () => {
    const existing = await db.prepare("SELECT * FROM walk_record WHERE record_id = ?").bind(row.record_id).first();
    if (existing === null) return null;
    if (existing.walk_id === row.walk_id && existing.answers_json === text) {
      const was = await db.prepare("SELECT final_rating, checks_json FROM walk_checks WHERE record_id = ?").bind(row.record_id).first();
      if (kept === null || was === null || was.checks_json === keptText && was.final_rating === kept.final_rating) return stored(existing);
    }
    throw new Conflict("Another walk of this clip was stored in the same second. Start again and finish it once more.");
  };
  const earlier = await same2();
  if (earlier !== null) return earlier;
  const dayStart = `${now.slice(0, 10)}T00:00:00Z`;
  const statements = [
    db.prepare(
      `INSERT OR IGNORE INTO walk_record (record_id, walk_id, answered_at, answers_json, bundle_json, created_at, delete_after)
         SELECT ?, ?, ?, ?, ?, ?, ? WHERE (SELECT COUNT(*) FROM walk_record WHERE created_at >= ?) < ?`
    ).bind(row.record_id, row.walk_id, row.answered_at, text, JSON.stringify(row.bundle), row.created_at, row.delete_after, dayStart, WALK_DAILY_CAP)
  ];
  if (kept !== null) {
    statements.push(
      db.prepare(
        `INSERT OR IGNORE INTO walk_checks (record_id, final_rating, checks_json)
           SELECT ?, ?, ? WHERE EXISTS (SELECT 1 FROM walk_record WHERE record_id = ? AND answers_json = ?)`
      ).bind(row.record_id, kept.final_rating, keptText, row.record_id, text)
    );
  }
  const [inserted] = await db.batch(statements);
  if (!inserted.meta.changes) {
    const raced = await same2();
    if (raced !== null) return raced;
    throw new TooMany("The demo store has taken all the walks it can for today. Your record is still on this page; try again tomorrow.");
  }
  return stored(row);
}
async function walkView(db, recordId, now) {
  const gone = `We have no stored walk record called '${recordId.slice(0, 40)}'. A walk record is deleted ${WALK_KEEP_DAYS} days after it is stored.`;
  if (!RECORD_ID_RE.test(recordId)) throw new NotFound(gone);
  const row = await db.prepare("SELECT * FROM walk_record WHERE record_id = ? AND delete_after > ?").bind(recordId, now).first();
  if (row === null) throw new NotFound(gone);
  const checks = await db.prepare("SELECT final_rating, checks_json FROM walk_checks WHERE record_id = ?").bind(recordId).first();
  const answers = JSON.parse(row.answers_json);
  return { ...stored(row), answers, bundle: JSON.parse(row.bundle_json), ...keptOf(checks, answers) };
}
async function walkFhir(db, recordId, now) {
  return (await walkView(db, recordId, now)).bundle;
}

// src/inaturalist.ts
var INVASIVE_ITEM = "invasive_species";
var SOURCE = "https://www.inaturalist.org";
var TERMS = "https://www.inaturalist.org/pages/terms";
var LINK_PREFIX = "https://www.inaturalist.org/observations";
function asSpot(row) {
  return {
    spot_id: row.spot_id,
    spot_name: row.spot_name,
    reach_id: row.reach_id,
    reach_name: row.reach_name,
    creek_id: row.creek_id,
    creek_name: row.creek_name,
    latitude: row.latitude,
    longitude: row.longitude,
    coarse: Boolean(row.coarse)
  };
}
async function creekSpots(env, creekRef) {
  const rows = (await env.DB.prepare("SELECT spot_id, spot_name, reach_id, reach_name, creek_id, creek_name, latitude, longitude, coarse FROM spot ORDER BY created_at").all()).results ?? [];
  const placed = new Map(rows.map((r) => [r.spot_id, placeSpot(asSpot(r), CREEKS)]));
  let creek = creekBySlug(creekRef);
  let spots;
  if (creek !== null) {
    const slug = creek.slug;
    spots = rows.filter((r) => placed.get(r.spot_id)?.creek.slug === slug);
  } else {
    spots = rows.filter((r) => r.creek_id === creekRef);
    const on = new Set(spots.map((r) => placed.get(r.spot_id)?.creek.slug).filter((x) => Boolean(x)));
    creek = on.size === 1 ? creekBySlug([...on][0]) : null;
  }
  return { key: creek?.slug ?? creekRef, spots: spots.filter((r) => !looksLikeATestName(r.spot_name)) };
}
async function invasiveAnswered(env, spotIds) {
  if (spotIds.length === 0) return false;
  const marks = spotIds.map(() => "?").join(",");
  const rows = (await env.DB.prepare(`SELECT answers_json FROM visit WHERE spot_id IN (${marks}) AND finalized_at IS NOT NULL`).bind(...spotIds).all()).results ?? [];
  for (const r of rows) {
    const answers = JSON.parse(r.answers_json);
    const value = answers && typeof answers === "object" ? answers[INVASIVE_ITEM] : void 0;
    if (value !== void 0 && value !== null && value !== "") return true;
  }
  return false;
}
function cleanSpecies(raw) {
  const out = [];
  for (const s of Array.isArray(raw) ? raw : []) {
    if (!s || typeof s !== "object") continue;
    const item = s;
    const url = String(item.url ?? "");
    const count = item.count;
    if (!url.startsWith(LINK_PREFIX) || typeof count !== "number" || !Number.isInteger(count) || count < 1) continue;
    out.push({
      taxon_id: item.taxon_id ?? null,
      name: String(item.name ?? ""),
      latin_name: String(item.latin_name ?? ""),
      count,
      last_observed: String(item.last_observed ?? ""),
      url
    });
  }
  return out;
}
async function inaturalistView(env, creekRef) {
  const { key, spots } = await creekSpots(env, creekRef);
  const shown = await invasiveAnswered(env, spots.map((s) => s.spot_id));
  const row = await env.DB.prepare("SELECT body, fetched_at FROM inaturalist_cache WHERE creek = ?").bind(key).first();
  let body = {};
  if (row !== null) {
    try {
      const parsed = JSON.parse(row.body);
      body = parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    } catch {
      body = {};
    }
  }
  return {
    creek: key,
    shown,
    status: row !== null ? "cached" : "none",
    fetched_at: row !== null ? row.fetched_at : null,
    since: body.since ?? null,
    radius_m: body.radius_m ?? null,
    // Withheld until a finished check on this creek has answered the invasive plant question.
    species: shown ? cleanSpecies(body.species) : [],
    source: SOURCE,
    terms: TERMS
  };
}

// src/index.ts
var DATA_LOCK_UTC = Date.parse("2026-09-28T01:00:00Z");
var JUDGE_MODE_OPENS_UTC = Date.parse("2026-10-03T04:00:00Z");
var SOURCE_LABELS = ["poster", "chat", "friends", "creek_group", "other", "panel"];
var UA_CLASSES = ["phone", "tablet", "desktop", "other"];
var ANSWERS2 = ["yes", "no", "cant_tell"];
var TOKEN_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789";
var TOKEN_LENGTH = 16;
var GOLD2 = Object.fromEntries(content_default.test_items.map((i) => [i.id, i.gold]));
var FEATURE = Object.fromEntries(content_default.test_items.map((i) => [i.id, i.feature]));
var ITEM_IDS = content_default.test_items.map((i) => i.id);
function isCorrect(answer2, gold) {
  return answer2 === "yes" && gold === "present" || answer2 === "no" && gold === "absent";
}
async function sha256Hex2(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, "0")).join("");
}
function randomHex3(bytes) {
  const a = new Uint8Array(bytes);
  crypto.getRandomValues(a);
  return Array.from(a, (b) => b.toString(16).padStart(2, "0")).join("");
}
function newContributorToken() {
  const a = new Uint32Array(TOKEN_LENGTH);
  crypto.getRandomValues(a);
  return Array.from(a, (n) => TOKEN_ALPHABET[n % TOKEN_ALPHABET.length]).join("");
}
function shuffled2(items) {
  const out = items.slice();
  for (let i = out.length - 1; i > 0; i--) {
    const r = new Uint32Array(1);
    crypto.getRandomValues(r);
    const j = r[0] % (i + 1);
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}
function sameSecret(given, expected) {
  if (!expected || expected.length < 16 || !given || given.length !== expected.length) return false;
  let diff = 0;
  for (let i = 0; i < expected.length; i++) diff |= given.charCodeAt(i) ^ expected.charCodeAt(i);
  return diff === 0;
}
var coerce = (raw, allowed, fallback) => typeof raw === "string" && allowed.includes(raw) ? raw : fallback;
function corsHeaders(env) {
  return {
    "Access-Control-Allow-Origin": env.ALLOWED_ORIGIN ?? "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "content-type, x-qa-key",
    "Access-Control-Max-Age": "86400"
  };
}
var json = (env, data, status = 200) => new Response(JSON.stringify(data), {
  status,
  headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...corsHeaders(env) }
});
var fhirJson = (env, request, data, status = 200) => new Response(JSON.stringify(data), {
  status,
  headers: { "content-type": fhirMediaType(request.headers.get("accept")), vary: "Accept", "cache-control": "no-store", ...corsHeaders(env) }
});
var nowIso2 = () => (/* @__PURE__ */ new Date()).toISOString().replace(/\.\d{3}Z$/, "Z");
async function createSession(env, body, isTest) {
  const raw = String(body.client_token_hash ?? "");
  if (raw.length < 8) return json(env, { detail: "client_token_hash is required." }, 422);
  const tokenHash = (await sha256Hex2(raw)).slice(0, 32);
  const earlier = await env.DB.prepare(
    "SELECT arm, block_id FROM session WHERE client_token_hash = ? ORDER BY started_at LIMIT 1"
  ).bind(tokenHash).first();
  const taken = await env.DB.prepare(
    "UPDATE counter SET next_position = next_position + 1 WHERE id = 1 RETURNING next_position"
  ).first();
  if (taken === null) return json(env, { detail: "The randomization counter is missing." }, 500);
  const position = Number(taken.next_position) - 1;
  const slot = await env.DB.prepare("SELECT arm, block_id FROM arm_slot WHERE position = ?").bind(position).first();
  if (slot === null) return json(env, { detail: "The randomization sequence has run out." }, 500);
  const arm = earlier && !isTest ? earlier.arm : slot.arm;
  const blockId = earlier && !isTest ? earlier.block_id : slot.block_id;
  const sessionId = randomHex3(16);
  const order = shuffled2(ITEM_IDS);
  const at = nowIso2();
  const hidden = String(body.hidden_field ?? "").trim().length > 0;
  const warmup = typeof body.warmup_choice === "string" && content_default.warmup_ids.includes(body.warmup_choice) ? body.warmup_choice : null;
  await env.DB.prepare(
    `INSERT INTO session (id, arm, block_id, item_order, consent_version, content_hash, build_hash,
       consent_at, started_at, client_token_hash, ua_class, is_test, source_label,
       hidden_field_filled, post_lock, warmup_choice)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  ).bind(
    sessionId,
    arm,
    blockId,
    JSON.stringify(order),
    String(body.consent_version ?? "").slice(0, 32),
    String(body.content_hash ?? "").slice(0, 64),
    String(body.build_hash ?? "").slice(0, 64),
    at,
    at,
    tokenHash,
    coerce(body.ua_class, UA_CLASSES, "other"),
    isTest ? 1 : 0,
    coerce(body.source_label, SOURCE_LABELS, "other"),
    hidden ? 1 : 0,
    Date.now() >= DATA_LOCK_UTC ? 1 : 0,
    warmup
  ).run();
  return json(env, { session_id: sessionId, arm, item_order: order, lesson_first: arm === "trained" });
}
async function recordResponse(env, body) {
  const sessionId = String(body.session_id ?? "");
  const itemId = String(body.item_id ?? "");
  const answer2 = String(body.answer ?? "");
  if (!ANSWERS2.includes(answer2)) return json(env, { detail: "We do not know that answer." }, 422);
  const session = await env.DB.prepare("SELECT id FROM session WHERE id = ?").bind(sessionId).first();
  if (session === null) return json(env, { detail: "We do not know that session. Start again from the first screen." }, 404);
  if (!(itemId in GOLD2)) return json(env, { detail: "We do not know that test item." }, 404);
  const existing = await env.DB.prepare("SELECT answer FROM response WHERE session_id = ? AND item_id = ?").bind(sessionId, itemId).first();
  if (existing !== null) {
    if (existing.answer !== answer2) return json(env, { detail: "This photo already has an answer. The first answer stays." }, 409);
    return json(env, { ok: true });
  }
  await env.DB.prepare(
    `INSERT OR IGNORE INTO response (session_id, item_id, answer, rt_ms, position,
       first_choice, t_first_ms, n_changes, received_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
  ).bind(
    sessionId,
    itemId,
    answer2,
    Number(body.rt_ms ?? 0),
    Number(body.position ?? 0),
    typeof body.first_choice === "string" ? body.first_choice : null,
    body.t_first_ms === void 0 || body.t_first_ms === null ? null : Number(body.t_first_ms),
    Number(body.n_changes ?? 0),
    nowIso2()
  ).run();
  return json(env, { ok: true });
}
async function scoresFor(env, sessionId) {
  const rows = await env.DB.prepare("SELECT item_id, answer FROM response WHERE session_id = ?").bind(sessionId).all();
  const byFeature = {};
  for (const f of content_default.features) byFeature[f] = { feature: f, correct: 0, total: 0 };
  for (const item of content_default.test_items) byFeature[item.feature].total += 1;
  for (const r of rows.results ?? []) {
    const gold = GOLD2[r.item_id];
    if (gold && isCorrect(r.answer, gold)) byFeature[FEATURE[r.item_id]].correct += 1;
  }
  const scores = content_default.features.map((f) => byFeature[f]);
  return { scores, correct_total: scores.reduce((n, s) => n + s.correct, 0), held: (rows.results ?? []).length };
}
async function completeSession(env, body) {
  const sessionId = String(body.session_id ?? "");
  const row = await env.DB.prepare("SELECT item_order, completed_at FROM session WHERE id = ?").bind(sessionId).first();
  if (row === null) return json(env, { detail: "We do not know that session. Start again from the first screen." }, 404);
  const order = JSON.parse(row.item_order);
  const held = await env.DB.prepare("SELECT item_id FROM response WHERE session_id = ?").bind(sessionId).all();
  const have = new Set((held.results ?? []).map((r) => r.item_id));
  const gap = order.filter((id) => !have.has(id));
  const answeredCount = Number(body.answered_count ?? 0);
  const isFinal = body.final === true;
  if (gap.length > 0 && !isFinal && row.completed_at === null && answeredCount > have.size) {
    return json(env, { need_resend: gap, stored_count: have.size });
  }
  const { scores, correct_total } = await scoresFor(env, sessionId);
  const out = { scores, correct_total };
  if (row.completed_at === null) {
    const prior = body.prior_experience === "yes" || body.prior_experience === "no" ? body.prior_experience : null;
    await env.DB.prepare("UPDATE session SET completed_at = ?, prior_experience = ?, unsent_count = ? WHERE id = ?").bind(nowIso2(), prior, Math.max(0, answeredCount - have.size), sessionId).run();
  }
  if (body.keep_score === true) {
    const token = newContributorToken();
    await env.DB.prepare("INSERT INTO observer (contributor_token, scores_json, tested_on) VALUES (?, ?, ?)").bind(token, JSON.stringify(scores), nowIso2().slice(0, 10)).run();
    out.contributor_token = token;
  }
  return json(env, out);
}
async function resumeState(env, sessionId) {
  const row = await env.DB.prepare(
    "SELECT id, arm, item_order, lesson_seconds, completed_at FROM session WHERE id = ?"
  ).bind(sessionId).first();
  if (row === null) return json(env, { detail: "We do not know that session. Start again from the first screen." }, 404);
  const answered = await env.DB.prepare("SELECT item_id FROM response WHERE session_id = ? ORDER BY position").bind(sessionId).all();
  const state2 = {
    session_id: row.id,
    arm: row.arm,
    item_order: JSON.parse(row.item_order),
    lesson_first: row.arm === "trained",
    lesson_done: Boolean(row.lesson_seconds),
    answered: (answered.results ?? []).map((r) => r.item_id),
    completed: row.completed_at !== null
  };
  if (row.completed_at !== null) {
    const { scores, correct_total } = await scoresFor(env, sessionId);
    state2.scores = scores;
    state2.correct_total = correct_total;
  }
  return json(env, state2);
}
async function counts2(env) {
  const byArm = {};
  for (const arm of ["untrained", "trained"]) {
    const r = await env.DB.prepare(
      "SELECT COUNT(*) AS n, SUM(CASE WHEN completed_at IS NOT NULL THEN 1 ELSE 0 END) AS done FROM session WHERE arm = ? AND is_test = 0"
    ).bind(arm).first();
    byArm[arm] = { randomized: Number(r?.n ?? 0), completed: Number(r?.done ?? 0) };
  }
  const bySource = Object.fromEntries(SOURCE_LABELS.map((s) => [s, 0]));
  const rows = await env.DB.prepare(
    "SELECT source_label, COUNT(*) AS n FROM session WHERE is_test = 0 AND completed_at IS NOT NULL GROUP BY source_label"
  ).all();
  for (const r of rows.results ?? []) bySource[coerce(r.source_label, SOURCE_LABELS, "other")] += Number(r.n);
  const post = await env.DB.prepare("SELECT COUNT(*) AS n FROM session WHERE is_test = 0 AND post_lock = 1").first();
  return json(env, { by_arm: byArm, by_source: bySource, post_lock: Number(post?.n ?? 0) });
}
function crc32(bytes) {
  let c = 4294967295;
  for (const b of bytes) {
    c ^= b;
    for (let k = 0; k < 8; k++) c = c & 1 ? 3988292384 ^ c >>> 1 : c >>> 1;
  }
  return (c ^ 4294967295) >>> 0;
}
function zipOf(files) {
  const enc = new TextEncoder();
  const chunks = [];
  const central = [];
  let offset = 0;
  for (const f of files) {
    const name = enc.encode(f.name);
    const data = enc.encode(f.text);
    const crc = crc32(data);
    const local = new Uint8Array(30 + name.length);
    const lv = new DataView(local.buffer);
    lv.setUint32(0, 67324752, true);
    lv.setUint16(4, 20, true);
    lv.setUint16(8, 0, true);
    lv.setUint32(14, crc, true);
    lv.setUint32(18, data.length, true);
    lv.setUint32(22, data.length, true);
    lv.setUint16(26, name.length, true);
    local.set(name, 30);
    chunks.push(local, data);
    const head = new Uint8Array(46 + name.length);
    const hv = new DataView(head.buffer);
    hv.setUint32(0, 33639248, true);
    hv.setUint16(4, 20, true);
    hv.setUint16(6, 20, true);
    hv.setUint32(16, crc, true);
    hv.setUint32(20, data.length, true);
    hv.setUint32(24, data.length, true);
    hv.setUint16(28, name.length, true);
    hv.setUint32(42, offset, true);
    head.set(name, 46);
    central.push(head);
    offset += local.length + data.length;
  }
  const centralSize = central.reduce((n, c) => n + c.length, 0);
  const end = new Uint8Array(22);
  const ev = new DataView(end.buffer);
  ev.setUint32(0, 101010256, true);
  ev.setUint16(8, files.length, true);
  ev.setUint16(10, files.length, true);
  ev.setUint32(12, centralSize, true);
  ev.setUint32(16, offset, true);
  const total = offset + centralSize + 22;
  const out = new Uint8Array(total);
  let at = 0;
  for (const c of [...chunks, ...central, end]) {
    out.set(c, at);
    at += c.length;
  }
  return out;
}
var csvCell = (v) => {
  const s = v === null || v === void 0 ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};
var csvRow = (cells) => cells.map(csvCell).join(",");
async function exportZip(env) {
  const sessions = await env.DB.prepare("SELECT * FROM session ORDER BY started_at").all();
  const responses = await env.DB.prepare("SELECT * FROM response ORDER BY session_id, position").all();
  const firstAt = {};
  for (const r of responses.results ?? []) {
    const sid = String(r.session_id);
    const at = String(r.received_at);
    if (!firstAt[sid] || at < firstAt[sid]) firstAt[sid] = at;
  }
  const sessionHead = [
    "session_id",
    "arm",
    "block_id",
    "source_label",
    "ua_class",
    "consent_version",
    "content_hash",
    "build_hash",
    "started_at_utc",
    "lesson_seconds_total",
    "completed_at_utc",
    "test_seconds",
    "is_test",
    "post_lock",
    "hidden_field_filled",
    "client_token_hash",
    "prior_experience",
    "warmup_choice",
    "unsent_count"
  ];
  const sessionLines = [csvRow(sessionHead)];
  for (const s of sessions.results ?? []) {
    let lessonTotal = "";
    if (s.lesson_seconds) {
      const vals = Object.values(JSON.parse(String(s.lesson_seconds)));
      lessonTotal = Math.round(vals.reduce((a, b) => a + b, 0) * 10) / 10;
    }
    let testSeconds = "";
    const first = firstAt[String(s.id)];
    if (s.completed_at && first) {
      testSeconds = Math.round((Date.parse(String(s.completed_at)) - Date.parse(first)) / 1e3 * 10) / 10;
    }
    sessionLines.push(
      csvRow([
        s.id,
        s.arm,
        s.block_id,
        s.source_label,
        s.ua_class,
        s.consent_version,
        s.content_hash,
        s.build_hash,
        s.started_at,
        lessonTotal,
        s.completed_at ?? "",
        testSeconds,
        s.is_test,
        s.post_lock,
        s.hidden_field_filled,
        s.client_token_hash,
        s.prior_experience ?? "",
        s.warmup_choice ?? "",
        s.unsent_count
      ])
    );
  }
  const responseHead = [
    "session_id",
    "item_id",
    "feature",
    "gold",
    "answer",
    "correct",
    "rt_ms",
    "position",
    "first_choice",
    "final_choice",
    "t_first_ms",
    "t_confirm_ms",
    "n_changes"
  ];
  const responseLines = [csvRow(responseHead)];
  for (const r of responses.results ?? []) {
    const itemId = String(r.item_id);
    const gold = GOLD2[itemId];
    responseLines.push(
      csvRow([
        r.session_id,
        itemId,
        FEATURE[itemId] ?? "",
        gold ?? "",
        r.answer,
        gold && isCorrect(String(r.answer), gold) ? 1 : 0,
        r.rt_ms,
        r.position,
        r.first_choice ?? "",
        r.answer,
        r.t_first_ms ?? "",
        r.rt_ms,
        r.n_changes
      ])
    );
  }
  const zip = zipOf([
    { name: "sessions.csv", text: sessionLines.join("\r\n") + "\r\n" },
    { name: "responses.csv", text: responseLines.join("\r\n") + "\r\n" },
    // Part 2 (UPDATE_31): two more files, read by evals/assist_analysis.py.
    ...await exportFiles(env, csvRow)
  ]);
  return new Response(zip, {
    status: 200,
    headers: {
      "content-type": "application/zip",
      "content-disposition": 'attachment; filename="second-look-export.zip"',
      "cache-control": "no-store",
      ...corsHeaders(env)
    }
  });
}
var src_default = {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(env) });
    if (path === "/health") return json(env, { status: "ok" });
    if (path === "/api/content/hash") return json(env, { content_hash: content_default.content_hash, build_hash: "worker" });
    const now = nowIso2();
    const checkEnv = { DB: env.DB, PHOTOS: env.PHOTOS, RAIN_FETCH: env.RAIN_URL ? rainFetchAt(env.RAIN_URL) : void 0 };
    try {
      if (path === "/api/upload" && request.method === "POST") return json(env, await storeUpload(env, request, now));
      if (path === "/api/walk" && request.method === "POST") return json(env, await storeWalk(env.DB, request, now));
      const walkBundle2 = /^\/api\/walk\/([^/]+)\/fhir$/.exec(path);
      if (walkBundle2 && request.method === "GET") return await fhirRoute(env, request, () => walkFhir(env.DB, idFrom(walkBundle2[1]), now));
      const walk = /^\/api\/walk\/([^/]+)$/.exec(path);
      if (walk && request.method === "GET") return json(env, await walkView(env.DB, idFrom(walk[1]), now));
      const photo = /^\/api\/photo\/([^/]+)$/.exec(path);
      if (photo && request.method === "GET") return withCors(env, await photoResponse(env, idFrom(photo[1]), url.searchParams.get("t")));
      if (path === "/api/creeks") return json(env, await creeksView(checkEnv));
      const city = /^\/api\/city\/([^/]+)$/.exec(path);
      if (city) return json(env, await cityView(checkEnv, idFrom(city[1]), todayOf(now)));
      const spotFhir = /^\/api\/spot\/([^/]+)\/fhir$/.exec(path);
      if (spotFhir) {
        return await fhirRoute(env, request, async () => {
          const found = await latestBundleForSpot(env.DB, idFrom(spotFhir[1]));
          if (found === null) throw new NotFound("no FHIR record for this spot yet");
          return found;
        });
      }
      const spot = /^\/api\/spot\/([^/]+)$/.exec(path);
      if (spot && request.method === "GET") {
        const id = idFrom(spot[1]);
        const view = await spotView(checkEnv, id, todayOf(now));
        return json(env, { ...view, place: await placeForSpot(checkEnv, id), downstream_notes: await notesForSpot(checkEnv, id, todayOf(now)) });
      }
      const bundle = /^\/api\/fhir\/Bundle\/([^/]+)$/.exec(path);
      if (bundle) {
        return await fhirRoute(env, request, async () => {
          const found = await loadVisitBundle(env.DB, idFrom(bundle[1]));
          if (found === null) throw new NotFound("no FHIR record for this visit");
          return found;
        });
      }
      if (path === "/api/fhir/validation") return json(env, fhir_validation_default);
      const example = /^\/api\/fhir\/referral\/([^/]+)\/example-result$/.exec(path);
      if (example) return await fhirRoute(env, request, () => exampleResultView(checkEnv, idFrom(example[1]), now));
      const referral = /^\/api\/fhir\/referral\/([^/]+)$/.exec(path);
      if (referral) return await fhirRoute(env, request, () => referralView(checkEnv, idFrom(referral[1]), now));
      if (path === "/api/two") return json(env, await two(env));
      const inat = /^\/api\/inaturalist\/([^/]+)$/.exec(path);
      if (inat && request.method === "GET") return json(env, await inaturalistView(env, idFrom(inat[1])));
    } catch (err) {
      return errorResponse(env, err);
    }
    let body = {};
    if (request.method === "POST" && (request.headers.get("content-type") ?? "").includes("application/json")) {
      try {
        body = await request.json();
      } catch {
        return json(env, { detail: "That was not JSON." }, 400);
      }
    }
    try {
      if (path === "/api/check/draft" && request.method === "POST") return json(env, await createDraft(checkEnv, body, now));
      if (path === "/api/check/finalize" && request.method === "POST") return json(env, await finalize(checkEnv, body, now));
      const quick = /^\/api\/quick\/([^/]+)$/.exec(path);
      if (quick && request.method === "POST") return json(env, await quickCheck(checkEnv, idFrom(quick[1]), body, now));
      if (path === "/api/test/session" && request.method === "POST") {
        const isTest = sameSecret(request.headers.get("x-qa-key"), env.QA_KEY);
        return await createSession(env, body, isTest);
      }
      if (path === "/api/test/response" && request.method === "POST") return await recordResponse(env, body);
      if (path === "/api/test/lesson-done" && request.method === "POST") {
        const sid = String(body.session_id ?? "");
        const seconds = body.lesson_seconds ?? {};
        const clean = {};
        for (const [k, v] of Object.entries(seconds)) clean[k.slice(0, 32)] = Math.round(Number(v) * 10) / 10;
        const r = await env.DB.prepare("UPDATE session SET lesson_seconds = ? WHERE id = ?").bind(JSON.stringify(clean), sid).run();
        if (!r.meta.changes) return json(env, { detail: "We do not know that session. Start again from the first screen." }, 404);
        return json(env, { ok: true });
      }
      if (path === "/api/test/complete" && request.method === "POST") return await completeSession(env, body);
      if (path === "/api/test/resume") return await resumeState(env, url.searchParams.get("session_id") ?? "");
      if (path === "/api/test/counts") return await counts2(env);
      if (path === "/api/test/export") {
        if (!sameSecret(url.searchParams.get("token"), env.EXPORT_TOKEN)) return json(env, { detail: "Not found." }, 404);
        return await exportZip(env);
      }
      if (path === "/api/t2/offer" && request.method === "POST") return reply(env, await offer(env, body, sameSecret(request.headers.get("x-qa-key"), env.QA_KEY)));
      if (path === "/api/t2/answer" && request.method === "POST") return reply(env, await answer(env, body));
      if (path === "/api/t2/choice" && request.method === "POST") return reply(env, await choice(env, body));
      if (path === "/api/t2/complete" && request.method === "POST") return reply(env, await complete(env, body));
      if (path === "/api/t2/resume") return reply(env, await resume(env, url.searchParams.get("part2_id") ?? ""));
      if (path === "/api/t2/counts") return reply(env, await counts(env));
      if (path === "/api/t2/demo" && request.method === "POST") {
        if (lockClock(env) < JUDGE_MODE_OPENS_UTC) return json(env, { detail: "Judge mode opens on Oct 3." }, 403);
        return reply(env, demo(body));
      }
      if (path === "/api/demo/answer" && request.method === "POST") {
        if (lockClock(env) < JUDGE_MODE_OPENS_UTC) return json(env, { detail: "Judge mode opens on Oct 3." }, 403);
        const gold = GOLD2[String(body.item_id ?? "")];
        if (!gold) return json(env, { detail: "We do not know that test item." }, 404);
        return json(env, { correct: isCorrect(String(body.answer ?? ""), gold) });
      }
    } catch (err) {
      return errorResponse(env, err);
    }
    return json(env, { detail: "Not found." }, 404);
  },
  /** Once a day (the cron in worker/wrangler.jsonc): deletes every video walk record past its
   *  delete date (UPDATE_30 section 1 item 3) and every upload row older than 30 days, whose photo
   *  KV has dropped by then (hard rule 8, docs/DATA_HANDLING.md). Each runs whatever the other
   *  does, and a failure in either is thrown, so the run shows as failed. Nothing else runs on it. */
  async scheduled(_controller, env) {
    const now = nowIso2();
    const runs = await Promise.allSettled([purgeWalks(env.DB, now), purgeUploads(env.DB, now)]);
    for (const run of runs) if (run.status === "rejected") throw run.reason;
  }
};
function reply(env, r) {
  return json(env, r.body, r.status);
}
function lockClock(env) {
  const fixed = env.E2E_NOW === void 0 ? Number.NaN : Date.parse(env.E2E_NOW);
  return Number.isFinite(fixed) ? fixed : Date.now();
}
function idFrom(part) {
  try {
    return decodeURIComponent(part);
  } catch {
    throw new NotFound("Not found.");
  }
}
function problemOf(err) {
  if (err instanceof Invalid) return { status: 422, detail: err.message };
  if (err instanceof NotFound) return { status: 404, detail: err.message };
  if (err instanceof TooLarge) return { status: 413, detail: err.message };
  if (err instanceof Conflict) return { status: 409, detail: err.message };
  if (err instanceof TooMany) return { status: 429, detail: err.message };
  return { status: 500, detail: "The server could not take that. Try again in a moment." };
}
function errorResponse(env, err) {
  const problem = problemOf(err);
  return json(env, { detail: problem.detail }, problem.status);
}
async function fhirRoute(env, request, make) {
  try {
    return fhirJson(env, request, await make());
  } catch (err) {
    const problem = problemOf(err);
    return fhirJson(env, request, operationOutcome(problem.status, problem.detail), problem.status);
  }
}
function withCors(env, response) {
  const headers = new Headers(response.headers);
  for (const [k, v] of Object.entries(corsHeaders(env))) headers.set(k, v);
  return new Response(response.body, { status: response.status, headers });
}
function rainFetchAt(base) {
  return async (url) => {
    const query = url.split("?")[1] ?? "";
    const response = await fetch(`${base}?${query}`, { signal: AbortSignal.timeout(5e3) });
    if (!response.ok) throw new Error(`rain ${response.status}`);
    return response.json();
  };
}

// test/golden.test.ts
var here = dirname(fileURLToPath(import.meta.url));
var root = join(here, "..", "..");
var golden = (name) => JSON.parse(readFileSync(join(root, "worker", "golden", `${name}.json`), "utf8"));
var instancesDir = join(root, "fhir", "build", "instances");
function tsBundles(dir) {
  return readdirSync(dir).filter((f) => f.startsWith("ts-") && f.endsWith(".json")).sort();
}
function clearOldBundles(dir) {
  mkdirSync(dir, { recursive: true });
  const old = tsBundles(dir);
  for (const f of old) rmSync(join(dir, f));
  return old;
}
clearOldBundles(instancesDir);
var written = /* @__PURE__ */ new Set();
function writeBundle(bundle) {
  const file = `ts-${String(bundle.id)}.json`;
  writeFileSync(join(instancesDir, file), JSON.stringify(bundle, null, 2) + "\n");
  written.add(file);
}
function canonical(value) {
  return JSON.stringify(value, (_k, v) => {
    if (v && typeof v === "object" && !Array.isArray(v)) {
      return Object.fromEntries(Object.keys(v).sort().map((k) => [k, v[k]]));
    }
    return v;
  });
}
function same(actual, expected, name) {
  assert.equal(canonical(actual), canonical(expected), name);
}
test("helpers: sha256, Python rounding, fhir_id", () => {
  const doc = golden("helpers");
  for (const c of doc.sha256) same(sha256Hex(c.input.text), c.expected, `sha256 ${c.name}`);
  for (const c of doc.round) same(pyRound(c.input.value, c.input.digits), c.expected, `round ${c.name}`);
  for (const c of doc.fhir_id) same(fhirId(...c.input.parts), c.expected, `fhir_id ${c.name}`);
});
test("assist: part 2's question and the stored row, the flag never an answer", () => {
  const doc = golden("assist");
  same(QUESTION, doc.question, "the question's words");
  for (const c of doc.flag_side) same(flagSide(c.input.flags, c.input.item_id), c.expected, `flag_side ${c.name}`);
  for (const c of doc.question_needed) same(questionNeeded(c.input.arm, c.input.side, c.input.first), c.expected, `ask ${c.name}`);
  for (const c of doc.settle) {
    let got;
    try {
      got = settle(c.input.first, c.input.asked, c.input.choice, c.input.changed_to);
    } catch (e) {
      if (!(e instanceof AssistError)) throw e;
      got = { error: e.message };
    }
    same(got, c.expected, `settle ${c.name}`);
  }
});
test("followups: the selector, over the repository's own table and form", () => {
  const doc = golden("followups");
  assert.ok(doc.cases.some((c) => c.input.flags.length > 0), "no vector carries a flag");
  for (const c of doc.cases) {
    const chosen = selectFollowups(c.input.answers, c.input.site, c.input.observer, c.input.flags, content_default.followups, content_default.form_items, c.input.checker_enabled);
    same(chosen, c.expected, c.name);
  }
});
test("labels: k of 4, the date, the expired sentence", () => {
  const doc = golden("labels");
  for (const c of doc.cases) {
    same(observerLabel(c.input.score, c.input.feature_name, c.input.today, c.input.locale), c.expected, c.name);
  }
});
test("healthcard: approved sentences only, the same pick for the same seed", () => {
  const doc = golden("healthcard");
  for (const c of doc.cases) same(pickActions(c.input.sentences, c.input.seed), c.expected, c.name);
});
test("act: findings, needs, pipes worth testing, and both pin guards", () => {
  const doc = golden("act");
  for (const c of doc.findings_from_visits) same(findingsFromVisits(c.input.visits, c.input.finding_key_for), c.expected, c.name);
  for (const c of doc.needs_from_findings) same(needsFromFindings(c.input.findings, c.input.sentences), c.expected, c.name);
  for (const c of doc.pipes_worth_testing) same(pipesWorthTesting(c.input.visits, c.input.today), c.expected, c.name);
  for (const c of doc.looks_like_a_test_name) same(looksLikeATestName(c.input.name), c.expected, c.name);
  for (const c of doc.metres_between) {
    const d = metresBetween(c.input.lat1, c.input.lon1, c.input.lat2, c.input.lon2);
    assert.ok(Math.abs(d - c.expected) < 2e-3, `${c.name}: ${d} vs ${c.expected}`);
  }
  for (const c of doc.nearest_spot) {
    const found = nearestSpot(c.input.latitude, c.input.longitude, c.input.spots, c.input.within);
    if (c.expected === null) assert.equal(found, null, c.name);
    else {
      assert.ok(found, c.name);
      assert.equal(found.spot.spot_id, c.expected.spot_id, c.name);
      assert.ok(Math.abs(found.metres - c.expected.metres) < 2e-3, `${c.name}: ${found.metres} vs ${c.expected.metres}`);
    }
  }
});
test("act: the downstream note, only where flows_into is set", () => {
  const doc = golden("act");
  for (const c of doc.downstream_note) same(downstreamNote(c.input.finding, c.input.feature_name, c.input.reaches_below), c.expected, c.name);
  for (const c of doc.notes_below) {
    const creek = c.input.creek;
    const foreign = c.input.foreign_reach ?? null;
    const reachOfSpot = Object.fromEntries(
      Object.entries(c.input.reach_of).map(([spotId, slug]) => [
        spotId,
        slug === null ? null : foreign && foreign.slug === slug ? foreign : reachOf(creek, slug)
      ])
    );
    same(notesBelow(c.input.findings, reachOfSpot, creek, c.input.labels), c.expected, c.name);
  }
});
test("regions: placement on a creek and a reach, and the reaches below", () => {
  const doc = golden("regions");
  for (const c of doc.place_spot) {
    const p = placeSpot(c.input.spot);
    const got = p === null ? null : { creek_slug: p.creek.slug, reach_slug: p.reach ? p.reach.slug : null };
    same(got, c.expected, c.name);
  }
  for (const c of doc.reaches_below) {
    const creek = creekBySlug(c.input.creek_slug);
    const reach = reachOf(creek, c.input.reach_slug);
    same(reachesBelow(reach, creek).map((r) => r.slug), c.expected, c.name);
  }
});
test("fhir_emit: the same Bundle as Python, and it passes the structural check", () => {
  const doc = golden("fhir_emit");
  for (const c of doc.cases) {
    const bundle = emitVisit(c.input.visit, c.input.test_sitting, c.input.emitted_at);
    same(bundle, c.expected, c.name);
    assert.deepEqual(checkBundle(bundle), [], `${c.name}: structural check`);
    writeBundle(bundle);
  }
  const doubled = emitVisit(doc.cases[0].input.visit, doc.cases[0].input.test_sitting, doc.cases[0].input.emitted_at);
  doubled.entry.push(JSON.parse(JSON.stringify(doubled.entry[2])));
  assert.ok(checkBundle(doubled).some((p) => p.includes("appears twice")));
  const broken = emitVisit(doc.cases[0].input.visit, doc.cases[0].input.test_sitting, doc.cases[0].input.emitted_at);
  const prov = broken.entry.find((e) => e.resource.resourceType === "Provenance");
  prov.resource.target.push({ reference: "Observation/nowhere" });
  assert.ok(checkBundle(broken).some((p) => p.includes("does not resolve")));
});
test("fhir_emit: an Observation names the finding and says each value as its display does, as Python", () => {
  const doc = golden("fhir_emit");
  assert.ok(doc.named.length > 0, "the named cases are there");
  for (const c of doc.named) {
    const bundle2 = emitVisit(c.input.visit, null, c.input.emitted_at, c.input.items);
    same(bundle2, c.expected, c.name);
    assert.deepEqual(checkBundle(bundle2), [], `${c.name}: structural check`);
  }
  const first = doc.cases[0];
  const bundle = emitVisit(first.input.visit, first.input.test_sitting, first.input.emitted_at);
  const bank = bundle.entry.map((e) => e.resource).find((r) => r.id.endsWith("-bank-type"));
  assert.equal(bank.code.text, "Artificial bank (Bank Type)");
  assert.ok(bank.text.div.includes("<p>Artificial bank (Bank Type) at Strawberry Creek, campus reach, spot 1: Present. The observer scored 4 of 4 on this feature, tested 2026-09-23.</p>"));
  const pipes = bundle.entry.map((e) => e.resource).find((r) => r.id.endsWith("-draining-pipes"));
  assert.ok(pipes.text.div.includes(": Can't tell. The observer scored"));
});
test("fhir_emit: a rating changed at the rating check is the value, and the first is a component", () => {
  const base = golden("fhir_emit").cases.find((c) => c.name.startsWith("a coarse pin")).input.visit;
  assert.equal(base.answers.overall_rating, "good", "the app stores the first rating as the answer");
  const rated = (first, final) => {
    const bundle = emitVisit({ ...base, first_rating: first, final_rating: final }, null, "2026-09-26T09:16:00Z");
    const byType = (t) => bundle.entry.map((e) => e.resource).filter((r) => r.resourceType === t);
    const qr = byType("QuestionnaireResponse").at(-1);
    const answered = qr.item.find((i) => i.linkId === "overall_rating").answer[0].valueCoding.code;
    const ratings = byType("Observation").filter((o) => o.id.endsWith("-overall-rating"));
    return { bundle, answered, ratings, provenance: byType("Provenance")[0] };
  };
  const changed = rated("good", "poor");
  assert.deepEqual(checkBundle(changed.bundle), []);
  assert.equal(changed.answered, "poor", "the response answers the kept rating");
  assert.equal(changed.ratings.length, 1);
  const [obs] = changed.ratings;
  assert.equal(obs.valueCodeableConcept.coding[0].code, "poor", "the value is the kept rating");
  assert.equal(obs.component.length, 1);
  assert.equal(obs.component[0].code.coding[0].code, "first-rating");
  assert.equal(obs.component[0].valueCodeableConcept.coding[0].code, "good", "the component is the first rating");
  assert.ok(changed.provenance.target.some((t) => t.reference === `Observation/${obs.id}`));
  assert.equal(base.answers.overall_rating, "good", "the stored answers stay as given");
  for (const [first, final] of [["good", "good"], ["good", null], [null, null], [null, "good"]]) {
    const same2 = rated(first, final);
    assert.equal(same2.ratings.length, 0, `${first} then ${final}`);
    assert.equal(same2.answered, "good");
  }
});
test("fhir_referral: the ServiceRequest and the example result, the same as Python", () => {
  const doc = golden("fhir_emit");
  const [referral, example] = doc.referral;
  const made = referralBundle(referral.input.pipe, referral.input.bundles, referral.input.emitted_at);
  same(made, referral.expected, referral.name);
  assert.equal(isExample(made), false, "a referral is real");
  const result = exampleLabResult(example.input.referral, example.input.collected_at, example.input.reported_at);
  same(result, example.expected, example.name);
  assert.equal(isExample(result), true, "the way back is an example, and says so");
  writeBundle(made);
  writeBundle(result);
});
test("walks: the same demo Bundle as Python, tagged on every resource, and structurally sound", () => {
  const doc = golden("walks");
  for (const c of doc.cases) {
    const bundle = walkBundle(c.input.walk, c.input.answers, c.input.answered_at, c.input.final_rating ?? null);
    same(bundle, c.expected, c.name);
    assert.deepEqual(checkBundle(bundle), [], `${c.name}: structural check`);
    assert.ok(isDemo(bundle), `${c.name}: the Bundle carries the demo tag`);
    for (const e of bundle.entry) {
      assert.ok(isDemo(e.resource), `${c.name}: ${String(e.resource.resourceType)} carries the demo tag`);
    }
    writeBundle(bundle);
  }
});
test("walks: the stored row of a finished walk, or the same reason to refuse it, as Python", () => {
  const doc = golden("walks");
  assert.ok(doc.record_cases.length >= 5, "cases that store and cases that refuse");
  let stored2 = 0;
  for (const c of doc.record_cases) {
    let got;
    try {
      got = walkRecord(c.input.walk, c.input.answers, c.input.answered_at, c.input.now, c.input.final_rating ?? null);
    } catch (err) {
      assert.ok(err instanceof WalkRecordError, `${c.name}: ${String(err)}`);
      got = { error: err.message };
    }
    same(got, c.expected, c.name);
    if (!("error" in c.expected)) stored2 += 1;
  }
  assert.ok(stored2 > 0 && stored2 < doc.record_cases.length, "both kinds of case ran");
});
test("walks: the follow-ups a walk asks and the checks kept with it, or the same reason to refuse them, as Python", () => {
  const doc = golden("walks");
  const kinds = /* @__PURE__ */ new Set();
  for (const c of doc.followups_cases) {
    const chosen = walkFollowups(c.input.answers, content_default.followups, content_default.form_items);
    let got;
    try {
      const out = walkChecks(c.input.answers, chosen, c.input.question_texts, c.input.given, c.input.final_rating);
      got = { followups: chosen, checks: out.checks, final_rating: out.final_rating };
      kinds.add(out.checks.length > 0 ? "checks" : "none");
    } catch (err) {
      assert.ok(err instanceof WalkRecordError, `${c.name}: ${String(err)}`);
      got = { followups: chosen, error: err.message };
      kinds.add("error");
    }
    same(got, c.expected, c.name);
  }
  assert.deepEqual([...kinds].sort(), ["checks", "error", "none"], "cases that keep checks, keep none, and refuse");
});
test("old Bundles: only ts- JSON files are deleted, and only the ones in that folder", () => {
  const dir = mkdtempSync(join(tmpdir(), "sl-instances-"));
  for (const f of ["ts-old-visit.json", "ts-old-walk.json", "visit-from-python.json", "ts-notes.txt"]) {
    writeFileSync(join(dir, f), "{}\n");
  }
  assert.deepEqual(clearOldBundles(dir), ["ts-old-visit.json", "ts-old-walk.json"]);
  assert.deepEqual(readdirSync(dir).sort(), ["ts-notes.txt", "visit-from-python.json"]);
  rmSync(dir, { recursive: true });
});
test("old Bundles: every ts- Bundle the validator will read was written by this run", () => {
  assert.ok(written.size > 0, "the tests above wrote Bundles");
  assert.deepEqual(tsBundles(instancesDir), [...written].sort());
});
var jpegParts = (() => {
  const seg = (marker, payload) => [255, marker, payload.length + 2 >> 8, payload.length + 2 & 255, ...payload];
  const text = (s) => [...s].map((c) => c.charCodeAt(0));
  return {
    soi: [255, 216],
    app0: seg(224, [...text("JFIF"), 0, 1, 1, 0, 0, 1, 0, 1, 0, 0]),
    exif: seg(225, [...text("Exif"), 0, 0, ...text("PROBE-GPS 37.87 -122.26")]),
    dqt: seg(219, [0, 1, 2]),
    sos: seg(218, [1, 1, 0, 0, 63, 0]),
    scan: [18, 255, 0, 52, 255, 208, 86],
    eoi: [255, 217]
  };
})();
var has = (bytes, words) => new TextDecoder("latin1").decode(bytes).includes(words);
test("uploads: a JPEG keeps its picture and loses its metadata, wherever the metadata sits", () => {
  const p = jpegParts;
  const picture = [...p.soi, ...p.app0, ...p.dqt, ...p.sos, ...p.scan, ...p.eoi];
  const plain = Uint8Array.from([...p.soi, ...p.app0, ...p.exif, ...p.dqt, ...p.sos, ...p.scan, ...p.eoi]);
  assert.deepEqual([...stripJpeg(plain)], picture);
  const trailing = Uint8Array.from([...picture, ...p.soi, ...p.exif, ...p.sos, ...p.scan, ...p.eoi]);
  assert.deepEqual([...stripJpeg(trailing)], picture);
  const betweenScans = Uint8Array.from([...p.soi, ...p.app0, ...p.dqt, ...p.sos, ...p.scan, ...p.exif, ...p.sos, ...p.scan, ...p.eoi]);
  const out = stripJpeg(betweenScans);
  assert.equal(has(out, "PROBE-GPS"), false);
  assert.deepEqual([...out], [...p.soi, ...p.app0, ...p.dqt, ...p.sos, ...p.scan, ...p.sos, ...p.scan, ...p.eoi]);
  const fill2 = Uint8Array.from([...p.soi, 255, ...p.exif, ...p.app0, ...p.dqt, ...p.sos, ...p.scan, ...p.eoi]);
  assert.equal(has(stripJpeg(fill2), "PROBE-GPS"), false);
});
test("uploads: a JPEG that breaks the shape is refused, not copied with its metadata", () => {
  const p = jpegParts;
  const stray = Uint8Array.from([...p.soi, 0, ...p.exif, ...p.dqt, ...p.sos, ...p.scan, ...p.eoi]);
  assert.throws(() => stripJpeg(stray), /could not be read/);
  const noEnd = Uint8Array.from([...p.soi, ...p.exif, ...p.dqt, ...p.sos, ...p.scan]);
  assert.throws(() => stripJpeg(noEnd), /could not be read/);
  const cut = Uint8Array.from([...p.soi, 255, 225, 64, 0, ...[..."Exif"].map((c) => c.charCodeAt(0))]);
  assert.throws(() => stripJpeg(cut), /could not be read/);
});
test("uploads: a stored photo is put in KV to expire after 30 days", async () => {
  const p = jpegParts;
  const puts = [];
  const env = {
    PHOTOS: {
      put: async (key, _value, options) => {
        puts.push({ key, options });
      }
    },
    DB: { prepare: () => ({ bind: () => ({ run: async () => ({}) }) }) }
  };
  const form = new FormData();
  form.append("file", new Blob([Uint8Array.from([...p.soi, ...p.app0, ...p.exif, ...p.dqt, ...p.sos, ...p.scan, ...p.eoi])], { type: "image/jpeg" }), "photo.jpg");
  const stored2 = await storeUpload(env, new Request("http://127.0.0.1/api/upload", { method: "POST", body: form }), "2026-09-24T10:00:00Z");
  assert.equal(puts.length, 1);
  assert.equal(puts[0].key, `photo:${stored2.photo_id}`);
  assert.equal(puts[0].options.expirationTtl, 30 * 24 * 60 * 60, "30 days, in seconds");
});
test("uploads: the daily run deletes the rows older than 30 days, and only those", async () => {
  assert.equal(uploadCutoff("2026-10-30T04:17:00Z"), "2026-09-30T04:17:00Z", "30 days back, written as created_at is");
  assert.equal(uploadCutoff("2026-03-01T00:00:05Z"), "2026-01-30T00:00:05Z", "across a month's end");
  const ran = [];
  const db = {
    prepare: (sql) => ({
      bind: (...args) => ({
        run: async () => {
          ran.push({ sql, args });
          return { meta: { changes: 3 } };
        }
      })
    })
  };
  assert.equal(await purgeUploads(db, "2026-10-30T04:17:00Z"), 3, "how many rows went");
  assert.deepEqual(ran, [{ sql: "DELETE FROM upload WHERE created_at <= ?", args: ["2026-09-30T04:17:00Z"] }]);
});
function recordingStore(changes = 0) {
  const ran = [];
  const DB = {
    prepare: (sql) => ({
      bind: (...args) => ({
        sql,
        args,
        run: async () => {
          ran.push({ sql, args });
          return { meta: { changes } };
        }
      })
    }),
    batch: async (statements) => statements.map((s) => {
      ran.push({ sql: s.sql, args: s.args });
      return { meta: { changes } };
    })
  };
  return { ran, env: { DB, PHOTOS: {} } };
}
test("cron: one daily run deletes the walks past their date and the old upload rows", async () => {
  const { ran, env } = recordingStore();
  const before = uploadCutoff((/* @__PURE__ */ new Date()).toISOString());
  await src_default.scheduled({}, env);
  const after = uploadCutoff((/* @__PURE__ */ new Date()).toISOString());
  const uploads = ran.filter((r) => r.sql === "DELETE FROM upload WHERE created_at <= ?");
  assert.equal(uploads.length, 1, JSON.stringify(ran));
  const cutoff = String(uploads[0].args[0]);
  assert.ok(before <= cutoff && cutoff <= after, `${cutoff} is 30 days before now`);
  assert.equal(ran.filter((r) => r.sql === "DELETE FROM walk_record WHERE delete_after <= ?").length, 1, "the walks still go");
  const broken = recordingStore();
  broken.env.DB.batch = async () => {
    throw new Error("the walk tables are gone");
  };
  await assert.rejects(() => src_default.scheduled({}, broken.env), /the walk tables are gone/);
  assert.equal(broken.ran.filter((r) => r.sql.startsWith("DELETE FROM upload")).length, 1);
});
test("fhir_http: an error as an OperationOutcome, the same as Python", () => {
  assert.deepEqual(operationOutcome(404, "no FHIR record for this visit"), {
    resourceType: "OperationOutcome",
    text: { status: "generated", div: '<div xmlns="http://www.w3.org/1999/xhtml"><p>no FHIR record for this visit</p></div>' },
    issue: [{ severity: "error", code: "not-found", details: { text: "no FHIR record for this visit" } }]
  });
  assert.deepEqual(
    [404, 409, 413, 422, 429, 500, 503].map((status) => operationOutcome(status, "x").issue[0].code),
    ["not-found", "conflict", "too-long", "invalid", "throttled", "exception", "exception"]
  );
  assert.equal(operationOutcome(404, "a <b> & c").text.div, '<div xmlns="http://www.w3.org/1999/xhtml"><p>a &lt;b&gt; &amp; c</p></div>');
});
test("fhir_http: FHIR's media type, and plain JSON for a browser that opens the link", () => {
  assert.equal(FHIR_JSON, "application/fhir+json; charset=utf-8");
  for (const accept of [null, "", "*/*", "application/fhir+json", "application/json", "application/fhir+json, text/plain"]) {
    assert.equal(fhirMediaType(accept), FHIR_JSON, String(accept));
  }
  for (const accept of ["text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "TEXT/HTML"]) {
    assert.equal(fhirMediaType(accept), PLAIN_JSON, accept);
  }
});
var ask = async (env, address, headers = {}) => {
  const res = await src_default.fetch(new Request(`http://127.0.0.1${address}`, { headers }), env);
  return { status: res.status, type: res.headers.get("content-type"), vary: res.headers.get("vary"), cache: res.headers.get("cache-control"), body: await res.json() };
};
test("routes: a broken percent code in the address is a plain 404", async () => {
  const { ran, env } = recordingStore();
  for (const address of ["/api/spot/%E0%A4%A", "/api/walk/%ff", "/api/city/%", "/api/photo/%E0%A4%A?t=x", "/api/inaturalist/%"]) {
    const answer2 = await ask(env, address);
    assert.deepEqual([answer2.status, answer2.body, answer2.type], [404, { detail: "Not found." }, PLAIN_JSON], address);
  }
  const quick = await src_default.fetch(new Request("http://127.0.0.1/api/quick/%E0%A4%A", { method: "POST", headers: { "content-type": "application/json" }, body: "{}" }), env);
  assert.deepEqual([quick.status, await quick.json()], [404, { detail: "Not found." }]);
  for (const address of ["/api/spot/%E0%A4%A/fhir", "/api/walk/%ff/fhir", "/api/fhir/Bundle/%", "/api/fhir/referral/%", "/api/fhir/referral/%/example-result"]) {
    const answer2 = await ask(env, address);
    assert.deepEqual([answer2.status, answer2.body, answer2.type], [404, operationOutcome(404, "Not found."), FHIR_JSON], address);
  }
  assert.deepEqual(ran, [], "nothing was asked of the store");
});
test("routes: a 500 says one fixed sentence and never the error's own text", async () => {
  const env = {
    DB: {
      prepare: () => {
        throw new Error("D1_ERROR: no such table: spot, asked with the-secret-word");
      }
    },
    PHOTOS: {}
  };
  const sentence = "The server could not take that. Try again in a moment.";
  const plain = await ask(env, "/api/creeks");
  assert.deepEqual([plain.status, plain.body], [500, { detail: sentence }], "no error field");
  const fhir = await ask(env, "/api/fhir/Bundle/visit-0001");
  assert.deepEqual([fhir.status, fhir.body, fhir.type], [500, operationOutcome(500, sentence), FHIR_JSON]);
  const study = await src_default.fetch(new Request("http://127.0.0.1/api/test/counts"), env);
  assert.deepEqual([study.status, await study.json()], [500, { detail: sentence }], "the study routes too");
  for (const answer2 of [plain.body, fhir.body]) assert.ok(!JSON.stringify(answer2).includes("secret") && !JSON.stringify(answer2).includes("D1_ERROR"));
});
test("routes: a FHIR route answers under FHIR's media type, found or not", async () => {
  const rows = {};
  const env = {
    DB: { prepare: () => ({ bind: () => ({ first: async () => rows.next ?? null, all: async () => ({ results: [] }) }) }) },
    PHOTOS: {}
  };
  const missing = await ask(env, "/api/fhir/Bundle/visit-nowhere");
  assert.deepEqual([missing.status, missing.body], [404, operationOutcome(404, "no FHIR record for this visit")]);
  assert.deepEqual([missing.type, missing.vary, missing.cache], [FHIR_JSON, "Accept", "no-store"]);
  const spot = await ask(env, "/api/spot/spot-nowhere/fhir");
  assert.deepEqual([spot.status, spot.body, spot.type], [404, operationOutcome(404, "no FHIR record for this spot yet"), FHIR_JSON]);
  const inBrowser = await ask(env, "/api/fhir/Bundle/visit-nowhere", { accept: "text/html,application/xhtml+xml,*/*;q=0.8" });
  assert.deepEqual([inBrowser.status, inBrowser.type, inBrowser.body], [404, PLAIN_JSON, missing.body], "the same bytes, shown in the tab");
  assert.equal((await ask(env, "/api/fhir/validation")).type, PLAIN_JSON);
  assert.equal((await ask(env, "/api/nothing-here")).type, PLAIN_JSON);
});
