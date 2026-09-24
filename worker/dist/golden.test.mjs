// test/golden.test.ts
import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

// src/content.json
var content_default = {
  content_hash: "3436a125a9e7df63",
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
      flat: "Flat channel",
      good: "Good overall rating",
      "invasive-plant": "Invasive plant",
      "lab-ecoli-cfu": "Escherichia coli, colony forming units",
      "lab-enterobacteriaceae-share": "Enterobacteriaceae, share of 16S reads",
      "lab-hf183": "Human faecal marker HF183",
      "leaf-deposits": "Deposits of fallen leaves",
      moderate: "Moderate overall rating",
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
      options: [
        {
          id: "flat",
          label: "Flat",
          value: "flat"
        },
        {
          id: "u_shape",
          label: "U shape",
          value: "u_shape"
        },
        {
          id: "v_shape",
          label: "V shape",
          value: "v_shape"
        },
        {
          id: "not_sure",
          label: "I'm not sure",
          value: "cant_tell"
        }
      ],
      section: "what_you_see",
      text: "Channel form",
      type: "choice",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah"
      },
      id: "bottom_type",
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
          label: "Not sure",
          value: "cant_tell"
        }
      ],
      section: "what_you_see",
      text: "Bottom type",
      type: "choice",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: "artificial_bank",
      fhir: {
        category: "morophology",
        code: "artificial-bank",
        code_system: "sl"
      },
      id: "bank_type",
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
          label: "Laid stones with no concrete",
          value: "absent"
        },
        {
          id: "not_sure",
          label: "Not sure",
          value: "cant_tell"
        }
      ],
      section: "what_you_see",
      short_label: "artificial banks",
      text: "Bank type",
      type: "choice",
      verified_against_app: false,
      wording_source: "master_brief"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah"
      },
      id: "habitats",
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
      text: "Habitats",
      type: "multi",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah"
      },
      id: "natural_debris",
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
      text: "Natural debris",
      type: "multi",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "hydrology",
        code_system: "oah"
      },
      id: "water_flow",
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
          label: "Stagnant or intermittent",
          value: "stagnant"
        },
        {
          id: "dry",
          label: "Dry",
          value: "dry"
        },
        {
          id: "not_sure",
          label: "Not sure",
          value: "cant_tell"
        }
      ],
      section: "what_you_see",
      text: "Water flow",
      type: "choice",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "foam",
        code_system: "oah"
      },
      id: "water_aspect",
      options: [
        {
          id: "clear",
          label: "Clear or transparent",
          value: "absent"
        },
        {
          id: "muddy",
          label: "Muddy or turbid",
          value: "present"
        },
        {
          id: "foam",
          label: "Has foam",
          value: "present"
        },
        {
          id: "colour",
          label: "Has colours or altered colour",
          value: "present"
        },
        {
          id: "not_sure",
          label: "Not sure",
          value: "cant_tell"
        }
      ],
      section: "water",
      text: "How is the water?",
      type: "choice",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "hydrology",
        code_system: "oah"
      },
      id: "water_withdrawal",
      section: "water",
      text: "Is there any kind of obvious water collection, use or removal from the stream?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah"
      },
      id: "barriers",
      section: "water",
      text: "Do you see any dams or other transversal artificial barriers?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: "pipe_running",
      fhir: {
        category: "hydrology",
        code: "pipe-running",
        code_system: "sl"
      },
      id: "draining_pipes",
      section: "water",
      text: "Are there pipes draining polluted water into the stream?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "master_brief"
    },
    {
      feature: "pipe_running",
      fhir: {
        category: "hydrology",
        code: "pipe-running",
        code_system: "sl"
      },
      id: "sewage_discharge",
      section: "water",
      short_label: "a sewage discharge",
      text: "Is there any kind of water entry or discharge of sewage?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "master_brief"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah"
      },
      id: "construction",
      section: "water",
      text: "Is there any construction or works in the stream?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "hydrology",
        code_system: "oah",
        unit: "m"
      },
      id: "water_height_m",
      section: "water",
      text: "Water height in metres",
      type: "number",
      unit: "m",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "LandUse",
        code_system: "oah"
      },
      id: "impervious_left",
      section: "margins",
      short_label: "a paved left margin",
      text: "Is more than one third of the left margin covered by impervious areas (such as roads, sidewalks or buildings)?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "master_brief"
    },
    {
      feature: null,
      fhir: {
        code: "LandUse",
        code_system: "oah"
      },
      id: "impervious_right",
      section: "margins",
      short_label: "a paved right margin",
      text: "Is more than one third of the right margin covered by impervious areas (such as roads, sidewalks or buildings)?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "master_brief"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah"
      },
      id: "vegetation_left",
      section: "margins",
      text: "Is the left margin covered by vegetation?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah"
      },
      id: "vegetation_right",
      section: "margins",
      text: "Is the right margin covered by vegetation?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah"
      },
      id: "vegetation_type_left",
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
          label: "Not sure",
          value: "cant_tell"
        }
      ],
      section: "margins",
      text: "Left margin: what is dominant (more than half) in the first 5 m?",
      type: "choice",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah"
      },
      id: "vegetation_type_right",
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
          label: "Not sure",
          value: "cant_tell"
        }
      ],
      section: "margins",
      text: "Right margin: what is dominant (more than half) in the first 5 m?",
      type: "choice",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: "invasive_plant",
      fhir: {
        category: "invasiveOrganisms",
        code: "invasive-plant",
        code_system: "sl"
      },
      id: "invasive_species",
      section: "margins",
      short_label: "invasive plants",
      text: "Do you see any non-native or invasive plant species?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "master_brief"
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
      text: "Which ones?",
      type: "pick_region_list",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah"
      },
      id: "vegetation_cuts",
      section: "margins",
      text: "Have there been recent cuts of vegetation (partial or total) on the banks?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "app_public_text"
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
      text: "Which feelings best describe your experience?",
      type: "sliders",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: null,
      id: "overall_rating",
      options: [
        {
          id: "good",
          label: "Good: the ecosystem components are there, riparian vegetation, natural channel, good water quality, biodiversity",
          value: "good"
        },
        {
          id: "moderate",
          label: "Moderate: some alterations, still biodiverse, with vegetation in the margins, water looks good",
          value: "moderate"
        },
        {
          id: "poor",
          label: "Poor: highly modified or artificialized, loss of riparian vegetation, loss of habitats, polluted",
          value: "poor"
        }
      ],
      rating_check: true,
      section: "overall",
      text: "Overall, how would you rate this stream?",
      type: "choice",
      verified_against_app: false,
      wording_source: "app_public_text"
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
  region_plants: [],
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
      flat: "Flat channel",
      good: "Good overall rating",
      "invasive-plant": "Invasive plant",
      "lab-ecoli-cfu": "Escherichia coli, colony forming units",
      "lab-enterobacteriaceae-share": "Enterobacteriaceae, share of 16S reads",
      "lab-hf183": "Human faecal marker HF183",
      "leaf-deposits": "Deposits of fallen leaves",
      moderate: "Moderate overall rating",
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
  form_items: [
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah"
      },
      id: "channel_form",
      options: [
        {
          id: "flat",
          label: "Flat",
          value: "flat"
        },
        {
          id: "u_shape",
          label: "U shape",
          value: "u_shape"
        },
        {
          id: "v_shape",
          label: "V shape",
          value: "v_shape"
        },
        {
          id: "not_sure",
          label: "I'm not sure",
          value: "cant_tell"
        }
      ],
      section: "what_you_see",
      text: "Channel form",
      type: "choice",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah"
      },
      id: "bottom_type",
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
          label: "Not sure",
          value: "cant_tell"
        }
      ],
      section: "what_you_see",
      text: "Bottom type",
      type: "choice",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: "artificial_bank",
      fhir: {
        category: "morophology",
        code: "artificial-bank",
        code_system: "sl"
      },
      id: "bank_type",
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
          label: "Laid stones with no concrete",
          value: "absent"
        },
        {
          id: "not_sure",
          label: "Not sure",
          value: "cant_tell"
        }
      ],
      section: "what_you_see",
      short_label: "artificial banks",
      text: "Bank type",
      type: "choice",
      verified_against_app: false,
      wording_source: "master_brief"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah"
      },
      id: "habitats",
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
      text: "Habitats",
      type: "multi",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah"
      },
      id: "natural_debris",
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
      text: "Natural debris",
      type: "multi",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "hydrology",
        code_system: "oah"
      },
      id: "water_flow",
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
          label: "Stagnant or intermittent",
          value: "stagnant"
        },
        {
          id: "dry",
          label: "Dry",
          value: "dry"
        },
        {
          id: "not_sure",
          label: "Not sure",
          value: "cant_tell"
        }
      ],
      section: "what_you_see",
      text: "Water flow",
      type: "choice",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "foam",
        code_system: "oah"
      },
      id: "water_aspect",
      options: [
        {
          id: "clear",
          label: "Clear or transparent",
          value: "absent"
        },
        {
          id: "muddy",
          label: "Muddy or turbid",
          value: "present"
        },
        {
          id: "foam",
          label: "Has foam",
          value: "present"
        },
        {
          id: "colour",
          label: "Has colours or altered colour",
          value: "present"
        },
        {
          id: "not_sure",
          label: "Not sure",
          value: "cant_tell"
        }
      ],
      section: "water",
      text: "How is the water?",
      type: "choice",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "hydrology",
        code_system: "oah"
      },
      id: "water_withdrawal",
      section: "water",
      text: "Is there any kind of obvious water collection, use or removal from the stream?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah"
      },
      id: "barriers",
      section: "water",
      text: "Do you see any dams or other transversal artificial barriers?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: "pipe_running",
      fhir: {
        category: "hydrology",
        code: "pipe-running",
        code_system: "sl"
      },
      id: "draining_pipes",
      section: "water",
      text: "Are there pipes draining polluted water into the stream?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "master_brief"
    },
    {
      feature: "pipe_running",
      fhir: {
        category: "hydrology",
        code: "pipe-running",
        code_system: "sl"
      },
      id: "sewage_discharge",
      section: "water",
      short_label: "a sewage discharge",
      text: "Is there any kind of water entry or discharge of sewage?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "master_brief"
    },
    {
      feature: null,
      fhir: {
        code: "morophology",
        code_system: "oah"
      },
      id: "construction",
      section: "water",
      text: "Is there any construction or works in the stream?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "hydrology",
        code_system: "oah",
        unit: "m"
      },
      id: "water_height_m",
      section: "water",
      text: "Water height in metres",
      type: "number",
      unit: "m",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "LandUse",
        code_system: "oah"
      },
      id: "impervious_left",
      section: "margins",
      short_label: "a paved left margin",
      text: "Is more than one third of the left margin covered by impervious areas (such as roads, sidewalks or buildings)?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "master_brief"
    },
    {
      feature: null,
      fhir: {
        code: "LandUse",
        code_system: "oah"
      },
      id: "impervious_right",
      section: "margins",
      short_label: "a paved right margin",
      text: "Is more than one third of the right margin covered by impervious areas (such as roads, sidewalks or buildings)?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "master_brief"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah"
      },
      id: "vegetation_left",
      section: "margins",
      text: "Is the left margin covered by vegetation?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah"
      },
      id: "vegetation_right",
      section: "margins",
      text: "Is the right margin covered by vegetation?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah"
      },
      id: "vegetation_type_left",
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
          label: "Not sure",
          value: "cant_tell"
        }
      ],
      section: "margins",
      text: "Left margin: what is dominant (more than half) in the first 5 m?",
      type: "choice",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah"
      },
      id: "vegetation_type_right",
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
          label: "Not sure",
          value: "cant_tell"
        }
      ],
      section: "margins",
      text: "Right margin: what is dominant (more than half) in the first 5 m?",
      type: "choice",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: "invasive_plant",
      fhir: {
        category: "invasiveOrganisms",
        code: "invasive-plant",
        code_system: "sl"
      },
      id: "invasive_species",
      section: "margins",
      short_label: "invasive plants",
      text: "Do you see any non-native or invasive plant species?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "master_brief"
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
      text: "Which ones?",
      type: "pick_region_list",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: {
        code: "riparianVegetation",
        code_system: "oah"
      },
      id: "vegetation_cuts",
      section: "margins",
      text: "Have there been recent cuts of vegetation (partial or total) on the banks?",
      type: "yesno",
      verified_against_app: false,
      wording_source: "app_public_text"
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
      text: "Which feelings best describe your experience?",
      type: "sliders",
      verified_against_app: false,
      wording_source: "app_public_text"
    },
    {
      feature: null,
      fhir: null,
      id: "overall_rating",
      options: [
        {
          id: "good",
          label: "Good: the ecosystem components are there, riparian vegetation, natural channel, good water quality, biodiversity",
          value: "good"
        },
        {
          id: "moderate",
          label: "Moderate: some alterations, still biodiverse, with vegetation in the margins, water looks good",
          value: "moderate"
        },
        {
          id: "poor",
          label: "Poor: highly modified or artificialized, loss of riparian vegetation, loss of habitats, polluted",
          value: "poor"
        }
      ],
      rating_check: true,
      section: "overall",
      text: "Overall, how would you rate this stream?",
      type: "choice",
      verified_against_app: false,
      wording_source: "app_public_text"
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
function observerLabel(score, featureName, today, locale) {
  if (score === null) return { text: "", expired: false, passed: null };
  const tested = shortDate(score.tested_on);
  const params = { correct: score.correct, total: score.total, feature: featureName, date: tested };
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
      if (!(feature in MEASURE_FOR_FEATURE) || !present(value)) continue;
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
      row.visit_ids.push(v.visit_id);
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
function downstreamNote(finding, featureName, reachSlugs) {
  const n = finding.observers.length;
  const people = n === 1 ? "one person" : `${n} people`;
  const line = `Upstream of here, ${people} reported ${featureName} on ${shortDate(finding.last_seen)}.`;
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
function narrative(text) {
  return { status: "generated", div: `<div xmlns="http://www.w3.org/1999/xhtml"><p>${escapeXml(text)}</p></div>` };
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
    text: narrative(`Creek check at ${visit.spot.spot_name} on ${instant(visit.answered_at)}, ${qrItems.length} items answered.`),
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
  let words = `${item.text ?? item.id} at ${visit.spot.spot_name}: `;
  let valuePart;
  if (typeof value === "boolean") {
    throw new FhirEmitError(`item ${item.id}: boolean answers are not allowed, use present/absent`);
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return null;
    valuePart = { component: components(item, value) };
    words += value.map((v) => String(v).replace(/_/g, " ")).join(", ") + ".";
  } else if (typeof value === "number") {
    const unit = fhir.unit || item.unit;
    if (!unit) throw new FhirEmitError(`item ${item.id}: a number needs a UCUM unit in form.yaml`);
    valuePart = { valueQuantity: quantity(value, unit) };
    words += `${pyFloat(value)} ${UCUM_DISPLAYS[unit] ?? unit}.`;
  } else {
    valuePart = { valueCodeableConcept: valueConcept(value) };
    words += value.replace(/_/g, " ") + ".";
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
    code: concept(itemCode(item), item.text),
    subject: ref("Location", spotLocationId),
    effectiveDateTime: instant(visit.answered_at),
    performer: [ref("Practitioner", pid)],
    ...valuePart,
    derivedFrom: [ref("QuestionnaireResponse", visitQrId)]
  };
  return out;
}
function provenance(visit, observations, pid, visitQrId, testQrId, emittedAt) {
  const entities = [{ role: "source", what: ref("QuestionnaireResponse", visitQrId) }];
  if (testQrId) entities.push({ role: "source", what: ref("QuestionnaireResponse", testQrId) });
  return {
    resourceType: "Provenance",
    id: fhirId("sl-provenance", visit.visit_id),
    text: narrative(
      `${observations.length} observations from one creek check, answered by the volunteer and assembled by the Second Look software. The sources are the visit and the observer test sitting.`
    ),
    target: observations.map((o) => ref("Observation", String(o.id))),
    recorded: instant(emittedAt),
    agent: [
      { type: concept(coding(PROVENANCE_TYPE_SYSTEM, "author")), who: ref("Practitioner", pid) },
      { type: concept(coding(PROVENANCE_TYPE_SYSTEM, "assembler")), who: ref("Device", DEVICE_ID) }
    ],
    entity: entities
  };
}
function emitVisit(visit, testSitting, emittedAt, items = FORM_ITEMS) {
  const [creek, reach, spot] = locations(visit);
  const tested = testedOn(visit, testSitting);
  const person = practitioner(visit, tested);
  const pid = String(person.id);
  const testQr = testSitting ? testResponse(testSitting, pid) : null;
  const visitQr = visitResponse(visit, pid, items);
  const scores = /* @__PURE__ */ new Map();
  for (const s of testSitting ? testSitting.scores : visit.observer.scores) scores.set(s.feature, s);
  const observations = [];
  for (const item of items) {
    if (!item.fhir || !(item.id in visit.answers)) continue;
    const obs = observation(visit, item, visit.answers[item.id], pid, String(spot.id), String(visitQr.id), scores.get(String(item.feature ?? "")) ?? null);
    if (obs !== null) observations.push(obs);
  }
  const prov = provenance(visit, observations, pid, String(visitQr.id), testQr ? String(testQr.id) : null, emittedAt);
  const resources2 = [organization(), device(visit.software_version), creek, reach, spot, person];
  if (testQr) resources2.push(testQr);
  resources2.push(visitQr, ...observations, prov);
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
  const observations = [];
  const provenances = [];
  entries.forEach((e, i) => {
    const r = e.resource ?? {};
    const rtype = String(r.resourceType);
    const label = `entry[${i}] ${rtype}/${r.id ?? e.fullUrl ?? "?"}`;
    walk(r, label);
    if (rtype === "Observation") {
      observations.push(bundle.type !== "transaction" ? `Observation/${r.id}` : String(e.fullUrl ?? ""));
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
    for (const obs of observations) if (!targets.has(obs)) problems.push(`Provenance does not target ${obs}`);
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
var RATING_ITEM = "overall_rating";
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
  if (answers[RATING_ITEM] !== BEST_RATING) return null;
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
    params: { issues: issues.join(", "), first_rating: BEST_RATING }
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
        followup = checkerEnabled && flags.length > 0 ? null : null;
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
var DEMO_TAG_DISPLAY = "Demo visit from a video walk. Made on the device, never stored or counted.";
var WALK_PREFIX = "walk-";
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
function walkVisit(walk, answers, answeredAt) {
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
    software_version: "0.1.0"
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
function walkBundle(walk, answers, answeredAt) {
  const visit = walkVisit(walk, answers, answeredAt);
  return tagDemo(emitVisit(visit, null, instant(answeredAt)));
}
function isDemo(bundle) {
  const tags = bundle.meta?.tag ?? [];
  return tags.some((t) => t.system === DEMO_TAG_SYSTEM && t.code === DEMO_TAG_CODE);
}

// src/check.ts
var Invalid = class extends Error {
};
var LOCALE = content_default.locale;
var REGION_PLANTS = /* @__PURE__ */ new Set([...content_default.region_plants, "cant_tell"]);
var randomHex = (bytes) => Array.from(crypto.getRandomValues(new Uint8Array(bytes)), (b) => b.toString(16).padStart(2, "0")).join("");

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
test("followups: the selector, over the repository's own table and form", () => {
  const doc = golden("followups");
  for (const c of doc.cases) {
    const chosen = selectFollowups(c.input.answers, c.input.site, c.input.observer, [], content_default.followups, content_default.form_items, c.input.checker_enabled);
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
    const bundle = walkBundle(c.input.walk, c.input.answers, c.input.answered_at);
    same(bundle, c.expected, c.name);
    assert.deepEqual(checkBundle(bundle), [], `${c.name}: structural check`);
    assert.ok(isDemo(bundle), `${c.name}: the Bundle carries the demo tag`);
    for (const e of bundle.entry) {
      assert.ok(isDemo(e.resource), `${c.name}: ${String(e.resource.resourceType)} carries the demo tag`);
    }
    writeBundle(bundle);
  }
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
  const stored = await storeUpload(env, new Request("http://127.0.0.1/api/upload", { method: "POST", body: form }), "2026-09-24T10:00:00Z");
  assert.equal(puts.length, 1);
  assert.equal(puts[0].key, `photo:${stored.photo_id}`);
  assert.equal(puts[0].options.expirationTtl, 30 * 24 * 60 * 60, "30 days, in seconds");
});
