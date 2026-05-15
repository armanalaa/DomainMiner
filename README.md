# DomainDiscover

**Automatic data mesh domain discovery from data lake CSV tables.**  
DomainDiscover takes a collection of CSV files and groups them into business domains using column similarity, table graphs, and Louvain clustering, with LLM-generated domain labels.

---

## Table of Contents

1. [How It Works](#how-it-works)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Folder Structure](#folder-structure)
5. [Step-by-Step: Running the Pipeline](#step-by-step-running-the-pipeline)
   - [Step 0 — Prepare your dataset](#step-0--prepare-your-dataset)
   - [Step 1 — Extract schema](#step-1--extract-schema)
   - [Step 2 — Extract knowledge](#step-2--extract-knowledge)
   - [Step 3 — Tune parameters](#step-3--tune-parameters)
   - [Step 4 — Build results summary](#step-4--build-results-summary)
   - [Step 5 — Pick the best result](#step-5--pick-the-best-result)
6. [Running a Single Configuration](#running-a-single-configuration)
7. [Parameter Reference](#parameter-reference)
8. [Validated Datasets](#validated-datasets)

---

## How It Works

The pipeline runs in 5 stages (CCM):

| Stage | Script | What it does |
|---|---|---|
| 1 — Prepare | `extract_schema.py` + `extract_knowledge.py` | Profiles columns, builds embeddings, extracts business knowledge from a PDF via LLM |
| 2 — Column similarity | `1_knowledge_concept_embedding.py`, `2_p_stat_name_sem.py`, `3_sim_attr_weights.py` | Computes statistical, name, and semantic similarity between every column pair |
| 3 — Column graph | `4_column_graph.py` | Connects similar columns above a threshold into a graph |
| 4 — Table graph | `5_table_similarity.py` | Aggregates column edges into table-level similarity; builds a table graph |
| 5 — Domain discovery | `6_domain_discovery.py` | Runs Louvain clustering; LLM assigns a business name to each domain |

---

## Requirements

- Python 3.9 or higher
- [Ollama](https://ollama.com) installed and running locally
- Git

### Python packages

```bash
pip install pandas numpy scikit-learn sentence-transformers python-docx \
            networkx python-louvain requests openpyxl tqdm
```

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/armanalaa/DomainDiscover.git
cd DomainDiscover

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
DomainDiscover/
│
├── extract_schema.py
├── extract_knowledge.py
├── run_pipeline.py
├── tune_params.py
├── pipeline_utils.py
├── 1_knowledge_concept_embedding.py
├── 2_p_stat_name_sem.py
├── 3_sim_attr_weights.py
├── 4_column_graph.py
├── 5_table_similarity.py
├── 6_domain_discovery.py
├── Modelfile
│
└── <YourDataset>/
    ├── csv/                  ← put all your CSV files here
    ├── knowledge/            ← put the dataset PDF here (one PDF)
    ├── logs/                 ← created automatically
    └── ccm_output/           ← all results written here
        ├── tA0.65_tT0.70_r1.2/
        │   ├── step3_sim_attr_report.txt
        │   ├── step4_report.txt
        │   └── step5_report.txt
        ├── tune_params_results.xlsx
        └── tune_params_summary.txt
```

---

## Step-by-Step: Running the Pipeline

Replace `<Dataset>` with your dataset folder name and `<DBName>` with a short name for your database (e.g. `TPC-H`, `Northwind`).

---

### Step 0 — Prepare your dataset

1. Create a folder with your dataset name inside the project root.
2. Put all CSV files inside `<Dataset>/csv/`.
3. Put the dataset documentation PDF inside `<Dataset>/knowledge/`.

```
DomainDiscover/
└── MyDataset/
    ├── csv/
    │   ├── orders.csv
    │   ├── customer.csv
    │   └── ...
    └── knowledge/
        └── MyDataset_docs.pdf
```

> **Tip — which tables to keep?**  
> Remove pure lookup tables with very few rows and columns that have no business process meaning (e.g. a `region` table with 5 rows and 2 columns). Keep junction tables only if they encode a real business relationship.

---

### Step 1 — Extract schema

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

### Step 2 — Extract knowledge

Reads the PDF in `knowledge/` and uses the LLM to extract business descriptions of each table and column. Writes `knowledge.docx`.

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

> This step can take 10–30 minutes depending on the PDF size. Progress is logged to `<Dataset>/logs/`.

---

### Step 3 — Tune parameters

Runs all 27 combinations of `theta_a`, `theta_t`, and `resolution` automatically and scores each with modularity Q.

```bash
python tune_params.py \
  --dataset_dir <Dataset> \
  --knowledge knowledge.docx \
  --theta_a 0.60 0.65 0.70 \
  --theta_t 0.65 0.70 0.75 \
  --resolution 1.2 1.5 2.0
```

**Output:**
- `<Dataset>/ccm_output/tune_params_results.xlsx` — color-coded Excel table (green = Q ≥ 0.3, red = Q < 0.3)
- `<Dataset>/ccm_output/tune_params_summary.txt` — plain text table sorted by Q descending

---

### Step 4 — Pick the best result

Open `ccm_output/tune_params_results.xlsx`.

- **Valid result:** Q ≥ 0.3 (Newman & Girvan, 2004)
- Pick the run with the **highest Q** and the most coherent domain labels
- The best run's output is in `ccm_output/tA<x>_tT<y>_r<z>/step5_report.txt`

> If no run reaches Q ≥ 0.3, the schema is likely too small or too densely connected (e.g. fewer than 12 tables). Document the best Q achieved and note it as a structural property of the dataset.

---

