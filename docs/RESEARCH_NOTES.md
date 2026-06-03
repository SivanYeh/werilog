# Research Notes: LLM-based Verilog / RTL Generation

Reviewed: 2026-05-24

## Scope and Naming Check

The issue labels the two target papers as **RTLLM-2 (2025)** and **VeriGen-Next (2025)**, but the two PDFs and arXiv links in this folder point to different papers:

| Issue label | Provided link / local PDF | Actual paper title | Method name |
|---|---|---|---|
| RTLLM-2 (2025) | `2502.15832v1.pdf` / https://arxiv.org/abs/2502.15832 | DeepRTL: Bridging Verilog Understanding and Generation with a Unified Representation Model | DeepRTL |
| VeriGen-Next (2025) | `2511.13139v1.pdf` / https://arxiv.org/abs/2511.13139 | Think with Self-Decoupling and Self-Verification: Automated RTL Design with Backtrack-ToT | VeriBToT |

This note follows the **provided PDFs/arXiv links**. If the issue owner intended the actual RTLLM 2.0 paper, that is **OpenLLM-RTL** (`2503.15112`), whose RTLLM 2.0 benchmark repo is https://github.com/hkust-zhiyao/RTLLM.

## Issue Checklist

- [x] Summarized the two provided papers.
- [x] Identified data sources for training, fine-tuning, and evaluation.
- [x] Organized result metrics: Pass@k, syntax correctness, functional correctness, and verification setup.
- [x] Located official code/data links where available.
- [x] Compared the methods and extracted implications for VerilogAgent inference logic.

## At-a-Glance Comparison

| Dimension | DeepRTL | VeriBToT |
|---|---|---|
| Contribution type | Fine-tuned Verilog understanding + generation model | Inference-time reasoning framework |
| Core idea | Align Verilog code with multi-level natural-language descriptions | Generate RTL through hierarchical decomposition, local verification, and backtracking |
| Base models | CodeT5+-220m and CodeT5+-16b | ChatGPT-4, DeepSeek-Coder-V2, plus domain-specific baselines |
| Training data | New Verilog/NL instruction-tuning dataset | No new training dataset |
| Evaluation data | Verilog understanding benchmark + expanded RTLLM-style generation benchmark | RTLLM and VerilogEval-Human |
| Verification | `iverilog` syntax and unit-test checks | Self-generated/provided testbenches plus final EDA verification |
| Best use for VerilogAgent | Better context representation, retrieval, summarization, and future fine-tuning data | Better inference logic: decompose, verify, repair, and backtrack |
| Code status | Official repo available, but mostly data/benchmark assets | No official implementation repo found |

## 1. DeepRTL

- Paper: https://arxiv.org/abs/2502.15832
- Official repo: https://github.com/PeterLau61/DeepRTL
- Fine-tuning dataset: https://huggingface.co/datasets/liuyi2000/deeprtl_finetuning_dataset
- Useful training-script reference: https://github.com/salesforce/CodeT5

### Main Idea

DeepRTL argues that Verilog generation improves when the model also learns Verilog understanding. Instead of only mapping natural-language specifications to RTL, it trains a unified model for both directions:

- Verilog understanding: Verilog code -> concise natural-language functional description.
- Verilog generation: natural-language specification + module header -> Verilog RTL.

The model is based on CodeT5+ and uses curriculum learning so the model first learns local semantics, then block/module behavior, then high-level functional intent.

### Data Sources

DeepRTL builds a new aligned Verilog/NL dataset from two sources:

| Source | Details |
|---|---|
| Open-source Verilog | `.v` files scraped from GitHub using the keyword `Verilog`. Files are split into modules, deduplicated with MinHash/Jaccard similarity, and filtered if mostly comments or missing complete `module` / `endmodule` structure. Final count: **61,755 distinct modules**. |
| Proprietary Verilog | **213 purchased industrial IP modules**, annotated by professional hardware engineers. |

Annotation pipeline:

- Removes original comments to avoid training on stale or misleading comments.
- Uses a 2048-token budget aligned with CodeT5+ context length.
- Splits longer modules into manageable blocks when possible; blocks still over 2048 tokens are discarded.
- Uses GPT-4 with CoT prompts to create line-level comments, detailed specifications, and high-level functional descriptions.
- Uses GPT-4o-mini to filter line-level comments that depend on context not present in the current line.
- Uses professional hardware engineers for proprietary-code annotations.

Dataset statistics reported in the paper:

| Annotation level | Granularity | Count |
|---|---:|---:|
| Line | N/A | 434,697 |
| Block | High-level description | 892 |
| Block | Medium-detail description | 1,306 |
| Block | Detailed description | 894 |
| Module | High-level functional description | 59,448 |
| Module | Detailed specification | 59,503 |

Human annotation-quality check:

- High-level function annotations: **91%** accuracy.
- Detailed specifications: **88%** accuracy.
- Line-level annotations: **98%** accuracy.
- Direct annotation baseline without the CoT pipeline: **67%** accuracy.

### Methodology

DeepRTL fine-tunes CodeT5+ with instruction tuning and curriculum learning:

- Stage 1: line/block-level data before module-level data.
- Stage 2: detailed specifications before high-level functional descriptions.
- Stage 3: GPT-annotated data before human-annotated data when available.

The authors fine-tune DeepRTL-220m and DeepRTL-16b, modify the CodeT5+ instruction-tuning setup for a 2048-token input context, and run training with DeepSpeed on 8 x NVIDIA A800 80GB GPUs.

### Result Analysis

DeepRTL evaluates two capabilities.

**Verilog understanding**

Benchmark: 100 human-annotated Verilog modules with high-level functional descriptions cross-checked by hardware engineers.

Metrics:

- BLEU-4 and ROUGE-1/2/L for lexical overlap.
- Embedding similarity using `text-embedding-3-large`.
- GPT Score using GPT-4 as a semantic evaluator.
- Human evaluation.

Key understanding results:

| Model | BLEU-4 | ROUGE-L | Emb. Sim. | GPT Score |
|---|---:|---:|---:|---:|
| GPT-4 | 5.36 | 30.66 | 0.824 | 0.683 |
| o1-preview | 6.06 | 31.01 | 0.806 | 0.643 |
| DeepRTL-220m | 18.66 | 44.02 | **0.837** | **0.705** |
| DeepRTL-16b | **18.94** | **44.13** | 0.830 | 0.694 |

Human evaluation: DeepRTL-220m reaches **78%** accuracy, compared with **72%** for GPT-4 and **67%** for o1-preview.

**Verilog generation**

Benchmark: the paper uses the generation benchmark from Chang et al. 2024, described as an expansion of RTLLM across arithmetic, digital logic, and advanced hardware designs.

Metrics:

- Syntax correctness: whether generated Verilog compiles with `iverilog`.
- Functional correctness: whether generated Verilog passes unit tests.
- Success rate: average percentage of the five generated samples that pass.
- Pass@1 and Pass@5 for both syntax and function.

Summary generation results:

| Model | Syntax success | Function success | Syntax Pass@1 | Function Pass@1 | Syntax Pass@5 | Function Pass@5 |
|---|---:|---:|---:|---:|---:|---:|
| GPT-4 | 63.87% | 27.74% | 51.61% | 29.03% | 77.42% | 45.16% |
| o1-preview | **78.06%** | **38.06%** | **74.19%** | **35.48%** | **80.65%** | **51.61%** |
| DeepRTL-220m | **78.06%** | 36.13% | 70.97% | 32.26% | **80.65%** | 41.94% |
| DeepRTL-16b | 76.13% | **38.06%** | **74.19%** | **35.48%** | 77.42% | 38.71% |

Takeaway: DeepRTL is not universally better than o1-preview, but it is competitive while being much smaller and domain-specialized. It also significantly improves over GPT-4 on syntax correctness, functional Pass@1, and functional success rate.

### Code Availability

The official repo exists, but it mainly exposes:

- `README.md`
- `understanding_benchmark.json`
- Hugging Face dataset links

