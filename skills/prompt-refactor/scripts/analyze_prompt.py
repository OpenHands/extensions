#!/usr/bin/env python3
"""
Analyze a prompt and identify components that can be factored into skills.

This script helps decompose monolithic prompts into modular, reusable skills.
"""

import re
from pathlib import Path
from typing import Dict, List


def identify_phases(prompt_text: str) -> List[Dict[str, str]]:
    """
    Identify distinct phases or sections in a prompt.
    
    Returns a list of dicts with 'title', 'content', and 'type' keys.
    """
    phases = []
    
    # Pattern 1: Numbered phases (e.g., "Phase 1. READING:")
    phase_pattern = r'(?:Phase|Step)\s+(\d+)\.\s+([A-Z\s]+):(.*?)(?=(?:Phase|Step)\s+\d+\.|$)'
    matches = re.finditer(phase_pattern, prompt_text, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        phase_num = match.group(1)
        phase_name = match.group(2).strip()
        phase_content = match.group(3).strip()
        
        phases.append({
            'title': f"{phase_name}",
            'number': phase_num,
            'content': phase_content,
            'type': 'phase'
        })
    
    # Pattern 2: Section headers (e.g., "## Section Title")
    if not phases:
        section_pattern = r'#{1,3}\s+(.+?)(?:\n|$)(.*?)(?=#{1,3}\s+|$)'
        matches = re.finditer(section_pattern, prompt_text, re.DOTALL)
        
        for match in matches:
            section_title = match.group(1).strip()
            section_content = match.group(2).strip()
            
            if section_content:
                phases.append({
                    'title': section_title,
                    'content': section_content,
                    'type': 'section'
                })
    
    return phases


def identify_workflows(phases: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Group related phases into cohesive workflows.
    
    A workflow is a set of related steps that accomplish a higher-level goal.
    """
    workflows = []
    
    # Simple heuristic: each phase is a workflow step
    # In more complex cases, you might group phases by semantic similarity
    
    current_workflow = {
        'name': 'main_workflow',
        'steps': phases
    }
    workflows.append(current_workflow)
    
    return workflows


def suggest_skills(phases: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Suggest skills based on identified phases and their characteristics.
    """
    skills = []
    
    for phase in phases:
        title = phase['title']
        content = phase['content']
        
        # Determine skill type based on phase name and content
        skill_type = 'workflow'
        reusability = 'high'
        
        # Keywords that suggest different skill types
        if any(kw in title.lower() for kw in ['test', 'testing', 'verification']):
            skill_type = 'testing'
        elif any(kw in title.lower() for kw in ['read', 'analysis', 'exploration', 'understand']):
            skill_type = 'analysis'
        elif any(kw in title.lower() for kw in ['fix', 'implement', 'edit', 'modify']):
            skill_type = 'implementation'
        elif any(kw in title.lower() for kw in ['review', 'validate', 'check']):
            skill_type = 'validation'
        
        skills.append({
            'phase_title': title,
            'suggested_skill_name': title.lower().replace(' ', '-'),
            'skill_type': skill_type,
            'reusability': reusability,
            'phase_content': content[:200] + '...' if len(content) > 200 else content
        })
    
    return skills


def analyze_prompt(prompt_path: str) -> Dict:
    """
    Main analysis function that processes a prompt file.
    """
    prompt_text = Path(prompt_path).read_text()
    
    # Step 1: Identify phases/sections
    phases = identify_phases(prompt_text)
    
    # Step 2: Identify workflows
    workflows = identify_workflows(phases)
    
    # Step 3: Suggest skills
    suggested_skills = suggest_skills(phases)
    
    return {
        'phases': phases,
        'workflows': workflows,
        'suggested_skills': suggested_skills,
        'original_length': len(prompt_text),
        'num_phases': len(phases)
    }


def print_analysis(analysis: Dict) -> None:
    """
    Pretty print the analysis results.
    """
    print("=" * 80)
    print("PROMPT ANALYSIS RESULTS")
    print("=" * 80)
    print(f"\nOriginal prompt length: {analysis['original_length']} characters")
    print(f"Number of phases identified: {analysis['num_phases']}")
    
    print("\n" + "-" * 80)
    print("IDENTIFIED PHASES:")
    print("-" * 80)
    for i, phase in enumerate(analysis['phases'], 1):
        print(f"\n{i}. {phase['title']}")
        print(f"   Type: {phase['type']}")
        if 'number' in phase:
            print(f"   Phase number: {phase['number']}")
    
    print("\n" + "-" * 80)
    print("SUGGESTED SKILLS:")
    print("-" * 80)
    for i, skill in enumerate(analysis['suggested_skills'], 1):
        print(f"\n{i}. Skill: {skill['suggested_skill_name']}")
        print(f"   Original phase: {skill['phase_title']}")
        print(f"   Type: {skill['skill_type']}")
        print(f"   Reusability: {skill['reusability']}")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python analyze_prompt.py <path_to_prompt_file>")
        sys.exit(1)
    
    prompt_path = sys.argv[1]
    
    if not Path(prompt_path).exists():
        print(f"Error: File not found: {prompt_path}")
        sys.exit(1)
    
    analysis = analyze_prompt(prompt_path)
    print_analysis(analysis)
