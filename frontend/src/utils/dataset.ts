const datasetOptionLabels: Record<string, string> = {
  "supergpqa": "SuperGPQA",
  "gpqa": "GPQA",
  "aime25": "AIME25",
  "aime26": "AIME26",
  "hmmt-nov-25": "HMMT-Nov-25",
  "hmmt-feb-26": "HMMT-Feb-26",
  "hmt-nov-25": "HMT-Nov-25",
  "beyondaime": "BeyondAIME",
  "imo-answerbench": "IMO-AnswerBench",
  "u-math": "U-Math",
  "ifeval": "IFEval",
  "arena-hard-v2": "Arena-Hard-v2",
  "mmmlu-lite": "MMMLU-Lite",
  "global-piqa": "Global-PIQA",
  "aa-lcr": "AA-LCR",
  "mrcr-v2": "MRCR-v2",
  "longbench": "LongBench",
  "livecodebench-v6": "LiveCodeBench-v6",
  "livecodebench-pro": "LiveCodeBench-Pro",
  "artifactbench": "ArtifactBench",
  "repoqa": "RepoQA",
  "multipl-e": "Multipl-E",
  "bfcl-v3": "BFCL-v3",
  "pinchbench": "PinchBench",
  "pinchbnch": "PinchBench",
  "pinch-bench": "PinchBench",
  "pinch_bench": "PinchBench",
  "数学": "Math-Smoke",
  "物理": "Physics-Smoke",
  "化学": "Chemistry-Smoke",
  "数学冒烟集": "Math-Smoke",
  "物理冒烟集": "Physics-Smoke",
  "化学冒烟集": "Chemistry-Smoke",
  "swe-bench-verified": "SWE-Bench-Verified",
  "swe_bench_verified": "SWE-Bench-Verified",
  "swebenchverified": "SWE-Bench-Verified",
  "multiswebench": "MultiSWEBench",
  "multi-swebench": "MultiSWEBench",
  "multi_swebench": "MultiSWEBench",
  "multi-swe-bench": "MultiSWEBench",
  "multi_swe_bench": "MultiSWEBench",
  "browsecomp": "BrowseComp",
  "browse-comp": "BrowseComp",
  "browse_comp": "BrowseComp",
  "browsecomp-zn": "BrowseComp-zn",
  "browsecomp_zn": "BrowseComp-zn",
  "browse-comp-zn": "BrowseComp-zn",
  "browse_comp_zn": "BrowseComp-zn",
  "ruler": "RULER",
  "korbench": "KorBench",
  "kor-bench": "KorBench",
  "kor_bench": "KorBench",
  "writingbench": "WritingBench",
  "writing-bench": "WritingBench",
  "writing_bench": "WritingBench",
  "creativewriting": "CreativeWriting",
  "creative-writing": "CreativeWriting",
  "creative_writing": "CreativeWriting",
  "disco-x": "Disco-X",
  "disco_x": "Disco-X",
  "discox": "Disco-X",
  "multichallenge": "MultiChallenge",
  "multi-challenge": "MultiChallenge",
  "multi_challenge": "MultiChallenge",
  "simpleqa": "SimpleQA",
  "c-simpleqa": "C-SimpleQA",
  "supergpqa-med": "SuperGPQA-Med",
  "medmcqa": "MedMCQA",
  "medqa": "MedQA",
  "cmexam": "CMExam",
  "mmlu-econonmics": "MMLU-Econonmics",
  "mmlu-economics": "MMLU-Econonmics",
  "shoppingmmlu": "ShoppingMMLU",
  "chineseecomqa": "ChineseEcomQA",
  "eckgbench": "ECKGBench",
};

