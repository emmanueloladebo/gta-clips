"""
Acceptance Test 7: Cloudflare R2 Storage Quotas and Presigned URLs.
Verifies soft 8 GiB threshold alerts and hard 10 GiB upload blockage.
"""
import pytest
from packages.shared.storage import StorageManager, QuotaExceededError


def test_r2_upload_and_presigned_url(tmp_path):
    mgr = StorageManager()
    mgr.mock_mode = True
    mgr.mock_r2_dir = tmp_path / "mock_r2"
    mgr.mock_r2_dir.mkdir(parents=True, exist_ok=True)

    dummy_clip = tmp_path / "clip_1.mp4"
    dummy_clip.write_bytes(b"\x00" * 1024 * 100)  # 100 KB

    key = mgr.upload_to_r2(str(dummy_clip), "clips/clip_1.mp4")
    assert key == "clips/clip_1.mp4"
    assert (mgr.mock_r2_dir / "clips" / "clip_1.mp4").exists()

    url = mgr.generate_presigned_url(key)
    assert "mock-media/clips/clip_1.mp4" in url


def test_r2_quota_enforcement(tmp_path):
    mgr = StorageManager()
    mgr.mock_mode = True
    mgr.mock_r2_dir = tmp_path / "mock_r2"
    mgr.mock_r2_dir.mkdir(parents=True, exist_ok=True)

    # Set mock limits for test: soft 1 MB, hard 2 MB
    mgr.soft_limit = 1024 * 1024  # 1 MB
    mgr.hard_limit = 2 * 1024 * 1024  # 2 MB

    # 1. Upload 500 KB: within limits
    file_500kb = tmp_path / "file_500k.mp4"
    file_500kb.write_bytes(b"\x00" * (500 * 1024))
    mgr.upload_to_r2(str(file_500kb), "file1.mp4")

    quota = mgr.check_r2_quota()
    assert not quota["soft_limit_exceeded"]
    assert not quota["hard_limit_exceeded"]

    # 2. Upload another 700 KB: total 1.2 MB -> exceeds soft limit (1 MB)
    file_700kb = tmp_path / "file_700k.mp4"
    file_700kb.write_bytes(b"\x00" * (700 * 1024))
    mgr.upload_to_r2(str(file_700kb), "file2.mp4")

    quota = mgr.check_r2_quota()
    assert quota["soft_limit_exceeded"]
    assert not quota["hard_limit_exceeded"]

    # 3. Try to upload 1.5 MB: total 2.7 MB -> exceeds hard limit (2 MB) -> must raise QuotaExceededError!
    file_1500kb = tmp_path / "file_1500k.mp4"
    file_1500kb.write_bytes(b"\x00" * (1500 * 1024))

    with pytest.raises(QuotaExceededError) as exc_info:
        mgr.upload_to_r2(str(file_1500kb), "file3_too_large.mp4")

    assert "Hard storage limit" in str(exc_info.value)
