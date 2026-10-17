from synpu.ui.qr_window import build_qr_image, should_autoshow


def test_build_qr_image_size():
    img = build_qr_image("http://192.168.1.13:8787")
    assert img.size[0] >= 100 and img.size[1] >= 100


def test_should_autoshow_first_then_false(tmp_path):
    assert should_autoshow(tmp_path) is True
    assert should_autoshow(tmp_path) is False