const normalizedDatasetOptionLabels: Record<string, string> = {
  aa_lcr: "AA-LCR",
  aime25: "AIME25",
  aime26: "AIME26",
  arenahardv2: "Arena-Hard-v2",
  artifactbench: "ArtifactBench",
  beyondaime: "BeyondAIME",
  bfclv3: "BFCL-v3",
  browsecomp: "BrowseComp",
  browsecompzn: "BrowseComp-zn",
  chemistrysmoke: "Chemistry-Smoke",
  chineseccomqa: "ChineseEcomQA",
  chineseecomqa: "ChineseEcomQA",
  cmexam: "CMExam",
  creativewriting: "CreativeWriting",
  csimpleqa: "C-SimpleQA",
  discox: "Disco-X",
  eckgbench: "ECKGBench",
  fineval60: "Fineval6.0",
  globalpiqa: "Global-PIQA",
  gpqa: "GPQA",
  hmmtfeb26: "HMMT-Feb-26",
  hmmtnov25: "HMMT-Nov-25",
  hmtnov25: "HMT-Nov-25",
  ifeval: "IFEval",
  imoanswerbench: "IMO-AnswerBench",
  korbench: "KorBench",
  livecodebenchpro: "LiveCodeBench-Pro",
  livecodebenchv6: "LiveCodeBench-v6",
  longbench: "LongBench",
  mathsmoke: "Math-Smoke",
  mathsmoketest: "Math-Smoke",
  medmcqa: "MedMCQA",
  medqa: "MedQA",
  mmlueconomics: "MMLU-Econonmics",
  mmluecononmics: "MMLU-Econonmics",
  mmmlulite: "MMMLU-Lite",
  mrcrv2: "MRCR-v2",
  multichallenge: "MultiChallenge",
  multiple: "Multipl-E",
  multiswebench: "MultiSWEBench",
  physicsmoke: "Physics-Smoke",
  physicsmoketest: "Physics-Smoke",
  pinchbench: "PinchBench",
  pinchbnch: "PinchBench",
  repoqa: "RepoQA",
  ruler: "RULER",
  shoppingmmlu: "ShoppingMMLU",
  simpleqa: "SimpleQA",
  supergpqa: "SuperGPQA",
  supergpqamed: "SuperGPQA-Med",
  swebenchverified: "SWE-Bench-Verified",
  terminalbench: "TerminalBench",
  umath: "U-Math",
  writingbench: "WritingBench",
  化学: "Chemistry-Smoke",
  化学冒烟集: "Chemistry-Smoke",
  化学冒烟: "Chemistry-Smoke",
  数学: "Math-Smoke",
  数学冒烟集: "Math-Smoke",
  数学冒烟: "Math-Smoke",
  物理: "Physics-Smoke",
  物理冒烟集: "Physics-Smoke",
  物理冒烟: "Physics-Smoke",
};

function normalizeDatasetName(datasetName: string): string {
  return datasetName.trim().toLowerCase().replace(/[-_.\s]/g, "");
}

export function formatDatasetOptionLabel(datasetName: string): string {
  const lookupName = datasetName.trim();
  const configuredLabel = datasetOptionLabels[lookupName.toLowerCase()];

  if (configuredLabel) {
    return configuredLabel;
  }

  const normalizedName = normalizeDatasetName(lookupName);
  const normalizedLabel = normalizedDatasetOptionLabels[normalizedName];

  if (normalizedLabel) {
    return normalizedLabel;
  }

  if (normalizedName.startsWith("pinchbench")) {
    return "PinchBench";
  }

  if (normalizedName.startsWith("discox")) {
    return "Disco-X";
  }

  if (normalizedName.startsWith("mathsmoke") || normalizedName.startsWith("数学冒烟")) {
    return "Math-Smoke";
  }

  if (normalizedName === "数学") {
    return "Math-Smoke";
  }

  if (
    normalizedName.startsWith("physicsmoke") ||
    normalizedName.startsWith("physicssmoke") ||
    normalizedName.startsWith("物理冒烟")
  ) {
    return "Physics-Smoke";
  }

  if (normalizedName === "物理") {
    return "Physics-Smoke";
  }

  if (
    normalizedName.startsWith("chemistrysmoke") ||
    normalizedName.startsWith("chemsmoke") ||
    normalizedName.startsWith("化学冒烟")
  ) {
    return "Chemistry-Smoke";
  }

  if (normalizedName === "化学") {
    return "Chemistry-Smoke";
  }

  const firstCharacter = lookupName.charAt(0);

  if (firstCharacter >= "a" && firstCharacter <= "z") {
    return `${firstCharacter.toUpperCase()}${lookupName.slice(1)}`;
  }

  return lookupName;
}
