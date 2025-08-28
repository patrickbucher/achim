def parse_ipv4(ip):
    segments = ip.strip().split(".")
    segments = [int(s) for s in segments]
    return segments

def is_valid_ipv4(ip):
    segments = parse_ipv4(ip)
    segments = [s for s in segments if s >= 0 and s <= 255]
    return len(segments) == 4
