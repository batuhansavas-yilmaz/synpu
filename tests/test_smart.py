from synpu.metrics.smart import parse_health, parse_smart_payload, parse_smart_temp


def _table(attrs: dict[int, tuple[int, ...]]) -> bytes:
    data = bytearray([1, 0])
    for attr_id, raw in attrs.items():
        entry = bytearray(12)
        entry[0] = attr_id
        entry[5:5 + len(raw)] = bytes(raw)
        data.extend(entry)
    data.extend(b"\x00" * 12)
    return bytes(data)


def test_parse_smart_temp_attr_194():
    raw = _table({5: (0,), 194: (40, 20, 60, 0, 0, 0)})
    assert parse_smart_temp(raw) == 40.0


def test_parse_smart_temp_attr_190():
    raw = _table({190: (36, 25, 50, 0, 0, 0)})
    assert parse_smart_temp(raw) == 36.0


def test_parse_smart_temp_none():
    raw = _table({5: (0,)})
    assert parse_smart_temp(raw) is None


def test_parse_payload_maps_letter():
    payload = {
        "disks": [
            {"model": "Samsung SSD 870 EVO 1TB", "letters": "D:"},
            {"model": "Samsung SSD 970 EVO Plus 500GB", "letters": "C:"},
        ],
        "smart": [
            {
                "instance": r"SCSI\Disk&Ven_Samsung&Prod_SSD_870_EVO_1TB\4&236eeeb9&0&050000_0",
                "bytes": list(_table({190: (36, 0, 0, 0, 0, 0)})),
            },
        ],
    }
    assert parse_smart_payload(payload) == {"D:": 36.0}


def test_parse_health():
    payload = [
        {"disk": 0, "wear": 3, "hours": 1234},
        {"disk": 1, "wear": None, "hours": None},
    ]
    assert parse_health(payload) == {
        "PhysicalDrive0": {"health_pct": 97.0, "power_on_hours": 1234},
    }