It does **not** appear to release a complete end-to-end training pipeline. For reproduction, the closest public implementation path is to combine the released dataset with the Salesforce CodeT5+ instruction-tuning scripts.

## 2. VeriBToT / Backtrack-ToT

- Paper: https://arxiv.org/abs/2511.13139
- DATE 2026 paper page/PDF: https://www.cse.cuhk.edu.hk/~byu/papers/C320-DATE2026-VeriBToT.pdf
- Official implementation repo: **not found** in the paper, arXiv page, DATE materials, or targeted web/GitHub searches.

### Main Idea

VeriBToT is an inference-time reasoning framework, not a new fine-tuned model. It argues that ordinary Chain-of-Thought is poorly matched to RTL design because hardware modules are parallel, hierarchical, timing-sensitive, and coupled through signals.

The framework makes the LLM behave more like an RTL engineer:

1. Decompose a complex design into submodules.
2. Generate RTL and testbench code for each node.
3. Verify intermediate modules.
4. Repair failed leaf modules.
5. Backtrack when the decomposition itself is wrong.
6. Aggregate verified modules into the final design.

### Data Sources and Benchmarks

VeriBToT does **not** introduce a new training or fine-tuning dataset.

Evaluation uses two NL2V benchmarks:

| Benchmark | Used for | Notes |
|---|---|---|
| RTLLM | Verilog generation evaluation | Used for full benchmark and hard-case analysis. |
| VerilogEval-Human | Verilog generation evaluation | Used because it supports natural-language-to-Verilog tasks with enough flexibility for modular decomposition. |

The paper explicitly excludes VerilogEval-Machine because it focuses on component connections and truth tables, which gives less room for modular decomposition.

### Methodology

VeriBToT combines:

- Top-down design: recursively partition the target design into coherent modules.
- Design for Verification (DFV): keep each intermediate module verifiable.
- Backtrack Tree of Thought: explore and revise the decomposition when verification fails.

The five operators are:

| Operator | Purpose |
|---|---|
| Branch Generator | Decomposes a complex node into submodules. |
| Node Evaluator | Checks whether the current RTL passes its testbench/verification context. |
| Node Rethinker | Rewrites a failed bottom-level module. |
| Backtrack Executor | Reverses an invalid module split and retries a better decomposition. |
| Code Aggregator | Combines verified modules into final Verilog. |

Each reasoning node contains natural-language design intent, RTL Verilog, and testbench Verilog. The traversal is depth-first and verification-driven.

### Result Analysis

Evaluated models:

- ChatGPT-4
- DeepSeek-Coder-V2
- RTLCoder and Thakur as domain-specific fine-tuned baselines under IO prompting

Metrics:

- Functional Pass@1 and Pass@5 on full benchmarks.
- Syntax correctness and functional correctness for hard cases, reported as `#Pass@5`.
- Token consumption.

Full-benchmark functional results:

| Paradigm | VerilogEval-Human DeepSeek Pass@1 / Pass@5 | VerilogEval-Human ChatGPT-4 Pass@1 / Pass@5 | RTLLM DeepSeek Pass@1 / Pass@5 | RTLLM ChatGPT-4 Pass@1 / Pass@5 |
|---|---:|---:|---:|---:|
| IO | 0.27 / 0.36 | 0.34 / 0.45 | 0.34 / 0.46 | 0.42 / 0.56 |
| CoT | 0.29 / 0.37 | 0.33 / 0.47 | 0.30 / 0.40 | 0.38 / 0.50 |
| CoT-SC | 0.27 / 0.37 | 0.38 / 0.50 | 0.24 / 0.38 | 0.40 / 0.46 |
| ToT | 0.26 / 0.39 | 0.35 / 0.48 | 0.28 / 0.48 | 0.38 / 0.48 |
| VeriBToT | **0.32 / 0.44** | **0.43 / 0.58** | **0.42 / 0.56** | **0.48 / 0.62** |
| VeriBToT- | 0.29 / 0.36 | 0.36 / 0.52 | 0.26 / 0.44 | 0.41 / 0.57 |

