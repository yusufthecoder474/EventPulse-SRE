$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'Install GitHub CLI: winget install --id GitHub.cli; then gh auth login --web' }
$login = gh api user --jq .login
if ($LASTEXITCODE -ne 0) { throw 'Run gh auth login --web, then retry.' }
if ($login.Trim() -ne 'yusufthecoder474') { throw "Wrong authenticated account: $login" }
$repo = 'yusufthecoder474/EventPulse-SRE'
$lookup = gh api "repos/$repo" 2>&1 | Out-String
$lookupStatus = $LASTEXITCODE
if ($lookupStatus -eq 0) { throw 'Target repository already exists. Inspect its content before publishing; this script never overwrites an existing repository.' }
if ($lookup -notmatch '404') { throw "Cannot establish that the repository is absent: $lookup" }
python -m ruff check backend/app backend/tests scripts
if ($LASTEXITCODE -ne 0) { throw 'Lint failed.' }
Push-Location backend
python -m pytest -q
$testStatus = $LASTEXITCODE
Pop-Location
if ($testStatus -ne 0) { throw 'Backend tests failed.' }
Push-Location frontend
npm ci
if ($LASTEXITCODE -ne 0) { Pop-Location; throw 'Dependency install failed.' }
npm test
if ($LASTEXITCODE -ne 0) { Pop-Location; throw 'Frontend tests failed.' }
npm run build
$buildStatus = $LASTEXITCODE
Pop-Location
if ($buildStatus -ne 0) { throw 'Build failed.' }
if (-not (Test-Path .git)) { git init -b main }
$remote = git remote
if ($remote) { throw 'Existing Git remotes found. Inspect before publishing.' }
git add .
python scripts/check_publish.py
if ($LASTEXITCODE -ne 0) { throw 'Publication content check failed.' }
git diff --cached --stat
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) { git commit -m 'feat: build EventPulse SRE observability platform' }
if ($LASTEXITCODE -ne 0) { throw 'Commit failed; configure your git user.name and user.email locally.' }
gh repo create $repo --public --source=. --remote=origin --push
if ($LASTEXITCODE -ne 0) { throw 'Repository publication failed. No success is claimed.' }
git ls-remote origin refs/heads/main
if ($LASTEXITCODE -ne 0) { throw 'Remote verification failed.' }
Write-Host "Published https://github.com/$repo"
Write-Host 'Check the Actions tab separately; configured CI is not a verified CI run.'
