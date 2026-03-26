# CI/CD Setup Guide for ClinicalMind

This guide walks you through setting up automated CI/CD pipelines for your ClinicalMind project.

## Overview

ClinicalMind uses GitHub Actions for continuous integration and deployment:

- **CI Pipeline** (`.github/workflows/ci.yml`): Runs on every push and pull request
- **CD Pipeline** (`.github/workflows/cd.yml`): Deploys on pushes to main branch

## Quick Start

### 1. Push Your Code to GitHub

```bash
cd /home/jeswin/Downloads/RAG_Chatbot/ClinicalMind

git init
git add .
git commit -m "Initial commit with CI/CD"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ClinicalMind.git
git push -u origin main
```

### 2. Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `ClinicalMind`
3. Choose Public or Private
4. Do NOT initialize with README
5. Click "Create repository"

### 3. Configure GitHub Secrets

Go to your repository: `Settings > Secrets and variables > Actions`

#### Required Secrets

| Secret Name | Value | How to Get |
|-------------|-------|------------|
| `GROQ_API_KEY` | Your Groq API key | https://console.groq.com/keys |

#### Optional Secrets (for CD)

| Secret Name | Value | How to Get |
|-------------|-------|------------|
| `DOCKER_USERNAME` | Your Docker Hub username | https://hub.docker.com/ |
| `DOCKER_PASSWORD` | Docker Hub access token | Docker Hub > Account Settings > Security |

### 4. Verify Pipeline

After pushing, go to the **Actions** tab in your GitHub repository:

- You should see "CI Pipeline" running
- Click on the workflow to view detailed logs
- Green checkmark = success, Red X = failure

## CI Pipeline Details

### What It Does

1. **Backend Tests**
   - Installs Python dependencies
   - Runs flake8 for linting
   - Runs Black for code formatting check
   - Runs mypy for type checking
   - Runs pytest for unit tests
   - Uploads coverage report

2. **Frontend Tests**
   - Installs Node.js dependencies
   - Runs ESLint for linting
   - Runs TypeScript compiler check
   - Builds the Next.js application
   - Runs frontend tests

3. **Security Scan**
   - Runs Bandit for Python security
   - Runs pip-audit for dependency vulnerabilities
   - Runs safety check for known vulnerabilities

4. **Docker Build**
   - Builds backend Docker image
   - Builds frontend Docker image
   - Validates docker-compose configuration

### Expected Duration

- First run: 5-10 minutes (downloads dependencies)
- Subsequent runs: 2-5 minutes (cached dependencies)

## CD Pipeline Details

### What It Does

1. Builds production Docker images
2. Pushes images to Docker Hub
3. Creates deployment manifest
4. Uploads deployment artifacts

### When It Runs

- Automatically on every push to `main` branch
- Can be triggered manually from Actions tab

## Local Development

### Install Pre-commit Hooks

Pre-commit hooks run checks before you commit code locally:

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Run on all files (optional)
pre-commit run --all-files
```

Now every `git commit` will automatically:
- Check for trailing whitespace
- Validate YAML/JSON files
- Run Black formatting
- Run flake8 linting
- Check for large files
- Detect private keys

### Run Tests Locally

```bash
# Backend tests
pytest tests/ -v

# Backend tests with coverage
pytest tests/ -v --cov=backend --cov=src

# Frontend build
cd frontend && npm run build

# Lint backend
flake8 backend/ src/

# Format backend
black backend/ src/
```

## Troubleshooting

### Pipeline Fails on First Run

**Issue**: Tests fail because of missing API key

**Solution**: 
1. Add `GROQ_API_KEY` to GitHub Secrets
2. Re-run the workflow

**Issue**: Docker build fails

**Solution**:
1. Check Dockerfile paths are correct
2. Ensure all files referenced in Dockerfile exist
3. Run `docker-compose config` locally to validate

### Pipeline Takes Too Long

**Solutions**:
1. Use caching (already configured)
2. Reduce test scope for PR checks
3. Split large test suites

### Security Scan Finds Vulnerabilities

**Actions**:
1. Review the vulnerability report in workflow logs
2. Update vulnerable packages: `pip install --upgrade package-name`
3. Re-run pipeline

## Badges

Add these badges to your README to show CI/CD status:

```markdown
![CI Pipeline](https://github.com/YOUR_USERNAME/ClinicalMind/actions/workflows/ci.yml/badge.svg)
![CD Pipeline](https://github.com/YOUR_USERNAME/ClinicalMind/actions/workflows/cd.yml/badge.svg)
```

Replace `YOUR_USERNAME` with your GitHub username.

## Advanced Configuration

### Skip CI for Certain Commits

Add `[skip ci]` to your commit message:

```bash
git commit -m "Update docs [skip ci]"
```

### Run CI on Specific Branches

Edit `.github/workflows/ci.yml`:

```yaml
on:
  push:
    branches: [main, develop, 'feature/*']
```

### Add Email Notifications

Edit workflows to include:

```yaml
jobs:
  notify:
    runs-on: ubuntu-latest
    if: failure()
    steps:
      - name: Send email
        uses: dawidd6/action-send-mail@v3
        with:
          to: your-email@example.com
          subject: CI Pipeline Failed
          body: Check ${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions
```

## Best Practices

1. **Keep tests fast**: Aim for < 10 minute CI runs
2. **Fix broken builds immediately**: Don't let main stay broken
3. **Review PR checks**: Don't merge if CI fails
4. **Monitor dependencies**: Regularly update packages
5. **Use branches**: Feature branches isolate changes
6. **Write meaningful commits**: Clear commit messages help debugging

## Next Steps

1. Set up code coverage reporting (Codecov)
2. Add automated deployment to cloud (AWS, GCP, Azure)
3. Configure staging environment
4. Add performance testing
5. Set up monitoring alerts

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions)
- [Pre-commit Framework](https://pre-commit.com/)
- [Docker Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

## Support

For CI/CD issues:
1. Check workflow logs in Actions tab
2. Run tests locally first
3. Review GitHub Actions documentation
4. Create an issue in your repository

---

**Last Updated**: 2024
**Maintained By**: ClinicalMind Team