The `VeriBToT-` ablation removes testbench-generation/self-validation prompts. Its drop from full VeriBToT indicates that local testbench-based self-verification is a major contributor, not just extra reasoning tokens.

Hard-case analysis:

- The paper reports syntax/function `#Pass@5` for difficult RTLLM and VerilogEval-Human cases.
- VeriBToT improves both syntax and functional correctness against IO, CoT, CoT-SC, and ToT in many hard cases.
- Token usage rises because the framework carries module descriptions and testbenches, but the paper reports that generated-context tokens remain comparable to CoT-SC/ToT and that backtracking helps avoid unbounded reasoning cost.

### Code Availability

No official VeriBToT repository was found. For internal experimentation, the paper is implementable as an agent workflow around the five operators:

- Prompt templates for branch/evaluate/rethink/backtrack/aggregate.
- A state tree storing node-level spec, RTL, testbench, verification status, and parent/child links.
- Tool calls to `iverilog`, Verilator, Verible, or the existing VerilogAgent simulator hooks.
- A retry/backtrack policy based on syntax errors, unit-test failures, and model-judged decomposition quality.

## Dataset and Benchmark Comparison

| Question | DeepRTL | VeriBToT |
|---|---|---|
| Does it train/fine-tune a model? | Yes. Fine-tunes CodeT5+ on a new Verilog/NL instruction dataset. | No. It changes inference-time reasoning. |
| What is the main data strategy? | Large paired Verilog/NL data with line, block, and module descriptions. | Uses benchmark testbenches and generated intermediate testbenches as verification signals. |
| What data quality controls matter? | Deduplication, comment stripping, context-length filtering, GPT-4o-mini line-comment filtering, human annotation checks. | Intermediate verification and backtracking prevent bad decompositions from propagating. |
| What benchmarks matter? | Verilog understanding benchmark and expanded RTLLM-style generation benchmark. | RTLLM and VerilogEval-Human. |
| What should VerilogAgent borrow first? | Better semantic context and summarization of surrounding RTL. | Hierarchical generation plus compile/test/repair loops. |

## Implications for VerilogAgent

1. Add an "understand before complete" step for non-trivial completions. Summarize nearby modules, ports, always blocks, FSM states, and signal roles before asking the model to complete code.

2. Use hierarchical completion for complex requests. If a completion touches multiple always blocks, FSM transitions, pipeline stages, or wide arithmetic, first ask for a small design plan and signal contract, then generate code.

3. Make verification part of inference. Rank completions by parse/lint/compile results first, then by functional tests when a testbench exists. For multi-module requests, verify submodules before aggregating.

4. Add bounded repair and backtracking. On syntax failure, repair the current candidate. On repeated functional failure, revisit the decomposition or signal contract instead of only editing local lines.

5. Track benchmark-style metrics internally. For autocomplete experiments, log syntax pass rate, functional pass rate, Pass@1, Pass@5, `#Pass@5`, and token cost on RTLLM/VerilogEval-Human-like tasks.

6. Improve future training data with DeepRTL-style filters. For any GitHub or internal RTL corpus, deduplicate modules, remove misleading comments, filter context-too-large modules, and prefer verified instruction-code pairs.

## Working Links

- DeepRTL arXiv: https://arxiv.org/abs/2502.15832
- DeepRTL official repo: https://github.com/PeterLau61/DeepRTL
- DeepRTL fine-tuning dataset: https://huggingface.co/datasets/liuyi2000/deeprtl_finetuning_dataset
- Salesforce CodeT5 reference implementation: https://github.com/salesforce/CodeT5
- VeriBToT arXiv: https://arxiv.org/abs/2511.13139
- VeriBToT DATE 2026 PDF: https://www.cse.cuhk.edu.hk/~byu/papers/C320-DATE2026-VeriBToT.pdf
- Actual RTLLM 2.0 / OpenLLM-RTL paper, if the issue label was intended literally: https://arxiv.org/abs/2503.15112
- RTLLM benchmark repo: https://github.com/hkust-zhiyao/RTLLM
