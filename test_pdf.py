from multimodal.adapter import MultimodalAdapter

res = MultimodalAdapter.extract_text('demo/maintenance_sop.pdf')
print('EXTRACTED TEXT:')
print(res.get('text', ''))
