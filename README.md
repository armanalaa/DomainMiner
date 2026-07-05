# DomainMiner

**Automatic data mesh domain discovery from data lake CSV tables.**  
DomainMiner takes a collection of CSV files and groups them into business domains using column similarity, table graphs, and Louvain clustering, with LLM-generated domain labels.

---

## Table of Contents

1. [How It Works](#how-it-works)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Folder Structure](#folder-structure)
5. [All Scripts Reference](#all-scripts-reference)
6. [Step-by-Step: Running the Pipeline](#step-by-step-running-the-pipeline)
   - [Step 0 â€” Prepare your dataset](#step-0--prepare-your-dataset)
   - [Step 1 â€” Extract schema](#step-1--extract-schema)
   - [Step 2 â€” Crawl documentation](#step-2--crawl-documentation)
   - [Step 3 â€” Extract knowledge](#step-3--extract-knowledge)
   - [Step 4 â€” Tune parameters](#step-4--tune-parameters)
   - [Step 5 â€” Rebuild results](#step-5--rebuild-results)
   - [Step 6 â€” Retry failed runs](#step-6--retry-failed-runs)
   - [Step 7 â€” Pick the best result](#step-7--pick-the-best-result)
7. [Running a Single Configuration](#running-a-single-configuration)
8. [Parameter Reference](#parameter-reference)
9. [Internal Pipeline Scripts â€” Parameters & Examples](#internal-pipeline-scripts--parameters--examples)
10. [Analysis & Reporting Utilities](#analysis--reporting-utilities)
11. [Validated Datasets](#validated-datasets)

---

## How It Works

The pipeline implements the 5-stage methodology described in the paper *Data Mesh Domain Discovery* (Arman et al., ICSOC 2026). Internal script numbering follows the order scripts run in, not the paper's stage numbers directly â€” the mapping is shown below.

| Paper Stage | Description (paper Â§) | Script(s) | What it does |
|---|---|---|---|
| **(1) Concept Analysis** | Â§4.1 | `knowledge_concept_embedding.py` (concept extraction half) | Extracts the business workflow document $K_{wf}$ from schema + raw knowledge sources, then extracts the mutually exclusive concept set $K = \{k_1, \dots, k_p\}$ and embeds each concept $e(k) \in \mathbb{R}^d$ |
| **(2) Column Analysis** | Â§4.2 | `knowledge_concept_embedding.py` (column profiling half), `p_stat_name_sem.py` | Computes the statistical profile $\Phi_{stat}(c_i)$ (17 z-scored meta-features), the semantic embedding $e(c_i)$, and the concept-affinity matrix $\Phi \in [0,1]^{|C|\times|K|}$ via $\phi(c_i,k) = \cos(e(c_i), e(k))$ |
| **(3) Column-Level Similarity Computation** | Â§4.3 | `sim_attr_weights.py`, `column_graph.py` | Computes $P_{stat}$, $P_{name}$ (Levenshtein), $P_{sem}$ (cosine on $\phi$-rows) for every column pair; derives variance-based weights $w_1, w_2, w_3$; combines into $Sim_{col}$; builds the column graph $G_C$ thresholded at $\theta_C$ |
| **(4) Table-Level Similarity Computation** | Â§4.4 | `table_similarity.py` | Greedily matches columns between every table pair, computes coverage ratio $CR$ and $Sim_{table} = raw\_sim \times CR$; builds the weighted table graph $G_T$ thresholded at $\theta_T$ |
| **(5) Domain Realization** | Â§4.5 | `domain_discovery.py` | Runs Louvain clustering on $G_T$ at resolution $\gamma$ to maximize modularity $Q$; computes mean concept-affinity $\bar\phi(D_i,k)$ per domain; LLM assigns each domain a human-readable label $\ell_i$ |

> **Naming note:** in code and CLI flags, $\theta_C$ (paper) = `theta_a` (script), and $\theta_T$ (paper) = `theta_t` (script). The Louvain resolution $\gamma$ (paper) = `resolution` (script).

---

## Requirements

- Python 3.9 or higher
- [Ollama](https://ollama.com) installed and running locally
- [Playwright](https://playwright.dev/python/) for `crawl_to_pdf.py`
- Git

### Python packages

```bash
pip install pandas numpy scikit-learn sentence-transformers python-docx \
            networkx python-louvain requests openpyxl tqdm playwright
playwright install chromium
```

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/armanalaa/DomainMiner.git
cd DomainMiner

# 2. Pull the base LLM
ollama pull mistral

# 3. Create the custom model with the extended context window
ollama create mistral-ctx4k -f Modelfile

# 4. Verify the model is available
ollama list
# You should see: mistral-ctx4k
```

---

## Folder Structure

Place your dataset inside the project root. Each dataset follows this layout:

```
DomainMiner/
â”‚
â”œâ”€â”€ extract_schema.py           â† Step 1: profile columns, build schema.json
â”œâ”€â”€ extract_knowledge.py        â† Step 3: extract knowledge from PDFs â†’ knowledge.docx
â”œâ”€â”€ run_pipeline.py             â† Run a single parameter combination
â”œâ”€â”€ tune_params.py              â† Run all 27 parameter combinations
â”œâ”€â”€ run_failed.py               â† Retry failed runs automatically
â”œâ”€â”€ build_tune_params_results.pyâ† Rebuild results xlsx from existing run folders
â”œâ”€â”€ pipeline_utils.py           â† Shared utilities (logging, cleanup, run tags)
â”œâ”€â”€ knowledge_concept_embedding.py
â”œâ”€â”€ p_stat_name_sem.py
â”œâ”€â”€ sim_attr_weights.py
â”œâ”€â”€ column_graph.py
â”œâ”€â”€ table_similarity.py
â”œâ”€â”€ domain_discovery.py
â”œâ”€â”€ Modelfile                   â† Ollama model configuration (4096 context window)
â”‚
â”œâ”€â”€ tools/
â”‚   â”œâ”€â”€ crawl_to_pdf.py         â† Step 2: crawl documentation websites â†’ knowledge/ PDFs
â”‚   â””â”€â”€ list_best_configs.py    â† Cross-dataset best-config summary (auto-discovers datasets)
â”‚   â”œâ”€â”€ list_concepts.py         â† List concepts extracted for one dataset (step1_concepts.json)
â”œâ”€â”€ tools/list_extracted_concepts.py  â† Identical to tools/list_concepts.py (legacy alias)
â”‚   â”œâ”€â”€ list_derived_weights.py â† Cross-dataset summary of variance-based similarity weights
â”‚   â”œâ”€â”€ sum_row_col.py           â† Quick table/column totals for dataset CSV files
â”‚
â””â”€â”€ <YourDataset>/
    â”œâ”€â”€ csv/                    â† put all your CSV files here
    â”œâ”€â”€ knowledge/              â† put documentation PDFs here
    â”œâ”€â”€ schema.json             â† generated by extract_schema.py
    â”œâ”€â”€ knowledge.docx          â† generated by extract_knowledge.py
    â”œâ”€â”€ logs/                   â† created automatically
    â””â”€â”€ ccm_output/             â† all results written here
        â”œâ”€â”€ tA0.65_tT0.70_r1.2/
        â”‚   â”œâ”€â”€ step3_sim_attr_report.txt
        â”‚   â”œâ”€â”€ step4_report.txt
        â”‚   â””â”€â”€ step5_report.txt
        â”œâ”€â”€ derived_weights.csv
        â”œâ”€â”€ step1_concepts.json
        â”œâ”€â”€ tune_params_results.xlsx
        â””â”€â”€ tune_params_summary.txt
```

---

## All Scripts Reference

### Core pipeline scripts

| Script | Purpose | Run from |
|---|---|---|
| `extract_schema.py` | Profiles every CSV column and builds `schema.json` | DomainMiner root |
| `extract_knowledge.py` | Reads PDFs in `knowledge/` and writes `knowledge.docx` | DomainMiner root |
| `tools/crawl_to_pdf.py` | Crawls a documentation website and saves pages as PDFs | DomainMiner root |
| `run_pipeline.py` | Runs the full CCM pipeline for one parameter combination | DomainMiner root |
| `tune_params.py` | Runs all 27 combinations of `theta_a Ã— theta_t Ã— resolution` | DomainMiner root |
| `run_failed.py` | Scans for failed runs and retries them automatically | DomainMiner root |
| `build_tune_params_results.py` | Rebuilds `tune_params_results.xlsx` from existing run folders | DomainMiner root |
| `pipeline_utils.py` | Shared helpers: logging, cleanup, run tag generation | (imported, not run directly) |

### Internal pipeline step scripts

These are called automatically by `run_pipeline.py` â€” you do not normally run them directly. Stage names follow the paper (Â§4.1â€“Â§4.5); see [Internal Pipeline Scripts â€” Parameters & Examples](#internal-pipeline-scripts--parameters--examples) for full CLI reference and standalone usage.

| Script | Paper Stage | What it does |
|---|---|---|
| `knowledge_concept_embedding.py` | (1) Concept Analysis + (2) Column Analysis | Extracts $K_{wf}$ and concept set $K$, embeds concepts, profiles columns ($\Phi_{stat}$, $e(c_i)$) |
| `p_stat_name_sem.py` | (2) Column Analysis | Computes the concept-affinity matrix $\Phi$ and pairwise $P_{stat}$, $P_{name}$, $P_{sem}$ |
| `sim_attr_weights.py` | (3) Column-Level Similarity | Derives variance-based weights $w_1,w_2,w_3$ and computes $Sim_{col}$ |
| `column_graph.py` | (3) Column-Level Similarity | Builds column similarity graph $G_C$ above $\theta_C$ (`theta_a`) |
| `table_similarity.py` | (4) Table-Level Similarity | Greedy column matching, coverage ratio, builds table graph $G_T$ above $\theta_T$ (`theta_t`) |
| `domain_discovery.py` | (5) Domain Realization | Louvain clustering at resolution $\gamma$ + LLM domain labeling |

### Analysis & reporting scripts

Run these from the DomainMiner root **after** one or more datasets have completed `tune_params.py`. They never modify pipeline outputs â€” read-only summarizers. See [Analysis & Reporting Utilities](#analysis--reporting-utilities) for full usage.

| Script | Purpose | Scope |
|---|---|---|
| `tools/list_best_configs.py` | Cross-dataset summary: best Q config + domain names per dataset, written to one Excel file | All datasets (auto-discovered) |
| `tools/list_concepts.py` | Lists extracted business concepts (`step1_concepts.json`) for one dataset | Single dataset |
| `tools/list_extracted_concepts.py` | Identical to `tools/list_concepts.py` â€” legacy alias kept for backward compatibility | Single dataset |
| `tools/list_derived_weights.py` | Cross-dataset summary of variance-based similarity weights ($w_1$/$w_2$/$w_3$) | All datasets (hardcoded list â€” see note below) |
| `tools/sum_row_col.py` | Prints total tables and total columns for dataset CSV files | One or all datasets |

---

## Step-by-Step: Running the Pipeline

Replace `<Dataset>` with your dataset folder name and `<DBName>` with a short name for your database (e.g. `TPC-H`, `Northwind`).

> **Note on numbering:** the "Step 0â€“7" workflow below is operational (preparing data, crawling, tuning, retrying) and does not map one-to-one onto the paper's 5 methodology stages. Steps 1 and 3 correspond to Stage (1)/(2) preprocessing; Step 4 (`tune_params.py`) runs Stages (2)â€“(5) once per parameter combination. See [How It Works](#how-it-works) for the paper-stage mapping, and [Internal Pipeline Scripts](#internal-pipeline-scripts--parameters--examples) for the scripts that implement each paper stage directly.

---

### Step 0 â€” Prepare your dataset

1. Create a folder with your dataset name inside the project root.
2. Put all CSV files inside `<Dataset>/csv/`.
3. Remove pure lookup tables (very few rows, only code+label columns â€” e.g. a `region` table with 5 rows and 2 columns).

```
DomainMiner/
â””â”€â”€ MyDataset/
    â””â”€â”€ csv/
        â”œâ”€â”€ orders.csv
        â”œâ”€â”€ customer.csv
        â””â”€â”€ ...
```

---

### Step 1 â€” Extract schema

Profiles every column in every CSV and builds `schema.json`.

```bash
python extract_schema.py \
  --dataset_dir <Dataset> \
  --csv_dir csv \
  --output schema.json \
  --database <DBName> \
  --model mistral-ctx4k \
  --ollama_timeout 600
```

**Output:** `<Dataset>/schema.json`

---

### Step 2 â€” Crawl documentation

Crawls a documentation website and saves each page as a PDF into `<Dataset>/knowledge/`.
Run multiple times with different URLs to build a rich knowledge base.

```bash
# Run from the DomainMiner root
python tools/crawl_to_pdf.py \
  --dataset_dir <Dataset> \
  --url https://en.wikipedia.org/wiki/Your_Topic \
  --depth 1
```

**Arguments:**

| Argument | Default | Description |
|---|---|---|
| `--dataset_dir` | required | Dataset subfolder name (e.g. `Northwind`) |
| `--url` | required | Root URL to start crawling from |
| `--depth` | `2` | Maximum crawl depth |
| `--delay` | `1.5` | Seconds between page loads |

**Output:** PDFs saved to `<Dataset>/knowledge/`

> **Tip:** Wikipedia pages always render cleanly. Avoid JavaScript-heavy sites (React SPAs) â€” they often produce empty PDFs.

---

### Step 3 â€” Extract knowledge

Reads all PDFs in `<Dataset>/knowledge/` and uses the LLM to extract business descriptions. Writes `knowledge.docx`.

```bash
python extract_knowledge.py \
  --dataset_dir <Dataset> \
  --database <DBName> \
  --schema schema.json \
  --pdf_dir knowledge/ \
  --backend ollama \
  --model mistral-ctx4k \
  --schema_max_chars 1000 \
  --source_max_chars 5000 \
  --max_tokens 2048 \
  --pdf_chunk_size 5000 \
  --num_ctx 4096 \
  --timeout 1800 \
  --output knowledge.docx \
  --log_dir logs
```

**Output:** `<Dataset>/knowledge.docx`

> This step can take 10â€“30 minutes depending on PDF size and number of tables.

---

### Step 4 â€” Tune parameters

Runs all 27 combinations of `theta_a`, `theta_t`, and `resolution` and scores each with modularity Q.

```bash
python tune_params.py \
  --dataset_dir <Dataset> \
  --knowledge knowledge.docx \
  --theta_a 0.60 0.65 0.70 \
  --theta_t 0.65 0.70 0.75 \
  --resolution 1.2 1.5 2.0
```

**Output:**
- `<Dataset>/ccm_output/tune_params_results.xlsx` â€” color-coded Excel table
- `<Dataset>/ccm_output/tune_params_summary.txt` â€” plain text table sorted by Q

---

### Step 5 â€” Rebuild results

If any runs completed after the xlsx was last generated, or if you suspect results are stale, rebuild from the existing run folders:

```bash
python build_tune_params_results.py --dataset_dir <Dataset>
```

This scans all `tA*_tT*_r*` subfolders in `ccm_output/`, reads each `step5_report.txt`, and writes a fresh `tune_params_results.xlsx`. No pipeline re-runs needed.

> Run this after any patch to the pipeline (e.g. fixing the modularity regex) to update results without re-running all 27 combinations.

---

### Step 6 â€” Retry failed runs

If any runs show as FAILED in the results xlsx, retry them automatically:

```bash
python run_failed.py \
  --dataset_dir <Dataset> \
  --max_retries 2
```

**Arguments:**

| Argument | Default | Description |
|---|---|---|
| `--dataset_dir` | required | Dataset folder name |
| `--max_retries` | `2` | Retry attempts per failed run |
| `--no_llm` | off | Skip Ollama domain labeling (faster) |
| `--model` | `mistral:latest` | Ollama model name |

The script rebuilds the results xlsx automatically after each successful retry.

> **Note:** `run_failed.py` re-runs the full pipeline (`run_pipeline.py --clean`) for each failed combination. If the failure was only in the Q metric parsing (e.g. negative Q values), use `build_tune_params_results.py` instead â€” it's much faster.

---

### Step 7 â€” Pick the best result

Open `ccm_output/tune_params_results.xlsx`.

- **Valid result:** Q â‰¥ 0.3 (Newman & Girvan, 2004)
- Pick the run with the **highest Q** and the most coherent domain labels
- The best run's output is in `ccm_output/tA<x>_tT<y>_r<z>/step5_report.txt`

> **Small schemas (â‰¤ 10 tables):** Q values are inherently low due to graph size constraints. Evaluate domain quality qualitatively through label coherence rather than relying solely on Q.

---

## Running a Single Configuration

To run one specific parameter combination without tuning:

```bash
python run_pipeline.py \
  --dataset_dir <Dataset> \
  --knowledge knowledge.docx \
  --theta_a 0.65 \
  --theta_t 0.70 \
  --resolution 1.2
```

To re-run from a specific step (skipping earlier steps):

```bash
python run_pipeline.py \
  --dataset_dir <Dataset> \
  --knowledge knowledge.docx \
  --theta_a 0.65 \
  --theta_t 0.70 \
  --resolution 1.2 \
  --start_from step5
```

**Valid `--start_from` values** (must match exactly):

| Value | Paper stage | What it (re)runs |
|---|---|---|
| `step12` | (1) Concept Analysis + (2) Column Analysis | Knowledge extraction + column profiling |
| `step3a` | (3) Column-Level Similarity | $P_{stat}$, $P_{name}$, $P_{sem}$ computation |
| `step3b` | (3) Column-Level Similarity | Derive weights $w_1, w_2, w_3$ |
| `step3c` | (3) Column-Level Similarity | $Sim_{col}$ + column graph $G_C$ |
| `step4` | (4) Table-Level Similarity | Table similarity + table graph $G_T$ |
| `step5` | (5) Domain Realization | Louvain clustering + LLM domain labeling |

---

## Parameter Reference

| Parameter | Values tested | Effect |
|---|---|---|
| `theta_a` | 0.60, 0.65, 0.70 | Column similarity threshold $\theta_C$ â€” higher = fewer column edges |
| `theta_t` | 0.65, 0.70, 0.75 | Table similarity threshold $\theta_T$ â€” higher = fewer table edges |
| `resolution` | 1.2, 1.5, 2.0 | Louvain resolution $\gamma$ â€” higher = more, smaller domains |

---

## Internal Pipeline Scripts â€” Parameters & Examples

These are normally invoked automatically by `run_pipeline.py`, but each accepts `--dataset_dir` and can be run standalone â€” useful for debugging a single stage or resuming after a manual fix, without using `--start_from`. All commands below are run from the DomainMiner root.

### `knowledge_concept_embedding.py` â€” Stage (1) Concept Analysis + Stage (2) Column Analysis

Extracts $K_{wf}$ and the concept set $K$ from the schema and `knowledge.docx`, embeds each concept $e(k)$, and profiles every column ($\Phi_{stat}$, $e(c_i)$).

| Argument | Default | Description |
|---|---|---|
| `--dataset_dir` | none | Dataset subfolder (e.g. `Mondial`) |
| `--schema` | `schema.json` | Schema JSON file |
| `--knowledge` | none | Path to $K_{raw}$ file (`.txt` or `.docx`) |
| `--out` | `ccm_output` | Output directory |
| `--embed_model` | `sentence-transformers/all-mpnet-base-v2` | Sentence embedding model (768-dim) |
| `--sample_size` | 5 | Max sample values per column |
| `--llm_backend` | `ollama` | `ollama` or `huggingface` |
| `--ollama_model` | `mistral-ctx4k` | Ollama model for $K_{wf}$/concept extraction |
| `--num_ctx` | 4096 | Ollama context window |
| `--temperature` | 0 | LLM temperature |

```bash
python knowledge_concept_embedding.py \
  --dataset_dir Mondial \
  --schema schema.json \
  --knowledge knowledge.docx \
  --embed_model sentence-transformers/all-mpnet-base-v2 \
  --ollama_model mistral-ctx4k \
  --num_ctx 4096
```

**Output:** `ccm_output/step1_concepts.json`, `ccm_output/step2_column_profiles.json`

### `p_stat_name_sem.py` â€” Stage (2) Column Analysis

Computes the concept-affinity matrix $\Phi$ (Eq. 5) and the three pairwise proximity measures $P_{stat}$ (Eq. 6), $P_{name}$ (Eq. 7), $P_{sem}$ (Eq. 8) for every column pair.

| Argument | Default | Description |
|---|---|---|
| `--dataset_dir` | none | Dataset subfolder |
| `--input-dir` | `ccm_output` | Directory containing Step 1+2 output |
| `--out-dir` | `ccm_output` | Output directory |

```bash
python p_stat_name_sem.py --dataset_dir Mondial
```

**Output:** `ccm_output/phi_matrix.csv`, `ccm_output/step3_proximity_long.csv`

### `sim_attr_weights.py` â€” Stage (3) Column-Level Similarity (weights)

Derives the variance-based weights $w_1, w_2, w_3$ (Eq. 11) from the proximity signals computed in the previous step.

| Argument | Default | Description |
|---|---|---|
| `--dataset_dir` | none | Dataset subfolder |
| `--input_dir` | `ccm_output` | Directory containing `step3_proximity_long.csv` |
| `--out_dir` | `ccm_output` | Output directory for `derived_weights.*` |

```bash
python sim_attr_weights.py --dataset_dir Mondial
```

**Output:** `ccm_output/derived_weights.csv` (see `tools/list_derived_weights.py` to inspect across datasets)

### `column_graph.py` â€” Stage (3) Column-Level Similarity (graph)

Combines $P_{stat}$, $P_{name}$, $P_{sem}$ into $Sim_{col}$ (Eq. 9) using the derived weights, and builds the column similarity graph $G_C$ thresholded at $\theta_C$ (`--theta`).

| Argument | Default | Description |
|---|---|---|
| `--dataset_dir` | none | Dataset subfolder |
| `--input-dir` | `ccm_output` | Directory with proximity + weights CSVs |
| `--out-dir` | `ccm_output` | Output directory |
| `--theta` | 0.60 | Column edge threshold $\theta_C$ |
| `--w1`, `--w2`, `--w3` | none (read from `derived_weights.csv`) | Manually override weights instead of using derived values |

```bash
python column_graph.py --dataset_dir Mondial --theta 0.65
```

**Output:** `ccm_output/step3_graph_edges.csv` (column graph $G_C$)

### `table_similarity.py` â€” Stage (4) Table-Level Similarity

Greedily matches columns between every table pair, computes the coverage ratio $CR$ (Eq. 13) and $Sim_{table}$ (Eq. 14), and builds the table graph $G_T$ thresholded at $\theta_T$ (`--theta_t`).

| Argument | Default | Description |
|---|---|---|
| `--dataset_dir` | none | Dataset subfolder |
| `--input_dir` | `ccm_output` | Directory with `step3_Sim_attr_long.csv` |
| `--schema` | `schema.json` | Path to schema.json |
| `--out_dir` | `ccm_output` | Output directory |
| `--theta_t` | 0.60 | Table similarity threshold $\theta_T$ |

```bash
python table_similarity.py --dataset_dir Mondial --theta_t 0.75
```

**Output:** `ccm_output/step4_graph_edges.csv` (table graph $G_T$)

### `domain_discovery.py` â€” Stage (5) Domain Realization

Runs Louvain clustering on $G_T$ at resolution $\gamma$ (`--resolution`) maximizing modularity $Q$ (Eq. 16), computes the mean concept-affinity $\bar\phi(D_i,k)$ per domain (Eq. 17), and uses the LLM to assign each domain a human-readable label $\ell_i$.

| Argument | Default | Description |
|---|---|---|
| `--dataset_dir` | none | Dataset subfolder |
| `--input_dir` | `ccm_output` | Directory with `step4_graph_edges.csv` |
| `--concepts` | `ccm_output/step1_concepts.json` | Path to concept set $K$ |
| `--profiles` | `ccm_output/step2_column_profiles.json` | Path to column profiles |
| `--phi_matrix` | `ccm_output/phi_matrix.csv` | Path to concept-affinity matrix $\Phi$ |
| `--schema` | `ccm_output/schema.json` | Path to schema.json |
| `--out_dir` | `ccm_output` | Output directory |
| `--resolution` | 1.0 | Louvain resolution $\gamma$ |
| `--random_state` | 42 | Louvain random seed (for reproducibility) |
| `--theta_t` | 0.60 | $\theta_T$ value used in Step 4 (report only) |
| `--no_llm` | off | Skip LLM â€” use $\phi$-based fallback labels only |
| `--model` | `mistral-ctx4k` | Ollama model for domain labeling |

```bash
python domain_discovery.py \
  --dataset_dir Mondial \
  --resolution 1.0 \
  --theta_t 0.75 \
  --model mistral-ctx4k
```

**Output:** `ccm_output/step5_domains.json` (domain partition $D^*$ + labels $L^*$), `ccm_output/step5_table_domain.csv`, `ccm_output/step5_column_domain.csv`, `ccm_output/step5_report.txt` (includes the modularity $Q$ score)

> **In practice:** running the five internal scripts standalone, in order, for one parameter combination is equivalent to a single `run_pipeline.py` call (see [Running a Single Configuration](#running-a-single-configuration)). Use the standalone form only when debugging one stage or re-deriving weights/graphs without LLM calls.

---

## Analysis & Reporting Utilities

These scripts are read-only summarizers, run from the DomainMiner root after `tune_params.py` has completed for one or more datasets. None of them modify pipeline outputs.

### `tools/list_best_configs.py` â€” cross-dataset best-config summary

Scans the project root for every dataset folder containing a completed `ccm_output/tune_params_results.xlsx`, reads the highest-Q row from each, and writes a single combined Excel report (`results/best_configs_summary.xlsx`) sorted by Q descending. Dataset discovery is automatic â€” any new dataset folder with completed tuning results is picked up without editing the script.

The workbook also includes a `Q_gt_0.3 by Ratio` sheet listing every configuration with `Q > 0.3` for each dataset, ranked by decreasing `Tables/Domain` ratio. It includes the same table-count checks printed in the console and explicit `none` rows for datasets without a valid configuration. The final columns place `Q`, `Tables`, `Domains`, `Single-table Domains`, and `Tables/Domain` side by side for quick comparison.

```bash
# Auto-discover every dataset in the project root
python tools/list_best_configs.py

# Restrict to specific datasets
python tools/list_best_configs.py --datasets Sakila Mondial Chinook

# Custom output path
python tools/list_best_configs.py --output results/best_configs.xlsx
```

**Output columns:** theta_A, theta_T, Resolution, Run Tag, Total Tables, Total Columns, CSV Tables, Domain Table Sum, Table Count Check, Tables/Edges in $G_T$, Domains, single-table domain count, **Tables/Domain ratio**, Q, Status, Time, and the full list of discovered domain names for the best run.

The console output also prints two extra rankings beyond the standard Q-descending list:
- **Tables/Domain ratio, ascending** â€” finer-grained domain separation first
- **Tables/Domain ratio, descending, restricted to Q > 0.3** â€” useful for picking which valid datasets produce the coarsest vs. finest domain partitions

### `tools/list_concepts.py` / `tools/list_extracted_concepts.py` â€” inspect extracted concepts

Lists every business concept extracted in Stage (1) Concept Analysis (`ccm_output/step1_concepts.json`) for a single dataset. The two scripts are identical; `tools/list_extracted_concepts.py` is kept as a backward-compatible alias.

```bash
python tools/list_concepts.py -dataset_dir Mondial
```

### `tools/list_derived_weights.py` â€” cross-dataset similarity weight summary

Collects `ccm_output/derived_weights.csv` from every dataset and writes `derived_weights_summary.xlsx`, showing the variance-based weights ($w_1$ = $P_{stat}$, $w_2$ = $P_{name}$, $w_3$ = $P_{sem}$) derived in Stage (3) Column-Level Similarity (Eq. 11), plus which signal dominates per dataset.

```bash
python tools/list_derived_weights.py
python tools/list_derived_weights.py --datasets Sakila Northwind Mondial
```

> **Note:** unlike `tools/list_best_configs.py`, this script still uses a hardcoded dataset list (`KNOWN_DATASETS`) rather than auto-discovery. Add new dataset names to that list, or pass `--datasets` explicitly, when including datasets added after this script was last edited.

### `tools/sum_row_col.py` â€” dataset table/column totals

Prints only the total number of tables and total number of columns for each dataset's CSV tables. With no dataset argument, it summarizes every dataset folder containing CSV files.

```bash
python tools/sum_row_col.py
python tools/sum_row_col.py Mondial
python tools/sum_row_col.py Mondial Sakila
```

The same concise results printed on screen are written to `results/row_col_totals.xlsx` by default. Use `--output` to choose a different workbook path.

---
**Tables/Domain ratio** = Total Tables Ã· Domains for the best-Q configuration. Lower values indicate finer-grained domain separation (e.g. eicu at 1.18); higher values indicate coarser clustering relative to schema size (e.g. adventure_works at 5.70). Generated automatically by `tools/list_best_configs.py`.

> Run `python tools/list_best_configs.py` after adding or re-tuning any dataset to regenerate this table from current results.


