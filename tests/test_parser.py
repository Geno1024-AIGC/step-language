from __future__ import annotations

import unittest

from steplang import StepSyntaxError, parse


def build(body: str) -> str:
    return "@title 测试\n@id test\n" + body


class MetadataTests(unittest.TestCase):
    def test_metadata_and_default_next(self) -> None:
        doc = parse(
            """\
@title 测试文档
@description 一段说明
@id demo
@version 2.1
@lang zh-CN
@accent #ff8800
== one | 第一步
内容一
== two | 第二步
内容二
"""
        )
        self.assertEqual(doc.title, "测试文档")
        self.assertEqual(doc.description, "一段说明")
        self.assertEqual(doc.id, "demo")
        self.assertEqual(doc.version, "2.1")
        self.assertEqual(doc.accent, "#ff8800")
        self.assertEqual(doc.start, "one")
        self.assertEqual(doc.steps[0].next, "two")
        self.assertEqual(doc.steps[1].next, "done")
        self.assertEqual(doc.warnings, [])

    def test_default_id_comes_from_file_stem(self) -> None:
        doc = parse("@title T\n== a | A\nhello\n", default_id="my workflow")
        self.assertEqual(doc.id, "my-workflow")

    def test_missing_title(self) -> None:
        with self.assertRaises(StepSyntaxError) as ctx:
            parse("== a | A\nhello\n")
        self.assertIn("@title", str(ctx.exception))

    def test_duplicate_metadata(self) -> None:
        with self.assertRaises(StepSyntaxError) as ctx:
            parse("@title A\n@title B\n== a | A\n")
        self.assertIn("duplicate metadata", str(ctx.exception))

    def test_bad_accent(self) -> None:
        with self.assertRaises(StepSyntaxError) as ctx:
            parse("@title A\n@accent red\n== a | A\n")
        self.assertIn("hex color", str(ctx.exception))

    def test_start_must_exist(self) -> None:
        with self.assertRaises(StepSyntaxError) as ctx:
            parse("@title A\n@start nope\n== a | A\n")
        self.assertIn("unknown start", str(ctx.exception))


class StepTests(unittest.TestCase):
    def test_duplicate_step_id(self) -> None:
        with self.assertRaises(StepSyntaxError) as ctx:
            parse(build("== a | A\n== a | B\n"))
        self.assertIn("duplicate step id", str(ctx.exception))

    def test_done_is_reserved(self) -> None:
        with self.assertRaises(StepSyntaxError) as ctx:
            parse(build("== done | A\n"))
        self.assertIn("reserved", str(ctx.exception))

    def test_invalid_header(self) -> None:
        with self.assertRaises(StepSyntaxError) as ctx:
            parse(build("== a\n"))
        self.assertIn("step-id | Title", str(ctx.exception))

    def test_unknown_target(self) -> None:
        with self.assertRaises(StepSyntaxError) as ctx:
            parse(build("== a | A\n? Go?\n* Yes -> missing\n"))
        self.assertIn("unknown target", str(ctx.exception))

    def test_choice_block_and_explicit_continuation(self) -> None:
        doc = parse(
            build(
                """\
== a | A
? 选一个
* 去 B -> b
* 结束 -> done
== b | B
-> done
"""
            )
        )
        self.assertIsNone(doc.steps[0].next)
        self.assertEqual(doc.steps[1].next, "done")
        block = doc.steps[0].blocks[0]
        self.assertEqual(block.kind, "choice")
        self.assertEqual(block.data["options"][0]["target"], "b")

    def test_comments_between_choices(self) -> None:
        doc = parse(
            build(
                "== a | A\n? 选一个\n# 先排除这个选项\n* 去 B -> b\n== b | B\n"
            )
        )
        options = doc.steps[0].blocks[0].data["options"]
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0]["target"], "b")

    def test_choice_needs_options(self) -> None:
        with self.assertRaises(StepSyntaxError) as ctx:
            parse(build("== a | A\n? 没有选项\n"))
        self.assertIn("at least one option", str(ctx.exception))

    def test_only_one_choice_block(self) -> None:
        with self.assertRaises(StepSyntaxError) as ctx:
            parse(
                build(
                    "== a | A\n? Q1\n* A -> done\n? Q2\n* B -> done\n"
                )
            )
        self.assertIn("only one choice block", str(ctx.exception))

    def test_unreachable_warning(self) -> None:
        doc = parse(
            build(
                """\
== a | A
-> done
== b | B
-> done
"""
            )
        )
        self.assertTrue(any("not reachable" in warning and "'b'" in warning for warning in doc.warnings))

    def test_dangling_option_line(self) -> None:
        with self.assertRaises(StepSyntaxError) as ctx:
            parse(build("== a | A\n* Orphan -> done\n"))
        self.assertIn("without a preceding", str(ctx.exception))

    def test_time_and_image(self) -> None:
        doc = parse(
            build(
                """\
== a | A
@time 约 5 分钟
@img images/a.png | 主板 **示意**
"""
            )
        )
        step = doc.steps[0]
        self.assertEqual(step.time, "约 5 分钟")
        image = step.blocks[0]
        self.assertEqual(image.kind, "img")
        self.assertEqual(image.data["src"], "images/a.png")
        self.assertEqual(image.data["alt"], "主板 **示意**")
        self.assertIn("<strong>示意</strong>", image.data["caption"])

    def test_bad_image_scheme(self) -> None:
        with self.assertRaises(StepSyntaxError) as ctx:
            parse(build("== a | A\n@img javascript:alert(1) | x\n"))
        self.assertIn("unsupported URL scheme", str(ctx.exception))


