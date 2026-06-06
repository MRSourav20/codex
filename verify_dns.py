import pyshark
import sys

print('Starting verification...')
capture = pyshark.LiveCapture(interface='any', display_filter='dns')
for pkt in capture.sniff_continuously(packet_count=5):
    if hasattr(pkt, 'dns') and hasattr(pkt.dns, '_all_fields'):
        fields = pkt.dns._all_fields
        found = False
        for k, v in fields.items():
            if 'qry.name' in k.lower() or 'query.name' in k.lower():
                print(f'Captured Domain: {v}')
                found = True
        if not found:
            print('No query field found in packet')
    else:
        print('Packet without DNS layer')
print('Finished verification')
