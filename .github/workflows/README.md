# Workflows — dev-build status

Both workflows here are **manual-trigger only** (`workflow_dispatch`) right now. The app isn't
stable/usable yet, so nothing should auto-publish a release until it is.

| Workflow | Current trigger | Trigger once stable |
|---|---|---|
| `build-release.yml` | Manual — pick an existing tag to build/release | Uncomment `push: tags: v[0-9]*` |
| `winget-release.yml` | Manual — pick a release tag to submit | Uncomment `release: types: [published]` |

To flip a workflow back to automatic, edit the commented-out `on:` block at the top of the file
(the intended trigger is already written there, just commented) and remove the
`workflow_dispatch`-only block, or keep both if you want manual + automatic triggers side by side.

Until then, `scripts/release.sh` still tags and pushes releases the normal way — you just trigger
the two workflows by hand from the **Actions** tab afterward if you want to test the pipeline.
