"""Unit tests for the BookReaderOrchestrator state machine.

Tests verify that the orchestrator routes to the correct skills based on
assess_scene results, without calling the real Claude Vision API.
All perception and motor skills are mocked.
"""

import unittest
from unittest.mock import MagicMock, patch, call


class FakeImageSource:
    """Minimal image source that returns a fixed byte string."""

    def __init__(self):
        self._frame = b"fake-jpeg-bytes"

    def grab(self) -> bytes:
        return self._frame

    def start(self):
        pass

    def stop(self):
        pass

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


class TestOrchestratorStateTransitions(unittest.TestCase):
    """Test that the orchestrator follows the correct state machine paths."""

    @patch("src.skills.orchestrator.read_right")
    @patch("src.skills.orchestrator.read_left")
    @patch("src.skills.orchestrator.classify_page")
    @patch("src.skills.orchestrator.assess_scene")
    def test_no_book_exits_immediately(self, mock_assess, mock_classify,
                                        mock_read_left, mock_read_right):
        """assess_scene -> no_book -> done (no skills executed)."""
        from src.skills.orchestrator import BookReaderOrchestrator

        mock_assess.return_value = "no_book"
        source = FakeImageSource()

        orch = BookReaderOrchestrator(source, silent=True, dry_run=True)
        orch.run()

        mock_assess.assert_called_once()
        mock_classify.assert_not_called()
        mock_read_left.assert_not_called()
        mock_read_right.assert_not_called()

    @patch("src.skills.orchestrator.read_right")
    @patch("src.skills.orchestrator.read_left")
    @patch("src.skills.orchestrator.classify_page")
    @patch("src.skills.orchestrator.assess_scene")
    def test_book_closed_then_open_then_done(self, mock_assess, mock_classify,
                                              mock_read_left, mock_read_right):
        """assess_scene -> book_closed -> open_book -> book_open -> read -> book_done -> close."""
        from src.skills.orchestrator import BookReaderOrchestrator

        # Sequence: closed -> open -> read spread -> done
        mock_assess.side_effect = ["book_closed", "book_open", "book_done"]
        mock_classify.return_value = "content"
        mock_read_left.return_value = "left text"
        mock_read_right.return_value = "right text"

        source = FakeImageSource()
        orch = BookReaderOrchestrator(source, silent=True, dry_run=True)
        orch.run()

        # assess_scene called 3 times
        assert mock_assess.call_count == 3
        # classify called once (for the book_open state)
        mock_classify.assert_called_once()
        # Both pages read
        mock_read_left.assert_called_once()
        mock_read_right.assert_called_once()
        # Spread count should be 1
        assert orch.spread_count == 1

    @patch("src.skills.orchestrator.read_right")
    @patch("src.skills.orchestrator.read_left")
    @patch("src.skills.orchestrator.classify_page")
    @patch("src.skills.orchestrator.assess_scene")
    def test_blank_page_skips_reading(self, mock_assess, mock_classify,
                                      mock_read_left, mock_read_right):
        """When classify_page returns 'blank', read_left/read_right should not be called."""
        from src.skills.orchestrator import BookReaderOrchestrator

        mock_assess.side_effect = ["book_open", "book_done"]
        mock_classify.return_value = "blank"

        source = FakeImageSource()
        orch = BookReaderOrchestrator(source, silent=True, dry_run=True)
        orch.run()

        mock_classify.assert_called_once()
        mock_read_left.assert_not_called()
        mock_read_right.assert_not_called()

    @patch("src.skills.orchestrator.read_right")
    @patch("src.skills.orchestrator.read_left")
    @patch("src.skills.orchestrator.classify_page")
    @patch("src.skills.orchestrator.assess_scene")
    def test_index_page_skips_reading(self, mock_assess, mock_classify,
                                      mock_read_left, mock_read_right):
        """When classify_page returns 'index', reading should be skipped."""
        from src.skills.orchestrator import BookReaderOrchestrator

        mock_assess.side_effect = ["book_open", "book_done"]
        mock_classify.return_value = "index"

        source = FakeImageSource()
        orch = BookReaderOrchestrator(source, silent=True, dry_run=True)
        orch.run()

        mock_read_left.assert_not_called()
        mock_read_right.assert_not_called()

    @patch("src.skills.orchestrator.read_right")
    @patch("src.skills.orchestrator.read_left")
    @patch("src.skills.orchestrator.classify_page")
    @patch("src.skills.orchestrator.assess_scene")
    def test_multiple_spreads(self, mock_assess, mock_classify,
                               mock_read_left, mock_read_right):
        """Orchestrator reads multiple spreads before hitting book_done."""
        from src.skills.orchestrator import BookReaderOrchestrator

        mock_assess.side_effect = ["book_open", "book_open", "book_open", "book_done"]
        mock_classify.return_value = "content"
        mock_read_left.return_value = "text"
        mock_read_right.return_value = "text"

        source = FakeImageSource()
        orch = BookReaderOrchestrator(source, silent=True, dry_run=True)
        orch.run()

        assert orch.spread_count == 3
        assert mock_read_left.call_count == 3
        assert mock_read_right.call_count == 3

    @patch("src.skills.orchestrator.read_right")
    @patch("src.skills.orchestrator.read_left")
    @patch("src.skills.orchestrator.classify_page")
    @patch("src.skills.orchestrator.assess_scene")
    def test_mixed_page_types(self, mock_assess, mock_classify,
                               mock_read_left, mock_read_right):
        """Mix of content and blank pages -- only content pages get read."""
        from src.skills.orchestrator import BookReaderOrchestrator

        mock_assess.side_effect = ["book_open", "book_open", "book_open", "book_done"]
        mock_classify.side_effect = ["content", "blank", "content"]
        mock_read_left.return_value = "text"
        mock_read_right.return_value = "text"

        source = FakeImageSource()
        orch = BookReaderOrchestrator(source, silent=True, dry_run=True)
        orch.run()

        assert orch.spread_count == 3
        # Only 2 out of 3 spreads should trigger reads
        assert mock_read_left.call_count == 2
        assert mock_read_right.call_count == 2


