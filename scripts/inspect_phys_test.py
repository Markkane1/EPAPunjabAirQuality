with open('tests/integration/test_m5_resilience_challenge.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('test_physical_invariant_frontend_client_guards')
if idx != -1:
    print(text[idx:idx+800])
