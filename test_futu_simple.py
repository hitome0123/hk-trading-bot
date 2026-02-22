#!/usr/bin/env python3
import os
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

from futu import *
import sys

print("Step 1: Starting test", flush=True)

try:
    print("Step 2: Creating OpenQuoteContext", flush=True)
    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    print("Step 3: Connected successfully!", flush=True)

    print("Step 4: Closing connection", flush=True)
    quote_ctx.close()
    print("Step 5: Closed successfully!", flush=True)

except Exception as e:
    print(f"Error: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("Step 6: Test complete!", flush=True)