class TestMotorSkillRetry(unittest.TestCase):
    """Test motor skill retry logic."""

    def test_retry_on_failure(self):
        """Motor skill retries the configured number of times."""
        from src.skills.motor import MotorSkill

        skill = MotorSkill(
            name="test_skill",
            policy_path="test/policy",
            duration=5,
            task_description="test",
            dry_run=True,
        )

        # Patch _execute_fallback to fail twice then succeed
        results = [False, False, True]
        skill._execute_fallback = MagicMock(side_effect=results)

        success = skill.execute(max_retries=3)
        assert success is True
        assert skill._execute_fallback.call_count == 3

    def test_gives_up_after_max_retries(self):
        """Motor skill returns False after exhausting retries."""
        from src.skills.motor import MotorSkill

        skill = MotorSkill(
            name="test_skill",
            policy_path="test/policy",
            duration=5,
            task_description="test",
            dry_run=True,
        )

        skill._execute_fallback = MagicMock(return_value=False)

        success = skill.execute(max_retries=2)
        assert success is False
        assert skill._execute_fallback.call_count == 2

    def test_succeeds_first_try(self):
        """Motor skill returns True immediately on first success."""
        from src.skills.motor import MotorSkill

        skill = MotorSkill(
            name="test_skill",
            policy_path="test/policy",
            duration=5,
            task_description="test",
            dry_run=True,
        )

        skill._execute_fallback = MagicMock(return_value=True)

        success = skill.execute(max_retries=3)
        assert success is True
        assert skill._execute_fallback.call_count == 1


class TestFolderImageSource(unittest.TestCase):
    """Test FolderImageSource for dry-run mode."""

    def test_loads_images_from_folder(self):
        """FolderImageSource finds and serves images in sorted order."""
        from src.pipeline.camera import FolderImageSource
        import os

        test_dir = os.path.join(os.path.dirname(__file__), "..", "test_data")
        if not os.path.isdir(test_dir):
            self.skipTest("test_data directory not found")

        source = FolderImageSource(test_dir)
        source.start()

        assert source.is_open()
        frame = source.grab()
        assert isinstance(frame, bytes)
        assert len(frame) > 0

        source.stop()

    def test_clamps_to_last_image(self):
        """After exhausting images, FolderImageSource returns the last one."""
        from src.pipeline.camera import FolderImageSource
        import os

        test_dir = os.path.join(os.path.dirname(__file__), "..", "test_data")
        if not os.path.isdir(test_dir):
            self.skipTest("test_data directory not found")

        source = FolderImageSource(test_dir)
        source.start()

        # Grab way more than available
        frames = []
        for _ in range(50):
            frames.append(source.grab())

        # Last several should all be the same (last image)
        assert frames[-1] == frames[-2]

        source.stop()


class TestFrameHash(unittest.TestCase):
    """Test frame hashing for same-page detection."""

    def test_same_bytes_same_hash(self):
        from src.pipeline.camera import frame_hash
        a = frame_hash(b"identical content")
        b = frame_hash(b"identical content")
        assert a == b

    def test_different_bytes_different_hash(self):
        from src.pipeline.camera import frame_hash
        a = frame_hash(b"page one content")
        b = frame_hash(b"page two content")
        assert a != b


class TestStartupValidation(unittest.TestCase):
    """Test that validate_config catches missing env vars."""

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "", "ELEVENLABS_API_KEY": ""})
    def test_missing_anthropic_key_exits(self):
        # Need to reimport to pick up patched env
        import importlib
        import src.config
        importlib.reload(src.config)
        from src.config import validate_config

        with self.assertRaises(SystemExit):
            validate_config(silent=False, dry_run=False)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key", "ELEVENLABS_API_KEY": ""})
    def test_silent_mode_skips_elevenlabs_check(self):
        import importlib
        import src.config
        importlib.reload(src.config)
        from src.config import validate_config

        # Should not raise
        validate_config(silent=True, dry_run=False)


if __name__ == "__main__":
    unittest.main()
