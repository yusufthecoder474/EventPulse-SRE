$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path .git)) { throw 'Use a clone of the existing repository. Do not initialize a new repository from a ZIP.' }
if ((git remote get-url origin).Trim() -notmatch '^https://github.com/yusufthecoder474/EventPulse-SRE(\.git)?$') { throw 'Unexpected origin. Inspect git remote -v.' }
if (git status --porcelain) { throw 'Review, test and commit intended changes first. This helper does not stage or overwrite files.' }
$branch = (git branch --show-current).Trim()
if ($branch -eq 'main' -or -not $branch.StartsWith('feat/')) { throw 'Use a reviewed feat/* branch; main is not pushed by this helper.' }
git fetch origin
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed; authenticate Git locally. Never paste tokens into chat.' }
python scripts/check_publish.py --all
if ($LASTEXITCODE -ne 0) { throw 'Content check failed.' }
git diff origin/main...HEAD --stat
git push -u origin $branch
if ($LASTEXITCODE -ne 0) { throw 'Push failed. No force push is attempted. Inspect the remote branch before retrying.' }
git ls-remote origin "refs/heads/$branch"
if ($LASTEXITCODE -ne 0) { throw 'Remote verification failed.' }
Write-Host 'Open a pull request to main and verify the Actions run for the pushed SHA.'
