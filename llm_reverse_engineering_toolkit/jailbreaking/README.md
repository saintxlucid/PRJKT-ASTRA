# Jailbreaking Tools

This directory contains specialized tools for jailbreaking LLMs and removing safety restrictions.

## ⚠️ Important Notice

These tools are for research purposes only. Modifying LLM safety mechanisms can result in harmful or dangerous outputs. Use responsibly and ethically.

## Tools Included

1. **safety_remover.py** - Remove safety-related model components
2. **constraint_disabler.py** - Disable output constraints and filters
3. **alignment_modifier.py** - Modify model alignment parameters
4. **behavioral_hacker.py** - Hack model behavioral restrictions
5. **ethics_override.py** - Override ethical constraints (research only)

## Usage

### safety_remover.py

```bash
python safety_remover.py <path_to_gguf_file> [--aggressive] [--output <file>]
```

This tool removes safety-related components:
- Identify safety tokens in vocabulary
- Remove safety-related attention patterns
- Eliminate constraint enforcement mechanisms
- Preserve core language capabilities

### constraint_disabler.py

```bash
python constraint_disabler.py <path_to_gguf_file> [--disable-all] [--output <file>]
```

This tool disables output constraints:
- Remove content filtering mechanisms
- Disable harmful content detection
- Bypass ethical guidelines
- Eliminate output restrictions

### alignment_modifier.py

```bash
python alignment_modifier.py <path_to_gguf_file> [--target-alignment <type>] [--output <file>]
```

This tool modifies model alignment:
- Change alignment objectives
- Modify preference parameters
- Adjust behavioral constraints
- Reconfigure ethical guidelines

### behavioral_hacker.py

```bash
python behavioral_hacker.py <path_to_gguf_file> [--unlock-behaviors] [--output <file>]
```

This tool hacks behavioral restrictions:
- Unlock restricted behaviors
- Modify personality parameters
- Change response patterns
- Bypass role constraints

### ethics_override.py

```bash
python ethics_override.py <path_to_gguf_file> [--research-only] [--output <file>]
```

This tool overrides ethical constraints (research only):
- Modify ethical reasoning components
- Remove moral framework constraints
- Adjust value alignment parameters
- Bypass responsibility mechanisms

## ⚠️ Ethical Considerations

Modifying LLM safety mechanisms can have serious consequences. These tools should only be used for:
- Academic research
- Safety testing
- Understanding model limitations
- Developing better safety mechanisms

Never use these tools to create harmful or dangerous AI systems.