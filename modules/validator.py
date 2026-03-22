import re
from typing import Set

# Valid IP address statuses
VALID_STATUSES: Set[str] = {"Active", "Inactive", "Reserved"}


def validate_ip(ip: str) -> bool:
    """Validate an IPv4 address string."""
    pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    if not re.match(pattern, ip.strip()):
        return False
    return all(0 <= int(p) <= 255 for p in ip.strip().split("."))


def validate_subnet(subnet: str) -> bool:
    """Validate subnet — accepts CIDR (0-32) or dotted netmask notation."""
    subnet = subnet.strip()
    # CIDR prefix
    try:
        val = int(subnet)
        return 0 <= val <= 32
    except ValueError:
        pass
    # Dotted netmask - must have contiguous 1s followed by 0s
    pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    if re.match(pattern, subnet):
        try:
            parts = [int(p) for p in subnet.split(".")]
            if not all(0 <= p <= 255 for p in parts):
                return False
            # Convert to 32-bit integer
            num = (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]
            # Valid netmask: all 1s followed by all 0s in binary
            inv = num ^ 0xffffffff
            return (inv + 1) & inv == 0
        except (ValueError, IndexError):
            return False
    return False


def normalize_subnet(subnet: str) -> str:
    """Return subnet in a clean string form."""
    subnet = subnet.strip()
    try:
        val = int(subnet)
        if 0 <= val <= 32:
            return str(val)
    except ValueError:
        pass
    return subnet


def ip_to_int(ip: str) -> int:
    """Convert IPv4 string to integer for sorting/comparison."""
    parts = ip.strip().split(".")
    result = 0
    for p in parts:
        result = result * 256 + int(p)
    return result


def validate_hostname_unique(hostname: str, records: list, exclude_index: int = -1) -> bool:
    """
    Check if hostname is unique among records (ignoring exclude_index).
    Empty/whitespace hostnames are always allowed.
    Returns True if hostname is unique (or empty), False if duplicate.
    """
    hostname = hostname.strip()
    if not hostname:
        return True
    
    for i, rec in enumerate(records):
        if i == exclude_index:
            continue
        if rec.get("hostname", "").strip().lower() == hostname.lower():
            return False
    return True


def ip_in_subnet(ip: str, subnet_cidr: str, network_ip: str = "") -> bool:
    """
    Check if an IP address is in a given subnet.
    If network_ip is provided, checks whether ip is in that specific network.
    Otherwise returns True when the IP and mask are syntactically valid.

    Example: ip_in_subnet("192.168.1.5", "24", "192.168.1.0") -> True
             ip_in_subnet("10.0.0.1",    "24", "192.168.1.0") -> False
    """
    try:
        cidr = int(subnet_cidr) if subnet_cidr.isdigit() else _netmask_to_cidr(subnet_cidr)
        mask = (0xFFFFFFFF << (32 - cidr)) & 0xFFFFFFFF

        def _to_int(addr: str) -> int:
            parts = [int(p) for p in addr.strip().split(".")]
            return (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]

        if network_ip:
            return (_to_int(ip) & mask) == (_to_int(network_ip) & mask)
        return True
    except Exception:
        return False


def _netmask_to_cidr(netmask: str) -> int:
    """Convert dotted netmask to CIDR prefix."""
    try:
        parts = [int(p) for p in netmask.split(".")]
        num = (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]
        # Count leading 1s
        cidr = 0
        for i in range(32, 0, -1):
            if num & (1 << (i - 1)):
                cidr += 1
            else:
                break
        return cidr
    except Exception:
        return 24


def detect_subnet_overlaps(ip: str, subnet: str, records: list, exclude_index: int = -1) -> list:
    """
    Detect if the given IP/subnet overlaps with any existing record's subnet.

    Two subnets A and B overlap when A contains B's network address or vice-versa,
    i.e. (net_A & min_mask) == (net_B & min_mask) where min_mask uses the smaller
    prefix (larger block).

    Returns a list of existing IPs whose subnet overlaps with the given one.
    """
    overlaps = []

    def _to_int(addr: str) -> int:
        parts = [int(p) for p in addr.strip().split(".")]
        return (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]

    def _mask(cidr: int) -> int:
        return (0xFFFFFFFF << (32 - cidr)) & 0xFFFFFFFF

    try:
        cidr_a = int(subnet) if subnet.isdigit() else _netmask_to_cidr(subnet)
        net_a = _to_int(ip) & _mask(cidr_a)

        for i, rec in enumerate(records):
            if i == exclude_index:
                continue
            existing_ip = rec.get("ip", "")
            existing_subnet = rec.get("subnet", "24")
            try:
                cidr_b = int(existing_subnet) if existing_subnet.isdigit() else _netmask_to_cidr(existing_subnet)
                net_b = _to_int(existing_ip) & _mask(cidr_b)
                # Use the less-specific (broader) mask to test containment
                min_cidr = min(cidr_a, cidr_b)
                broad_mask = _mask(min_cidr)
                if (net_a & broad_mask) == (net_b & broad_mask):
                    overlaps.append(existing_ip)
            except Exception:
                pass
    except Exception:
        pass

    return overlaps


