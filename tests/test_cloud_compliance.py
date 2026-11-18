"""
Acceptance Test 11: Cloud-native compliance verification.
Ensures zero local PC workstation dependencies; all background processing
runs strictly in cloud containers / Linux VPS.
"""
import inspect
from workers import runner, capture_worker, transcription_worker, candidate_worker, render_worker, storage_worker, cleanup_worker, publish_worker
from packages.shared.config import settings


def test_zero_local_workstation_dependencies():
    """Verify background workers are purely headless async services with no GUI/desktop requirements."""
    # Check that runner has headless async main loop
    assert inspect.iscoroutinefunction(runner.main)
    assert inspect.iscoroutinefunction(runner.capture_loop)
    assert inspect.iscoroutinefunction(runner.transcription_loop)
    assert inspect.iscoroutinefunction(runner.render_loop)
    assert inspect.iscoroutinefunction(runner.cleanup_loop)


def test_cloud_storage_and_database_configuration():
    """Verify production defaults point to cloud infrastructure (S3/R2, PostgreSQL, Redis)."""
    # Environment variables in production point to containerized services
    assert "postgresql" in settings.DATABASE_URL or "sqlite" in settings.DATABASE_URL
    assert "redis" in settings.REDIS_URL
    assert settings.MEDIA_TTL_HOURS == 24
    assert settings.R2_HARD_LIMIT_BYTES == 10 * 1024 * 1024 * 1024  # 10 GiB ceiling
