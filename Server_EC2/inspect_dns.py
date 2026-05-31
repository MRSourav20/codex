#!/usr/bin/env python3
"""
Inspection script: prints the exact structure of packet.dns fields
so we know how to extract domain names from the 'queries' field.
"""
import pyshark
import sys

print("Waiting for a DNS packet on interface 'any'...")
print("(browse something or run: curl https://google.com in another terminal)")
print("="*60)

capture = pyshark.LiveCapture(interface='any', display_filter='dns')

for pkt in capture.sniff_continuously(packet_count=3):
    if not hasattr(pkt, 'dns'):
        continue
    dns = pkt.dns

    print("\n--- _all_fields (first 40 keys) ---")
    if hasattr(dns, '_all_fields'):
        for i, (k, v) in enumerate(dns._all_fields.items()):
            if i >= 40:
                break
            print(f"  {repr(k)}: {repr(str(v)[:100])}")
    else:
        print("  (no _all_fields attribute)")

    print("\n--- dir() query/name related attrs ---")
    for a in dir(dns):
        if any(x in a.lower() for x in ['qry', 'query', 'name', 'queries']):
            print(f"  {repr(a)}")

    if hasattr(dns, 'queries'):
        q = dns.queries
        print(f"\n--- dns.queries ---")
        print(f"  type: {type(q)}")
        print(f"  repr: {repr(str(q)[:300])}")
        if hasattr(q, '_all_fields'):
            print(f"  q._all_fields: {dict(q._all_fields)}")
        if hasattr(q, '__iter__'):
            for item in q:
                print(f"  item type: {type(item)}, repr: {repr(str(item)[:200])}")

    print("\n" + "="*60)
    print("DONE INSPECTING PACKET")
    break

capture.close()
