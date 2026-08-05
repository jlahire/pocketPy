"""
prewarm.py - pull everything down before you go offline.

Run once, on wifi, in the IDE. It downloads each package so the service worker
caches it, then imports it to prove it works. When it finishes, Share -> Add to
Home Screen. After that these all work with the network off.

Only what you download gets cached. Anything you skip here fails later offline.
Edit the lists below. The whole set is a few minutes and 100-200MB.
"""

import sys
import time

import pyodide_js

# micropip ships with the runtime but is not loaded until something asks for it
await pyodide_js.loadPackage("micropip")
import micropip  # noqa: E402

# ---------------------------------------------------------------- lists

# Built by Pyodide as wasm. These come from the runtime, never from PyPI.
RUNTIME = [
    "numpy",
    "pandas",
    "matplotlib",
    "scipy",
    "sympy",
    "scikit-learn",
    "pillow",
    "lxml",
    "beautifulsoup4",
    "requests",
    "cryptography",
    "pyyaml",
    "regex",
    "python-dateutil",
]

# Pure python wheels off PyPI. Must be py3-none-any.
PYPI = [
    "pyodide-http",   # makes requests and urllib actually reach the network
    "construct",      # declarative binary parsing
    "rich",
    "tabulate",
    "python-dotenv",
    "jinja2",
    "markdown",
    "httpx",
    # "black",        # uncomment for the fmt command offline, ~10MB
    # "pytest",
]

# import name when it differs from the package name
IMPORT_AS = {
    "beautifulsoup4": "bs4",
    "pyyaml": "yaml",
    "pillow": "PIL",
    "scikit-learn": "sklearn",
    "python-dateutil": "dateutil",
    "python-dotenv": "dotenv",
    "pyodide-http": "pyodide_http",
}

# ---------------------------------------------------------------- work

ok, failed = [], []


def note(mark, name, detail=""):
    print(f"  {mark} {name}{('  ' + detail) if detail else ''}", flush=True)


LOCAL = "http" in str(getattr(pyodide_js, "version", "")) or False


def loaded(name):
    """loadPackage resolves even when the download 404s, so check the ledger."""
    try:
        keys = [str(k).lower() for k in pyodide_js.loadedPackages.object_keys()]
    except Exception:
        try:
            keys = [str(k).lower() for k in dir(pyodide_js.loadedPackages)]
        except Exception:
            return True          # cannot tell, assume it worked
    return name.lower() in keys


async def fetch(name):
    """Runtime build first, PyPI wheel second. Same order the IDE uses."""
    try:
        await pyodide_js.loadPackage(name)
        if loaded(name):
            return "runtime"
    except Exception:
        pass
    await micropip.install(name)
    return "pypi"


async def grab(name):
    t0 = time.time()
    try:
        how = await fetch(name)
    except Exception as e:
        failed.append((name, str(e).split("\n")[0][:110]))
        note("x", name, str(e).split("\n")[0][:70])
        return

    mod = IMPORT_AS.get(name, name.replace("-", "_"))
    try:
        __import__(mod)
        ok.append(name)
        note("+", name, f"{how}  {time.time() - t0:.1f}s")
    except Exception as e:
        why = f"not actually present: {e}"
        failed.append((name, why))
        note("!", name, f"missing. on the server run:  ./setup.sh {name}")


print("runtime packages")
for pkg in RUNTIME:
    await grab(pkg)

print("\npypi wheels")
for pkg in PYPI:
    await grab(pkg)

# local wheels you dropped in ./wheels
import os  # noqa: E402

if os.path.isdir("wheels"):
    print("\nlocal wheels")
    for f in sorted(os.listdir("wheels")):
        if not f.endswith(".whl"):
            continue
        try:
            await micropip.install("emfs:" + os.path.abspath("wheels/" + f))
            ok.append(f)
            note("+", f)
        except Exception as e:
            failed.append((f, str(e)[:110]))
            note("x", f, str(e)[:70])

# ---------------------------------------------------------------- warm up

print("\nwarming up")

try:
    import matplotlib.pyplot as plt

    fig = plt.figure()
    plt.plot([0, 1, 2], [0, 1, 4])
    fig.canvas.draw()          # builds the font cache, slow only once
    plt.close("all")
    note("+", "matplotlib font cache")
except Exception as e:
    note("-", "matplotlib", str(e)[:60])

try:
    import pandas as pd

    pd.DataFrame({"a": [1, 2]}).describe()
    note("+", "pandas")
except Exception as e:
    note("-", "pandas", str(e)[:60])

try:
    import pyodide_http

    pyodide_http.patch_all()
    note("+", "network patch for requests")
except Exception as e:
    note("-", "pyodide_http", str(e)[:60])

# ---------------------------------------------------------------- report

lines = [
    f"prewarmed {time.strftime('%Y-%m-%d %H:%M')}",
    f"python {sys.version.split()[0]}",
    "",
    f"ready ({len(ok)}):",
]
lines += [f"  {n}" for n in ok]
if failed:
    lines += ["", f"failed ({len(failed)}):"]
    lines += [f"  {n}: {why}" for n, why in failed]

with open("prewarm-report.txt", "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"\n{len(ok)} ready, {len(failed)} failed")
for n, why in failed:
    print(f"  {n}: {why}")

if len(failed) > len(ok):
    print()
    print("that many failures usually means the local runtime folder is empty.")
    print("on the machine serving this, run:")
    print("    ./setup.sh --recommended")
    print("then reload here and run this again.")
print("\nwrote prewarm-report.txt")
print("now: Share -> Add to Home Screen. do not clear site data.")
