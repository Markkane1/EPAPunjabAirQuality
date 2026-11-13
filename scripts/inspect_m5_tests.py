with open('tests/integration/test_m5_remediation_adversarial_deep.py', 'r', encoding='utf-8') as f:
    t1 = f.read()
with open('tests/integration/test_m5_resilience_challenge.py', 'r', encoding='utf-8') as f:
    t2 = f.read()

print("test_m5_remediation_adversarial_deep.py lines:", len(t1.split('\n')))
for l in t1.split('\n'):
    if 'def test_' in l:
        print(" ", l)

print("\ntest_m5_resilience_challenge.py lines:", len(t2.split('\n')))
for l in t2.split('\n'):
    if 'def test_' in l:
        print(" ", l)
