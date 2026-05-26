# CI workflow

The `.github/workflows/ci.yml` file (lint + matrix tests on 3.10/3.11/3.12)
exists locally but is not committed to the default branch — the PAT used for
the initial automated push lacked the `workflow` scope. To enable it:

```
gh auth refresh -h github.com -s workflow
git checkout -b ci/enable
# (re-add ci.yml from the local copy)
git add .github/workflows/ci.yml && git commit -m "ci: enable matrix tests"
git push -u origin ci/enable
```

Then merge via PR.
