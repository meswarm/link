"""AgentConfig 辅助属性单元测试。"""

import unittest
from pathlib import Path

from link.config import AgentConfig


class TestResolvedMediaCacheRoot(unittest.TestCase):
    def test_default_under_dot_link_cache(self):
        c = AgentConfig()
        self.assertEqual(c.resolved_media_cache_root, Path(".") / ".link_cache" / "media_cache")

    def test_with_work_dir(self):
        c = AgentConfig(work_dir="/tmp/foo")
        self.assertEqual(c.resolved_media_cache_root, Path("/tmp/foo") / "media_cache")

    def test_explicit_media_cache_dir(self):
        c = AgentConfig(media_cache_dir="/var/cache/link-media")
        self.assertEqual(c.resolved_media_cache_root, Path("/var/cache/link-media"))

    def test_pass_r2_images_default_true(self):
        c = AgentConfig()
        self.assertTrue(c.pass_r2_images_to_llm)


if __name__ == "__main__":
    unittest.main()
