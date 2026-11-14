import sys
sys.path.insert(0, r'C:\temp\projects\testproject1\src')
from pmk.events import compute_hash
import json

print("Testing kernel's compute_hash")
e = {"seq": 1, "type": "TEST", "payload": {}, "actor": {}}
h = compute_hash(e, e)  # maybe takes (event, body)?
print("Hash:", h)

# Check the function signature
import inspect
print(inspect.signature(compute_hash))