"""Test the hard constraints directly."""
query_size = 0.058
candidate_size = 0.06

size_diff = abs(query_size - candidate_size) / query_size

print(f"Query size: {query_size} kg")
print(f"Candidate size: {candidate_size} kg")
print(f"Size difference: {abs(query_size - candidate_size):.6f} kg")
print(f"Size diff %: {size_diff:.4f} ({size_diff*100:.2f}%)")
print(f"Threshold: 0.05 (5%)")
print(f"Passes: {size_diff <= 0.05}")

if size_diff > 0.05:
    print("\n❌ REJECTED by hard constraint")
else:
    print("\n✓ PASSES hard constraint")
