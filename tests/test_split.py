"""Run with python -m unittest discover -s tests in an AstrBot environment."""

import unittest
from types import SimpleNamespace

from astrbot.api.message_components import Plain

from core.config import SplitConfig
from core.step.split import SplitStep


OTHER_LINE_ENDINGS = ("\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029")


class SplitNewlineTests(unittest.TestCase):
    def make_splitter(self, char_list=None, max_count=5):
        cfg = SplitConfig(
            {
                "max_length": 600,
                "max_count": max_count,
                "char_list": (
                    char_list if char_list is not None else ["。", "？", r"\s", r"\n"]
                ),
                "per_char_delay": 0,
                "delay_scope_str": "0~0",
                "show_typing": False,
                "tail_punc": [],
            }
        )
        return SplitStep(SimpleNamespace(split=cfg, context=None))

    def split_text(self, text, **kwargs):
        splitter = self.make_splitter(**kwargs)
        segments = splitter._split_chain([Plain(text)])
        for segment in segments:
            segment.strip_plain()
        return [segment.text for segment in segments if not segment.is_empty]

    def test_reply_separated_only_by_blank_line(self):
        self.assertEqual(
            self.split_text("第一句没有标点\n\n第二句也没有标点"),
            ["第一句没有标点", "第二句也没有标点"],
        )

    def test_literal_and_escaped_newline_configuration(self):
        for char_list in ([r"\n"], ["\n"], [r"\s"]):
            for separator in ("\n", "\n\n", "\r\n", " \n\t\n "):
                with self.subTest(char_list=char_list, separator=separator):
                    self.assertEqual(
                        self.split_text("第一句" + separator + "第二句", char_list=char_list),
                        ["第一句", "第二句"],
                    )

    def test_newline_is_preserved_when_not_configured(self):
        self.assertEqual(
            self.split_text("第一句\n\n第二句", char_list=["。", "？"]),
            ["第一句\n\n第二句"],
        )

    def test_other_line_endings_are_respected_when_configured(self):
        for separator in OTHER_LINE_ENDINGS:
            for char_list in ([r"\s"], [separator]):
                with self.subTest(separator=separator, char_list=char_list):
                    self.assertEqual(
                        self.split_text("第一句" + separator + "第二句", char_list=char_list),
                        ["第一句", "第二句"],
                    )

    def test_other_line_endings_are_preserved_when_not_configured(self):
        for separator in OTHER_LINE_ENDINGS:
            for char_list in (["。", "？"], [r"\n"]):
                text = "第一句" + separator + "第二句"
                with self.subTest(separator=separator, char_list=char_list):
                    self.assertEqual(self.split_text(text, char_list=char_list), [text])

    def test_other_line_endings_do_not_create_empty_tokens(self):
        for separator in OTHER_LINE_ENDINGS:
            text = separator * 2 + "第一句" + separator * 2 + "第二句" + separator * 2
            with self.subTest(separator=separator):
                splitter = self.make_splitter()
                tokens = list(splitter.tokenizer.tokenize(text))
                self.assertTrue(all(token.text.strip() for token in tokens))
                self.assertEqual(self.split_text(text), ["第一句", "第二句"])
                tokens = list(splitter.tokenizer.tokenize(separator * 2))
                self.assertFalse(any(token.is_split for token in tokens))

    def test_other_line_endings_inside_quotes_are_protected(self):
        for separator in OTHER_LINE_ENDINGS:
            text = "“第一句" + separator + "第二句”"
            with self.subTest(separator=separator):
                self.assertEqual(self.split_text(text), [text])
                self.assertEqual(self.split_text(text + separator + "第三句"), [text, "第三句"])

    def test_horizontal_whitespace_does_not_create_split_points(self):
        for text in (
            "hello world",
            "第一句 第二句",
            "第一句\t第二句",
            "第一句\u00a0第二句",
            "第一句\u3000第二句",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.split_text(text), [text])

    def test_leading_and_trailing_blank_lines_do_not_create_empty_tokens(self):
        text = "\n \n第一句\n\n第二句\n\n"
        splitter = self.make_splitter()
        tokens = list(splitter.tokenizer.tokenize(text))
        self.assertTrue(all(token.text.strip() for token in tokens))
        self.assertEqual(self.split_text(text), ["第一句", "第二句"])

    def test_whitespace_only_text_does_not_create_split_points(self):
        splitter = self.make_splitter()
        tokens = list(splitter.tokenizer.tokenize("\n \n\t\n"))
        self.assertFalse(any(token.is_split for token in tokens))
        self.assertEqual(self.split_text("\n \n\t\n"), [])

    def test_newlines_inside_quotes_and_brackets_are_protected(self):
        for text in (
            "“第一句\n第二句”",
            '"first\nsecond"',
            "（第一句\n第二句）",
            "[第一句\n第二句]",
            "`first\nsecond`",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.split_text(text), [text])
                self.assertEqual(self.split_text(text + "\n第三句"), [text, "第三句"])

    def test_kaomoji_are_preserved(self):
        self.assertEqual(self.split_text("（＾▽＾）\n你好"), ["（＾▽＾）", "你好"])

    def test_punctuation_separators_still_split(self):
        self.assertEqual(self.split_text("第一句。\n第二句？第三句"), ["第一句。", "第二句？", "第三句"])

    def test_maximum_segment_count_is_respected(self):
        text = "第一句\n第二句\n第三句\n第四句"
        for max_count in (1, 2):
            with self.subTest(max_count=max_count):
                segments = self.split_text(text, max_count=max_count)
                self.assertEqual(len(segments), max_count)
                self.assertEqual("".join(segments).replace("\n", ""), text.replace("\n", ""))


if __name__ == "__main__":
    unittest.main()
