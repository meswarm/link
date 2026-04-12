"""Skills 加载器 — 加载和管理 Agent 的技能知识"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """一个技能的完整数据"""

    name: str
    description: str
    content: str  # SKILL.md 正文（不含 frontmatter）
    path: Path  # 技能目录路径
    references: dict[str, str] = field(default_factory=dict)  # name -> content
    assets: dict[str, str] = field(default_factory=dict)  # name -> content


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """解析 SKILL.md 的 YAML frontmatter 和正文

    Returns:
        (frontmatter_dict, body_text)
    """
    # 匹配 --- ... --- 格式的 YAML frontmatter
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not match:
        return {}, text

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        frontmatter = {}

    body = match.group(2)
    return frontmatter, body


def _load_dir_files(dir_path: Path) -> dict[str, str]:
    """加载目录下所有 Markdown 文件"""
    files = {}
    if not dir_path.exists():
        return files

    for file_path in sorted(dir_path.iterdir()):
        if file_path.is_file() and file_path.suffix in (".md", ".txt", ".yaml", ".yml"):
            try:
                content = file_path.read_text(encoding="utf-8")
                files[file_path.name] = content
            except Exception as e:
                logger.warning(f"读取文件失败 {file_path}: {e}")

    return files


def load_skill(skill_dir: Path) -> Skill | None:
    """从目录加载一个技能

    Args:
        skill_dir: 技能目录路径，包含 SKILL.md

    Returns:
        Skill 实例，如果加载失败返回 None
    """
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        logger.warning(f"技能目录缺少 SKILL.md: {skill_dir}")
        return None

    try:
        raw_text = skill_file.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"读取技能文件失败 {skill_file}: {e}")
        return None

    frontmatter, body = _parse_frontmatter(raw_text)

    name = frontmatter.get("name", skill_dir.name)
    description = frontmatter.get("description", "").strip()

    if not description:
        logger.warning(f"技能 '{name}' 没有 description")

    # 加载 references 和 assets
    references = _load_dir_files(skill_dir / "references")
    assets = _load_dir_files(skill_dir / "assets")

    skill = Skill(
        name=name,
        description=description,
        content=body.strip(),
        path=skill_dir,
        references=references,
        assets=assets,
    )

    logger.info(
        f"已加载技能: {name}"
        f" (references: {len(references)}, assets: {len(assets)})"
    )
    return skill


def load_skills_from_dir(skills_dir: str | Path) -> list[Skill]:
    """从目录加载所有技能

    遍历 skills_dir 下的每个子目录，查找包含 SKILL.md 的目录。

    Args:
        skills_dir: 技能根目录

    Returns:
        加载的技能列表
    """
    path = Path(skills_dir)
    if not path.exists():
        logger.info(f"技能目录不存在，跳过: {path}")
        return []

    if not path.is_dir():
        logger.error(f"技能路径不是目录: {path}")
        return []

    skills = []
    for item in sorted(path.iterdir()):
        if item.is_dir() and (item / "SKILL.md").exists():
            skill = load_skill(item)
            if skill:
                skills.append(skill)

    logger.info(f"共加载 {len(skills)} 个技能: {[s.name for s in skills]}")
    return skills


def format_skills_for_prompt(skills: list[Skill]) -> str:
    """将技能格式化为可注入 system prompt 的文本

    结构：
    - 技能概览（名称 + 描述）
    - 每个技能的详细指令
    - 引用资料（如果有）

    Args:
        skills: 技能列表

    Returns:
        格式化后的 prompt 文本
    """
    if not skills:
        return ""

    parts = []
    parts.append("# 你的技能\n")
    parts.append("你有以下技能，请根据用户的需求灵活运用：\n")

    # 技能概览
    for skill in skills:
        parts.append(f"- **{skill.name}**: {skill.description}")
    parts.append("")

    # 每个技能的详细内容
    for skill in skills:
        parts.append(f"---\n")
        parts.append(f"## 技能: {skill.name}\n")
        parts.append(skill.content)
        parts.append("")

        # 附加引用资料
        if skill.references:
            parts.append(f"### 参考资料\n")
            for ref_name, ref_content in skill.references.items():
                parts.append(f"#### {ref_name}\n")
                parts.append(ref_content)
                parts.append("")

    return "\n".join(parts)
