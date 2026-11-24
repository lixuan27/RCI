// Every number below is copied from the paper (tables and figures named in `src`).
// acc = group accuracy Y; nB = token budget in independent agents (completion tokens);
// margin = Y - pass@n_B; level on the equal-budget ladder (0-3). null = not reported in the paper.
window.RCI = {
  settings: {
    split: {
      title: "Split facts", bench: "HiddenBench, 65 official tasks", model: "Qwen3.8-27B, four agents",
      blurb: "Each agent holds part of the decisive facts. No single agent can answer from its own share.",
    },
    corpus: {
      title: "Shared corpus", bench: "DocSweep", model: "Qwen3.8-27B, four agents",
      blurb: "The answer is spread over a corpus that every agent can open, but no agent can read all of it within its budget.",
    },
    same: {
      title: "Same question for all", bench: "GPQA-Diamond", model: "Qwen3.8-27B, four agents",
      blurb: "Every agent sees the whole question. Extra agents add samples from the same distribution.",
    },
    org: {
      title: "Self-organization", bench: "HiddenBench", model: "Qwen3.8-27B, four agents, one message of reading each",
      blurb: "Members may give their reading budget away, so the group can build its own structure.",
    },
  },

  // ---------------- split facts (Table 2, Figure 5b, Table 9) ----------------
  split: [
    {id:"bb", fam:"Argue", flow:"board", name:"Blackboard", hint:false, acc:0.369, nB:8.6, margin:-0.331, level:2, src:"Table 2"},
    {id:"bbh", fam:"Argue", flow:"board", name:"Blackboard", hint:true, acc:null, nB:null, margin:0.043, level:2, src:"Figure 5b"},
    {id:"deb2", fam:"Argue", flow:"debate", name:"Debate", rounds:2, hint:false, acc:0.688, nB:8.8, margin:-0.015, level:2, src:"Table 2"},
    {id:"deb2h", fam:"Argue", flow:"debate", name:"Debate", rounds:2, hint:true, acc:0.782, nB:8.8, margin:0.079, level:2, src:"Table 9 (row 2: 0.959 - 0.177)"},
    {id:"deb3h", fam:"Argue", flow:"debate", name:"Debate", rounds:3, hint:true, acc:0.841, nB:11.1, margin:0.109, level:3, src:"Table 2"},
    {id:"sc", fam:"Fact", flow:"context", name:"Shared context", acc:0.881, nB:7.9, margin:0.190, level:3, src:"Table 2"},
    {id:"ff", fam:"Fact", flow:"forward", name:"Fact forwarding", acc:0.959, nB:6.2, margin:0.310, level:3, src:"Table 2"},
    {id:"scff", fam:"Fact", flow:"context+forward", name:"Shared context + forwarding", acc:0.972, nB:6.0, margin:0.328, level:3, src:"Table 2"},
    {id:"fobb", fam:"Fact", flow:"board-facts", name:"Facts-only blackboard", acc:null, nB:null, margin:0.137, level:3, src:"Figure 5b"},
    {id:"gbb", fam:"Fact", flow:"board-gated", name:"Gated blackboard", acc:null, nB:null, margin:0.234, level:3, src:"Figure 5b"},
  ],
  fullInfoAgent: 0.942, // Table 2: full-information agent at equal budget

  // fact forwarding across model scales (Table 9 rows 1-3)
  scales: [
    {model:"Qwen3.5-9B", acc:0.834, nB:9.5, margin:0.160, level:3, src:"Table 9, Figure 11b"},
    {model:"Qwen3.8-27B", acc:0.959, nB:6.2, margin:0.310, level:3, src:"Table 2"},
    {model:"Qwen3.6-35B-A3B", acc:null, nB:10.6, margin:0.181, level:3, src:"Table 9"},
  ],

  // ---------------- shared corpus and same question (Table 1) ----------------
  corpus: [
    {id:"so", fam:"Self", flow:"selforg", name:"Self-organized", acc:0.200, nB:4.93, margin:0.026, level:2, src:"Table 1"},
    {id:"swp", fam:"Notes", flow:"prompt", name:"Self-written prompt", acc:0.861, nB:4.02, margin:0.706, level:3, src:"Table 1"},
    {id:"agg", fam:"Design", flow:"aggregator", name:"Designed aggregator", acc:0.930, nB:4.56, margin:0.759, level:3, src:"Table 1"},
  ],
  same: [
    {id:"bb", fam:"Argue", flow:"board", name:"Blackboard", acc:0.909, nB:4.22, margin:-0.039, level:0, src:"Table 1"},
    {id:"deb2", fam:"Argue", flow:"debate", name:"Debate, 2 rounds", acc:0.899, nB:4.24, margin:-0.049, level:0, src:"Table 1"},
  ],

  // ---------------- self-organization (Table 3, Table 9b) ----------------
  org: {
    free: [
      {id:"none", fam:"Solo", flow:"noxfer", name:"No transfer", acc:0.496, nB:20.3, margin:-0.300, level:2, tasks:65, src:"Table 3a"},
      {id:"so", fam:"Self", flow:"selforg", name:"Self-organized", acc:0.677, nB:21.3, margin:-0.124, level:2, tasks:65, src:"Table 3a"},
      {id:"sop", fam:"Self", flow:"selforg-plan", name:"Self-organized + planning round", acc:0.822, nB:18.3, margin:0.037, level:2, tasks:65, src:"Table 3a",
        share:{wait:0.258, coord:0.67, note:"56 tasks", src:"Table 9b"}},
      {id:"rules", fam:"Notes", flow:"prompt", name:"Prompt written from the rules", acc:0.879, nB:9.2, margin:0.205, level:3, tasks:56, descriptive:true, src:"Table 3a"},
      {id:"evolved", fam:"Notes", flow:"prompt", name:"Prompt evolved over 4 generations", acc:0.862, nB:9.7, margin:0.180, level:3, tasks:56, descriptive:true, src:"Table 3a"},
      {id:"hub", fam:"Design", flow:"hub", name:"Designed hub", acc:0.863, nB:11.3, margin:0.130, level:3, tasks:65, src:"Table 3a"},
    ],
    cap: [
      {id:"none", fam:"Solo", flow:"norelay", name:"No relay", acc:0.571, nB:37.0, margin:-0.267, level:2, tasks:56, src:"Table 3a"},
      {id:"so", fam:"Self", flow:"relay", name:"Self-organized", acc:0.689, nB:40.7, margin:-0.159, level:2, tasks:56, src:"Table 3a"},
      {id:"sop", fam:"Self", flow:"relay-plan", name:"Self-organized + planning round", acc:0.677, nB:44.4, margin:-0.180, level:2, tasks:56, src:"Table 3a",
        share:{wait:0.377, coord:0.69, src:"Table 9b"}},
      {id:"rules", fam:"Notes", flow:"prompt-cap", name:"Prompt written from the rules", acc:0.732, nB:40.2, margin:-0.115, level:2, tasks:56, src:"Table 3a",
        share:{wait:0.404, coord:0.67, src:"Table 9b"}},
      {id:"evolved", fam:"Notes", flow:"prompt-cap", name:"Prompt evolved over 4 generations", acc:0.840, nB:25.0, margin:0.043, level:2, tasks:56, src:"Table 3a",
        share:{wait:0.332, coord:0.64, src:"Table 9b"}},
      {id:"tree", fam:"Design", flow:"tree", name:"Designed tree", acc:0.802, nB:10.8, margin:0.107, level:3, tasks:56, beforeMTC:true, src:"Table 3a",
        share:{wait:0.308, coord:0.50, src:"Table 9b"}},
    ],
    families: [ // Table 3b: share of records with a hub, with a transfer, and the accuracy gain from allowing transfers
      {model:"Qwen3.5-4B", hubs:0.000, transfers:0.024, gain:0.027},
      {model:"Qwen3.5-9B", hubs:0.000, transfers:0.008, gain:-0.001},
      {model:"Qwen3.6-35B-A3B", hubs:0.000, transfers:0.004, gain:0.025},
      {model:"Qwen3.8-27B", hubs:0.345, transfers:0.611, gain:0.181},
      {model:"GLM-4.5-Air", hubs:0.000, transfers:0.017, gain:0.025},
      {model:"gpt-oss-120b", hubs:0.045, transfers:0.372, gain:0.036},
    ],
  },

  // ---------------- prior methods under shared information (Table 12, Qwen3.5-9B) ----------------
  prior: {
    methods: ["Multi-agent debate","DeLM","AOrchestra","Blackboard","Blackboard + 9B reviewer","Blackboard + 27B reviewer"],
    rows: [
      ["Multi-agent debate","GPQA-Diamond",4,-0.005,0.013],["Multi-agent debate","GPQA-Diamond",8,0.008,0.015],["Multi-agent debate","GPQA-Diamond",16,0.022,0.016],
      ["Multi-agent debate","BrowseComp-Plus",4,-0.055,0.036],["Multi-agent debate","BrowseComp-Plus",8,-0.178,0.032],["Multi-agent debate","BrowseComp-Plus",16,-0.163,0.031],
      ["Multi-agent debate","LongBench v2",8,-0.016,0.014],["Multi-agent debate","MMLongBench-Doc",16,-0.016,0.017],["Multi-agent debate","SWE-bench Verified",8,-0.173,0.025],
      ["Multi-agent debate","FATE-M",4,-0.057,0.029],["Multi-agent debate","FATE-M",8,-0.045,0.028],
      ["DeLM","GPQA-Diamond",4,0.022,0.014],["DeLM","GPQA-Diamond",8,0.015,0.011],["DeLM","GPQA-Diamond",16,0.022,0.015],
      ["DeLM","BrowseComp-Plus",4,-0.002,0.044],["DeLM","BrowseComp-Plus",16,-0.243,0.044],["DeLM","MMLongBench-Doc",16,-0.066,0.022],
      ["DeLM","SWE-bench Verified",8,-0.506,0.034],["DeLM","FATE-M",4,-0.235,0.035],["DeLM","FATE-M",8,-0.304,0.041],
      ["AOrchestra","GPQA-Diamond",null,0.021,0.020],["AOrchestra","BrowseComp-Plus",null,-0.075,0.046],["AOrchestra","MMLongBench-Doc",null,-0.112,0.022],["AOrchestra","SWE-bench Verified",null,-0.360,0.043],
      ["Blackboard","GPQA-Diamond",16,0.013,0.014],["Blackboard","BrowseComp-Plus",16,0.016,0.026],["Blackboard","LongBench v2",8,-0.013,0.012],["Blackboard","MMLongBench-Doc",16,0.013,0.017],
      ["Blackboard + 9B reviewer","GPQA-Diamond",16,0.010,0.018],["Blackboard + 9B reviewer","BrowseComp-Plus",16,0.113,0.036],["Blackboard + 9B reviewer","LongBench v2",8,0.016,0.015],["Blackboard + 9B reviewer","MMLongBench-Doc",16,-0.025,0.019],
      ["Blackboard + 27B reviewer","GPQA-Diamond",16,0.050,0.019],["Blackboard + 27B reviewer","BrowseComp-Plus",16,0.131,0.038],["Blackboard + 27B reviewer","LongBench v2",8,0.037,0.015],["Blackboard + 27B reviewer","MMLongBench-Doc",16,0.044,0.018],
    ],
  },

  // ---------------- recursion ----------------
  splitbench: { // Table 4: margin over pass@n of base-model agents, 196 held-out SplitBench tasks
    chains: [
      {name:"Qwen3.5-9B, 3-step debate", m:[-0.253,-0.028,0.159], control:-0.033, g2MinusControl:0.192},
      {name:"Qwen3.8-27B, 3-step debate", m:[-0.009,0.201,0.284], control:0.016, g2MinusControl:0.268},
      {name:"Qwen3.5-9B, standard debate", m:[-0.228,-0.090,0.098]},
      {name:"Qwen3.5-4B, standard debate", m:[-0.498,-0.077,0.117]},
    ],
  },
  planbench: { // Table 6 (selection set, 300 problems)
    group:[0.613,0.857,0.937,0.940,0.950], anyOfFour:[0.683,0.860,0.937,0.947,0.950],
    draft:[0.371,0.480,0.591,0.630,0.672], final:[0.423,0.610,0.707,0.752,0.773],
    truncated:[0.598,0.447,0.343,0.297,0.265], tokensPerCall:[7416,6802,6651,6523,6541],
    d:[null,[0.295,0.020],[0.080,0.014],[0.024,0.012],[0.021,0.010]],
  },
  hiddenbench: { // Figure 11a (selection set, 200 tasks x 2 seeds)
    t3k:[0.509,0.713,0.791,0.811,0.845,0.886], t3kOne:[0.501,0.710,0.774,0.780,0.828,0.878], t3kTokensK:[19.2,22.6,22.4,22.1,21.2,20.3],
    t3:[0.509,0.703,0.755,0.836], selfFour:[0.070,0.396,0.563,0.658,0.672], selfOne:[0.148,0.408,0.475,0.558,0.564],
    rounds:[ // Figure 10b: confirmation, candidate vs current generation, every round of T3k
      {r:1,parent:0.4913,cand:0.6946,d:0.203,rel:"G1"},{r:2,parent:0.7344,cand:0.7788,d:0.044,rel:"G2"},{r:3,parent:0.8069,cand:0.8075,d:0.001,rel:null},
      {r:4,parent:0.7800,cand:0.8238,d:0.044,rel:"G3"},{r:5,parent:0.7900,cand:0.8550,d:0.065,rel:"G4"},{r:6,parent:0.8250,cand:0.8263,d:0.001,rel:null},
      {r:7,parent:0.8237,cand:0.8700,d:0.046,rel:"G5"},{r:8,parent:0.9038,cand:0.9183,d:0.015,rel:null}],
  },
  hanabi: { // Table 7: challenge score out of 25
    rec:[0,0.678,2.953,4.110,4.420,4.523,4.482], control:[null,0.678,2.000,2.907],
    gain:[null,[0.678,0.045],[2.363,0.075],[1.102,0.087],[0.208,0.077],[0.087,0.074],[0.125,0.075]],
  },
};
