FINE_RATE = 0.50
def compute_fine(days_late):
    return max(0, days_late) * FINE_RATE