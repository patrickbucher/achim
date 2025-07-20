def is_valid_ipv4(ip):
    segments = ip.strip().split(".")
    segments = [int(s) for s in segments]
    segments = [s for s in segments if s >= 0 and s <= 255]
    return len(segments) == 4
