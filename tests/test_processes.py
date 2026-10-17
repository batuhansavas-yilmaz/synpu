from synpu.metrics.processes import parse_gpu_engine


def test_parse_gpu_engine_sums_per_pid():
    payload = [
        {"Name": "pid_1234_luid_0x0_phys_0_eng_0_engtype_3D", "UtilizationPercentage": 20},
        {"Name": "pid_1234_luid_0x0_phys_0_eng_1_engtype_3D", "UtilizationPercentage": 5},
        {"Name": "pid_99_luid_0x0_phys_0_eng_0_engtype_3D", "UtilizationPercentage": 7},
        {"Name": "pid_50_luid_0x0_phys_0_eng_0_engtype_Copy", "UtilizationPercentage": 90},
    ]
    assert parse_gpu_engine(payload) == {1234: 25.0, 99: 7.0, 50: 90.0}


def test_parse_gpu_engine_single_dict():
    payload = {"Name": "pid_7_luid_0x0_phys_0_eng_0_engtype_3D", "UtilizationPercentage": 12}
    assert parse_gpu_engine(payload) == {7: 12.0}
