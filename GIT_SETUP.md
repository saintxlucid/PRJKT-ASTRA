# Git Setup and Initial Commits

## Step 1: Initialize Repository
```powershell
git init
```

## Step 2: Stage Documentation Changes
```powershell
git add docs/
git commit -m "docs: add comprehensive documentation system

- Add architecture overview
- Add API reference documentation
- Add getting started guides
- Add testing documentation"
```

## Step 3: Stage Project Structure
```powershell
git add src/ tests/ config/
git commit -m "chore: reorganize project structure

- Create proper directory organization
- Set up testing infrastructure
- Add configuration management
- Implement test automation"
```

## Step 4: Stage Examples
```powershell
git add evolution/gguf/examples/
git commit -m "feat: add example notebooks

- Add LoRA merging examples
- Add RoPE tuning examples
- Add schema enforcement examples
- Include test data and fixtures"
```

## Step 5: Stage Core Files
```powershell
git add .
git commit -m "feat: initial project setup

- Add project configuration
- Set up development tooling
- Add quality assurance tools
- Configure CI/CD pipeline"
```

## Step 6: Tag Initial Release
```powershell
git tag -a v2.0.0 -m "Initial release v2.0.0"
```