#!/usr/bin/env python
# @category Analysis
#
# Headless preScript to force-enable the analyzer required by LATTE:
# "Decompiler Parameter ID"

program = currentProgram

wanted = {
    "Decompiler Parameter ID": "true",
}
optional = {
    "Decompiler Parameter ID.Analysis Decompiler Timeout (sec)": "120",
}

try:
    current = getCurrentAnalysisOptionsAndValues(program)
except Exception as e:
    current = None
    print("[LATTE prescript] failed reading current analysis options: {}".format(e))

final_options = {}
final_options.update(wanted)
if current is not None:
    for k, v in optional.items():
        try:
            if current.containsKey(k):
                final_options[k] = v
        except Exception:
            pass

bulk_ok = False
try:
    setAnalysisOptions(program, final_options)
    bulk_ok = True
except Exception as e:
    print("[LATTE prescript] bulk setAnalysisOptions failed: {}".format(e))

if not bulk_ok:
    for k, v in final_options.items():
        try:
            setAnalysisOption(program, k, v)
        except Exception as e:
            print("[LATTE prescript] failed setting '{}': {}".format(k, e))

try:
    verify = getCurrentAnalysisOptionsAndValues(program)
    for k in final_options.keys():
        val = verify.get(k) if verify is not None else None
        print("[LATTE prescript] {} = {}".format(k, val))
except Exception as e:
    print("[LATTE prescript] verify failed: {}".format(e))

