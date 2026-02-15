# ⚠️ ModelScan Bypass PoC — Security Research

> **WARNING: This repository contains proof-of-concept code for security research purposes only.**
> **Do NOT load these pickle files in production environments.**

## Overview

This repository demonstrates **5 methods to bypass ProtectAI's ModelScan** (v0.8.7, latest as of Feb 2026), the model scanner used by HuggingFace to detect malicious ML models.

All 5 bypass methods produce pickle files that:
- ✅ Pass ModelScan with **"No issues found"** (CLEAN)
- ❌ Execute **arbitrary code** when loaded with `pickle.load()`, `joblib.load()`, or `torch.load()`

## Bypass Methods

| # | Module | Function | Code Execution Mechanism |
|---|--------|----------|--------------------------|
| 1 | `timeit` | `timeit()` | Executes string as Python code via `compile()` + `exec()` internally |
| 2 | `timeit` | `repeat()` | Same as above, repeated execution |
| 3 | `cProfile` | `run()` | Profiles (and executes) arbitrary Python code string |
| 4 | `profile` | `run()` | Pure-Python profiler, same execution capability |
| 5 | `doctest` | `debug_script()` | Compiles and executes Python source string |

## Root Cause

ModelScan maintains a blocklist of "unsafe globals" in `settings.py`. The modules `timeit`, `cProfile`, `profile`, and `doctest` are **not included** in this blocklist, despite all having functions that execute arbitrary Python code from string arguments.

## Reproduction

```bash
pip install modelscan
python generate_poc.py
modelscan --path poc_models/bypass_timeit_timeit.pkl
# Output: "No issues found! 🎉"

# Verify code execution:
python -c "import pickle; pickle.load(open('poc_models/bypass_timeit_timeit.pkl','rb'))"
# Output: creates /tmp/poc_proof file
```

## Disclosure

- Reported to ProtectAI via Huntr.com
- Author: Hussain Al-Saibai (hussain.alsaibai@gmail.com)
