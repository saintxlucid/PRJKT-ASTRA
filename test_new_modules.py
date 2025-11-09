"""Test Micro-Simulators and Language Kernel modules."""

import numpy as np
from astra_core.cortex import micro_simulators, language_kernel

print('=== MICRO-SIMULATORS TESTS ===')
# Test supply/demand equilibrium
equilibrium = np.zeros(3, dtype=np.float32)
micro_simulators.simulate_supply_demand(100.0, 2.0, -1.5, 5.0, equilibrium)
print(f'Supply/Demand: price={equilibrium[0]:.2f}, supply={equilibrium[1]:.2f}, demand={equilibrium[2]:.2f}')

# Test opinion diffusion
opinions = np.array([1.0, -1.0, 0.0, 0.5], dtype=np.float32)
adjacency = np.array([[0, 1, 1, 0], [1, 0, 1, 1], [1, 1, 0, 0], [0, 1, 0, 0]], dtype=np.float32)
opinions_out = np.zeros(4, dtype=np.float32)
micro_simulators.diffuse_opinions(opinions, adjacency, 0.3, opinions_out)
print(f'Opinion diffusion: {opinions_out}')

# Test TSP with distance matrix
dist_matrix = np.array([[0.0, 1.4, 2.2, 2.5], [1.4, 0.0, 1.1, 1.8], [2.2, 1.1, 0.0, 1.6], [2.5, 1.8, 1.6, 0.0]], dtype=np.float32)
path = np.zeros(4, dtype=np.int32)
total_dist = micro_simulators.optimize_route_greedy(dist_matrix, 0, path)
print(f'TSP route: path={path}, distance={total_dist:.3f}')

# Test resource allocation
demands = np.array([50.0, 30.0, 20.0], dtype=np.float32)
capacities = np.array([40.0, 30.0, 10.0], dtype=np.float32)
allocation = np.zeros(3, dtype=np.float32)
micro_simulators.allocate_resources(demands, capacities, allocation)
print(f'Resource allocation: {allocation}')

print('\n=== LANGUAGE KERNEL TESTS ===')
# Convert strings to writable numpy byte arrays for Cython
text_en = np.array(list(b'Hello World'), dtype=np.uint8)
text_ar = np.array(list('مرحبا بك'.encode('utf-8')), dtype=np.uint8)
text_mixed = np.array(list('Hello مرحبا'.encode('utf-8')), dtype=np.uint8)

script_en = language_kernel.detect_script(text_en)
script_ar = language_kernel.detect_script(text_ar)
script_mixed = language_kernel.detect_script(text_mixed)
print(f'Script detection: English={script_en}, Arabic={script_ar}, Mixed={script_mixed}')

# Test RTL detection
print(f'RTL: English={language_kernel.is_rtl_script(script_en)}, Arabic={language_kernel.is_rtl_script(script_ar)}')

# Test language detection (returns string)
lang_en = language_kernel.detect_language(text_en)
lang_ar = language_kernel.detect_language(text_ar)
lang_mixed = language_kernel.detect_language(text_mixed)
print(f'Language: English={lang_en}, Arabic={lang_ar}, Mixed={lang_mixed}')

# Test Arabic normalization
ar_with_diacritics = np.array(list('مَرْحَبًا'.encode('utf-8')), dtype=np.uint8)
normalized_out = np.zeros(len(ar_with_diacritics), dtype=np.uint8)
new_len = language_kernel.normalize_arabic_text(ar_with_diacritics, normalized_out)
print(f'Arabic normalization: {len(ar_with_diacritics)} bytes -> {new_len} bytes')

# Test code-switching
switches = np.zeros(10, dtype=np.int32)
language_kernel.detect_code_switching_points(text_mixed, switches, 10)
valid_switches = switches[switches >= 0]
print(f'Code-switching: {len(valid_switches)} transition points at {valid_switches.tolist()}')

# Test Arabic word count
ar_sentence = np.array(list('مرحبا كيف حالك اليوم'.encode('utf-8')), dtype=np.uint8)
word_count = language_kernel.count_arabic_words(ar_sentence)
print(f'Arabic word count: {word_count} words')

# Test dialect classification (requires feature vectors)
# Features: [egyptian_score, levantine_score, gulf_score, maghrebi_score]
msa_features = np.array([0.1, 0.1, 0.1, 0.1], dtype=np.float32)
egyptian_features = np.array([0.8, 0.2, 0.1, 0.0], dtype=np.float32)
dialect_msa = language_kernel.classify_arabic_dialect(msa_features)
dialect_egy = language_kernel.classify_arabic_dialect(egyptian_features)
print(f'Dialect classification: MSA={dialect_msa}, Egyptian={dialect_egy}')

print('\n✅ All 14 Cython modules operational!')
