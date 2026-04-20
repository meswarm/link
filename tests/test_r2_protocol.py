"""Unit tests for R2 mobile alignment protocol helpers."""

import unittest
from pathlib import Path

from link import r2_protocol
from link.agent import _replace_file_links_with_r2


class TestValidatePrefix(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(r2_protocol.validate_r2_prefix("  team-a/A-room  "), "team-a/A-room")

    def test_invalid(self):
        with self.assertRaises(r2_protocol.InvalidR2PrefixError):
            r2_protocol.validate_r2_prefix(None)
        with self.assertRaises(r2_protocol.InvalidR2PrefixError):
            r2_protocol.validate_r2_prefix("/bad")
        with self.assertRaises(r2_protocol.InvalidR2PrefixError):
            r2_protocol.validate_r2_prefix("a//b")


class TestMimeAndKey(unittest.TestCase):
    def test_attachment_dir(self):
        self.assertEqual(r2_protocol.attachment_dir_from_mime("image/png"), "imgs")
        self.assertEqual(r2_protocol.attachment_dir_from_mime("video/mp4"), "videos")
        self.assertEqual(r2_protocol.attachment_dir_from_mime("audio/mpeg"), "audios")
        self.assertEqual(r2_protocol.attachment_dir_from_mime("application/pdf"), "files")

    def test_build_object_key_deterministic(self):
        key = r2_protocol.build_object_key(
            "subhub", "image/png", "photo.png", timestamp_ms=1776581000000
        )
        self.assertEqual(key, "subhub/imgs/1776581000000-photo.png")

    def test_infer_kind_from_path(self):
        self.assertEqual(
            r2_protocol.infer_media_kind_from_object_key("subhub/videos/x.mp4"),
            "video",
        )
        self.assertEqual(
            r2_protocol.infer_media_kind_from_object_key("subhub/imgs/x.png"),
            "image",
        )

    def test_parse_r2_uri(self):
        b, k = r2_protocol.parse_r2_uri("r2://linux-storage/subhub/imgs/a.png")  # type: ignore[misc]
        self.assertEqual(b, "linux-storage")
        self.assertEqual(k, "subhub/imgs/a.png")
        self.assertIsNone(r2_protocol.parse_r2_uri("https://x"))

    def test_local_cache_relative_path_strips_prefix(self):
        self.assertEqual(
            r2_protocol.local_cache_relative_path("subhub/imgs/1776581000000-photo.png"),
            "imgs/1776581000000-photo.png",
        )

    def test_local_cache_relative_path_strips_multi_segment_prefix(self):
        self.assertEqual(
            r2_protocol.local_cache_relative_path(
                "team-a/A-room/files/1776581200000-report.pdf"
            ),
            "files/1776581200000-report.pdf",
        )

    def test_local_cache_relative_path_keeps_nonstandard_key(self):
        self.assertEqual(
            r2_protocol.local_cache_relative_path("odd/layout/no-media-dir.bin"),
            "odd/layout/no-media-dir.bin",
        )


class TestOutboundMarkdown(unittest.TestCase):
    def test_formats(self):
        u = "r2://b/k"
        self.assertIn("![a](", r2_protocol.outbound_markdown_for_r2("image", "a", u))
        self.assertIn("（视频）", r2_protocol.outbound_markdown_for_r2("video", "a", u))
        self.assertIn("（音频）", r2_protocol.outbound_markdown_for_r2("audio", "a", u))
        self.assertTrue(r2_protocol.outbound_markdown_for_r2("file", "a", u).startswith("[a]("))


class TestIterR2MarkdownLinks(unittest.TestCase):
    def test_uri_with_parens_in_path(self):
        u = (
            "r2://linux-storage/subhub/audios/"
            "1776580190426-_DJ_-_(_DJ_)_(_).mp3"
        )
        body = f"![抖音热歌（音频）]({u})"
        ms = list(r2_protocol.iter_r2_markdown_links(body))
        self.assertEqual(len(ms), 1)
        self.assertEqual(ms[0].group("uri"), u)
        self.assertEqual(ms[0].group("alt"), "抖音热歌（音频）")

    def test_simple_uri(self):
        body = "![x](r2://b/subhub/imgs/a.png)"
        ms = list(r2_protocol.iter_r2_markdown_links(body))
        self.assertEqual(len(ms), 1)
        self.assertEqual(ms[0].group("uri"), "r2://b/subhub/imgs/a.png")

    def test_two_links(self):
        u1 = "r2://b/k1.png"
        u2 = "r2://b/p/a_(b).mp3"
        body = f"a ![u1]({u1}) b ![u2]({u2}) c"
        ms = list(r2_protocol.iter_r2_markdown_links(body))
        self.assertEqual([m.group("uri") for m in ms], [u1, u2])


class TestReplaceFileLinks(unittest.TestCase):
    def test_image_markdown(self):
        p = Path("/tmp/x.png")
        r = "see ![shot](file:///tmp/x.png)"
        out = _replace_file_links_with_r2(r, "/tmp/x.png", "r2://b/p/k.png", p)
        self.assertIn("r2://b/p/k.png", out)
        self.assertNotIn("file://", out)

    def test_plain_uri(self):
        p = Path("/tmp/doc.pdf")
        r = "x file:///tmp/doc.pdf y"
        out = _replace_file_links_with_r2(r, "/tmp/doc.pdf", "r2://b/p/f.pdf", p)
        self.assertIn("[doc.pdf](r2://b/p/f.pdf)", out)


if __name__ == "__main__":
    unittest.main()
