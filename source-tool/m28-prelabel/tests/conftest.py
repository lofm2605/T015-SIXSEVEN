"""Cô lập cài đặt của trang (tool/cai_dat.py) khỏi máy thật: mọi test chạy với M28_CONFIG_DIR trỏ vào thư mục tạm và Settings dùng chung
được dựng lại, nên không test nào đọc hay ghi hồ sơ người dùng thật (%APPDATA%\\m28, ~/.config/m28)."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tool'))


@pytest.fixture(autouse=True)
def _isolated_user_settings(tmp_path_factory, monkeypatch):
    import cai_dat
    d = tmp_path_factory.mktemp('m28cfg')
    monkeypatch.setenv(cai_dat.ENV_DIR, str(d / 'm28'))
    cai_dat.reset()
    yield
    cai_dat.reset()
