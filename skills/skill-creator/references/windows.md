# Windows Notes for Skill Creation Commands

Use these PowerShell equivalents for the Unix shell examples in this skill.

## Create a Skill Directory

```powershell
New-Item -ItemType Directory -Force skill-name\references,skill-name\scripts,skill-name\assets | Out-Null
New-Item -ItemType File -Force skill-name\SKILL.md | Out-Null
```

## Run Helper Scripts

Use `python` if `python3` is not available:

```powershell
python scripts\init_skill.py <skill-name> --path <output-directory>
python scripts\quick_validate.py <path\to\skill-folder>
```

## Search and Extract Text

PowerShell alternatives for common Unix text tools:

```powershell
Select-String -Path SKILL.md -Pattern "^name:"
Get-Content SKILL.md | Select-Object -First 20
```

If a repository already provides `rg`, prefer it for recursive searches because it works well on Windows too.
