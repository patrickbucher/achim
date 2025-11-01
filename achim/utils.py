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


def parse_label_value_arg(arg):
    pairs = arg.split(",") if "," in arg else [arg]
    label_values = [p.strip().split("=") for p in pairs]
    if not label_values:
        raise ValueError(f"invalid arg '{arg}'")
    return {
        x[0].strip(): x[1].strip()
        for x in label_values
        if len(x) == 2 and x[0] and x[1]
    }