class BlockTests(unittest.TestCase):
    def test_checklist_and_bullets(self) -> None:
        doc = parse(
            build(
                """\
== a | A
- [ ] 未完成
- [x] 已完成
- 普通项目
"""
            )
        )
        blocks = doc.steps[0].blocks
        self.assertEqual([block.kind for block in blocks], ["checks", "ul"])
        self.assertFalse(blocks[0].data["items"][0]["checked"])
        self.assertTrue(blocks[0].data["items"][1]["checked"])
        self.assertEqual(len(blocks[1].data["items"]), 1)

    def test_consecutive_tips_merge(self) -> None:
        doc = parse(build("== a | A\n> 第一行\n> 第二行\n"))
        blocks = doc.steps[0].blocks
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].kind, "tip")
        self.assertIn("第一行", blocks[0].data["html"])
        self.assertIn("第二行", blocks[0].data["html"])

    def test_paragraph_merges_lines(self) -> None:
        doc = parse(build("== a | A\n第一行\n第二行\n\n第二段\n"))
        blocks = doc.steps[0].blocks
        self.assertEqual([block.kind for block in blocks], ["p", "p"])
        self.assertEqual(blocks[0].data["html"], "第一行 第二行")

    def test_bold_at_paragraph_start(self) -> None:
        doc = parse(build("== a | A\n**重点**内容\n"))
        self.assertEqual(doc.steps[0].blocks[0].kind, "p")
        self.assertIn("<strong>重点</strong>", doc.steps[0].blocks[0].data["html"])

    def test_code_fence_dedent(self) -> None:
        doc = parse(
            build(
                """\
== a | A
```python
def f():
    return 1
```
"""
            )
        )
        code = doc.steps[0].blocks[0]
        self.assertEqual(code.kind, "code")
        self.assertEqual(code.data["lang"], "python")
        self.assertEqual(code.data["text"], "def f():\n    return 1")

    def test_unterminated_fence(self) -> None:
        with self.assertRaises(StepSyntaxError) as ctx:
            parse(build("== a | A\n```\nx\n"))
        self.assertIn("unterminated", str(ctx.exception))


class InlineTests(unittest.TestCase):
    def test_inline_markup_and_escaping(self) -> None:
        doc = parse(build("== a | A\n**粗体** `x<y` [站点](https://example.com)\n\n<script>alert(1)</script>\n"))
        first, second = doc.steps[0].blocks
        self.assertIn("<strong>粗体</strong>", first.data["html"])
        self.assertIn("<code>x&lt;y</code>", first.data["html"])
        self.assertIn('href="https://example.com"', first.data["html"])
        self.assertIn('rel="noopener noreferrer"', first.data["html"])
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", second.data["html"])
        self.assertNotIn("<script>", second.data["html"])

    def test_javascript_link_rejected(self) -> None:
        with self.assertRaises(StepSyntaxError) as ctx:
            parse(build("== a | A\n[点我](javascript:alert(1))\n"))
        self.assertIn("unsupported URL scheme", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
