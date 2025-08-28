def increment_ip(ip_str):
    ip = parse_ipv4(ip_str)
    ip = [s if i < 3 else s + 1 for i, s in enumerate(ip)]
    return ".".join([str(s) for s in ip])


def parse_ipv4(ip_str):
    segments = ip_str.strip().split(".")
    segments = [int(s) for s in segments]
    return segments


def is_valid_ipv4(ip_str):
    segments = parse_ipv4(ip_str)
    segments = [s for s in segments if s >= 0 and s <= 255]
    return len(segments) == 4
