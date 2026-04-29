import ipaddress


def _is_ip_literal(host: str) -> bool:
    h = host.strip("[]")
    try:
        ipaddress.ip_address(h)
        return True
    except ValueError:
        return False


def _parse_content_length(header_block: bytes) -> int:
    for raw_line in header_block.split(b"\r\n"):
        name, sep, value = raw_line.partition(b":")
        if sep and name.strip().lower() == b"content-length":
            try:
                return int(value.strip())
            except ValueError:
                return 0
    return 0


def _has_unsupported_transfer_encoding(header_block: bytes) -> bool:
    for raw_line in header_block.split(b"\r\n"):
        name, sep, value = raw_line.partition(b":")
        if not sep or name.strip().lower() != b"transfer-encoding":
            continue
        encodings = [token.strip().lower() for token in value.decode(errors="replace").split(",") if token.strip()]
        return any(token != "identity" for token in encodings)
    return False
