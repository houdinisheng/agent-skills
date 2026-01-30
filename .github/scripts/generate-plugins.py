#!/usr/bin/env python3
"""
Generate plugins/ directory from skills/ source.

This script:
1. Clears the plugins/ directory
2. For each skill in skills/:
   - Creates plugin directory structure
   - Copies skill files into plugins/{name}/skills/
   - Generates .claude-plugin/plugin.json
   - Generates README.md
3. Generates root .claude-plugin/marketplace.json
"""

import json
import shutil
import subprocess
import re
from pathlib import Path

import yaml


def get_skill_timestamp(skill_path: Path) -> int:
    """Get Unix timestamp of last git commit that modified this skill."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%ct", "--", str(skill_path)],
        capture_output=True,
        text=True
    )
    if result.returncode == 0 and result.stdout.strip():
        return int(result.stdout.strip())
    # Fallback to current time if no git history
    import time
    return int(time.time())


def extract_frontmatter(skill_md_path: Path) -> dict:
    """Extract YAML frontmatter from SKILL.md."""
    content = skill_md_path.read_text()
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if match:
        return yaml.safe_load(match.group(1)) or {}
    return {}


def generate_plugin_json(name: str, description: str, version: str) -> dict:
    """Generate plugin.json manifest."""
    return {
        "name": name,
        "version": version,
        "description": description,
        "author": {
            "name": "Eleanor Berger",
            "url": "https://intellectronica.net"
        },
        "repository": "https://github.com/intellectronica/agent-skills",
        "homepage": f"https://github.com/intellectronica/agent-skills/tree/main/plugins/{name}",
        "license": "MIT"
    }


# Category mapping based on skill characteristics
SKILL_CATEGORIES = {
    "anki-connect": "integrations",
    "notion-api": "integrations",
    "raindrop-api": "integrations",
    "todoist-api": "integrations",
    "gog-cli": "integrations",
    "context7": "development",
    "copilot-sdk": "development",
    "mgrep-code-search": "development",
    "here-be-git": "development",
    "gpt-image-1-5": "media",
    "nano-banana-pro": "media",
    "beautiful-mermaid": "productivity",
    "lorem-ipsum": "productivity",
    "promptify": "productivity",
    "markdown-converter": "productivity",
    "ray-so-code-snippet": "productivity",
    "tavily": "productivity",
    "ultrathink": "productivity",
    "youtube-transcript": "productivity",
}


def get_category(name: str) -> str:
    """Get category for a skill, defaulting to 'productivity'."""
    return SKILL_CATEGORIES.get(name, "productivity")


def generate_readme(name: str, description: str) -> str:
    """Generate plugin README.md."""
    return f"""# {name}

{description}

## Installation

### Claude Code / Cowork

```bash
claude plugin marketplace add intellectronica/agent-skills
claude plugin install {name}@intellectronica-skills
```

### npx skills

```bash
npx skills add intellectronica/agent-skills --skill {name}
```

---

> This plugin is auto-generated from [skills/{name}](../../skills/{name}).
"""


def copy_skill_to_plugin(skill_path: Path, plugin_path: Path):
    """Copy skill contents into plugin structure."""
    plugin_skills_dir = plugin_path / "skills"
    plugin_skills_dir.mkdir(parents=True, exist_ok=True)

    for item in skill_path.iterdir():
        dest = plugin_skills_dir / item.name if item.name in ["SKILL.md", "references"] else plugin_path / item.name

        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)


def main():
    skills_dir = Path("skills")
    plugins_dir = Path("plugins")

    # Clear plugins directory
    if plugins_dir.exists():
        shutil.rmtree(plugins_dir)
    plugins_dir.mkdir()

    marketplace_plugins = []

    for skill_path in sorted(skills_dir.iterdir()):
        if not skill_path.is_dir() or skill_path.name.startswith("."):
            continue

        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            continue

        # Extract metadata
        frontmatter = extract_frontmatter(skill_md)
        name = frontmatter.get("name", skill_path.name)
        description = frontmatter.get("description", "").strip()

        if not description:
            print(f"Warning: {name} has no description")
            description = f"Agent skill: {name}"

        # Get version from git timestamp
        timestamp = get_skill_timestamp(skill_path)
        version = f"0.1.{timestamp}"

        # Create plugin directory
        plugin_path = plugins_dir / name
        plugin_path.mkdir()

        # Copy skill files
        copy_skill_to_plugin(skill_path, plugin_path)

        # Generate plugin.json
        plugin_json_dir = plugin_path / ".claude-plugin"
        plugin_json_dir.mkdir()
        plugin_json = generate_plugin_json(name, description, version)
        (plugin_json_dir / "plugin.json").write_text(
            json.dumps(plugin_json, indent=2) + "\n"
        )

        # Generate README
        readme = generate_readme(name, description)
        (plugin_path / "README.md").write_text(readme)

        # Add to marketplace
        marketplace_plugins.append({
            "name": name,
            "source": f"./plugins/{name}",
            "description": description,
            "version": version,
            "category": get_category(name)
        })

        print(f"Generated plugin: {name}")

    # Generate marketplace.json
    marketplace = {
        "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
        "name": "intellectronica-skills",
        "description": "A curated collection of agent skills for Claude Code and Cowork",
        "owner": {
            "name": "Eleanor Berger",
            "url": "https://intellectronica.net"
        },
        "plugins": marketplace_plugins
    }

    marketplace_dir = Path(".claude-plugin")
    marketplace_dir.mkdir(exist_ok=True)
    (marketplace_dir / "marketplace.json").write_text(
        json.dumps(marketplace, indent=2) + "\n"
    )

    print(f"\nGenerated {len(marketplace_plugins)} plugins")
    print("Generated .claude-plugin/marketplace.json")


if __name__ == "__main__":
    main()
