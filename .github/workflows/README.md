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

## What `build-release.yml` checks

The workflow builds twice, once per GPU edition: `cuda` (NVIDIA, the main release with the plain
file names that `winget-release.yml` submits) and `xpu` (Intel Arc and Core Ultra, file names with
an `_intel_gpu` suffix). Each build installs its PyTorch and the DirectML ONNX Runtime with
`Install-GpuRuntime` from `scripts/bundle.ps1`.

Before anything is published, the `cuda` build runs the test suite and `pyright`, and both builds
bundle the app with the same PyInstaller options as the local scripts (`scripts/bundle.ps1`), then
run the installer bundle and the portable exe with `--self-test`. A missing module, DLL, data file,
speech dictionary, or QML plugin fails the workflow with a PASS/FAIL report in the log. The release
job publishes one GitHub Release with both editions' files only after both builds pass.
