# Release Workflow Reference

Commit-keyword-triggered versioning pattern from jschell/HEIC-convert.

## How it works

1. Developer merges a PR whose commit message contains `[bump minor]` (or patch/major/release)
2. `check-release` job parses the keyword, reads current version, computes new version
3. `build-and-release` compiles, checksums, creates GitHub Release with artifacts
4. Optional `publish-*` job pushes to package registry

## Full template

```yaml
name: Release

on:
  push:
    branches: [main]

jobs:
  check-release:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    outputs:
      should_release: ${{ steps.check.outputs.should_release }}
      new_version: ${{ steps.check.outputs.new_version }}
      tag: ${{ steps.check.outputs.tag }}

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.RELEASE_TOKEN }}   # PAT required — GITHUB_TOKEN is silently blocked

      - name: Check release keyword
        id: check
        shell: bash
        run: |
          MSG="${{ github.event.head_commit.message }}"
          CURRENT=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
          IFS='.' read -r MAJOR MINOR PATCH <<< "${CURRENT#v}"

          if echo "$MSG" | grep -q "\[bump major\]"; then
            NEW="$((MAJOR+1)).0.0"
          elif echo "$MSG" | grep -q "\[bump minor\]"; then
            NEW="${MAJOR}.$((MINOR+1)).0"
          elif echo "$MSG" | grep -q "\[bump patch\]"; then
            NEW="${MAJOR}.${MINOR}.$((PATCH+1))"
          elif echo "$MSG" | grep -q "\[release\]"; then
            NEW="${MAJOR}.${MINOR}.${PATCH}"
          else
            echo "should_release=false" >> "$GITHUB_OUTPUT"
            exit 0
          fi

          echo "should_release=true" >> "$GITHUB_OUTPUT"
          echo "new_version=$NEW" >> "$GITHUB_OUTPUT"
          echo "tag=v$NEW" >> "$GITHUB_OUTPUT"

  build-and-release:
    needs: check-release
    if: needs.check-release.outputs.should_release == 'true'
    runs-on: windows-latest       # adjust per stack
    timeout-minutes: 30

    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.RELEASE_TOKEN }}

      # Stack setup + cache (see ci-workflow.md)
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'

      - uses: actions/cache@v4
        with:
          path: ~/.nuget/packages
          key: ${{ runner.os }}-nuget-${{ hashFiles('**/*.csproj') }}
          restore-keys: ${{ runner.os }}-nuget-

      - run: dotnet restore
      - run: dotnet test --configuration Release

      - name: Publish
        run: >
          dotnet publish src/MyApp/MyApp.csproj
          --configuration Release
          --runtime win-x64
          --self-contained true
          -p:PublishSingleFile=true
          -p:IncludeNativeLibrariesForSelfExtract=true
          -o publish/

      - name: Zip artifact
        run: Compress-Archive -Path publish\* -DestinationPath MyApp-${{ needs.check-release.outputs.new_version }}-win-x64.zip
        shell: pwsh

      - name: SHA256 checksum
        shell: bash
        run: sha256sum *.zip > checksums.txt

      - name: Smoke test
        shell: bash
        run: |
          ./publish/MyApp.exe &
          sleep 5
          kill %1 2>/dev/null || true

      - name: Tag and create release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ needs.check-release.outputs.tag }}
          name: Release ${{ needs.check-release.outputs.new_version }}
          generate_release_notes: true
          files: |
            *.zip
            checksums.txt
        env:
          GITHUB_TOKEN: ${{ secrets.RELEASE_TOKEN }}
```

## Why `RELEASE_TOKEN`, not `GITHUB_TOKEN`

GitHub's anti-loop protection prevents a workflow triggered by `GITHUB_TOKEN` from triggering downstream events (like a release event that other workflows listen to). A PAT bypasses this. Store it as a repo secret named `RELEASE_TOKEN`.

## Versioning convention

- Start at `v0.1.0` — `1.0.0` signals production-stable
- `[release]` re-publishes current version without bumping (useful for CI re-runs)
- Dependabot auto-merge uses `[bump patch]` in squash commit message — feeding back into this workflow automatically

## Multi-platform builds

For cross-compile (Go, Rust) or multi-OS (.NET), use a matrix:
```yaml
strategy:
  matrix:
    include:
      - os: ubuntu-latest;  runtime: linux-x64
      - os: windows-latest; runtime: win-x64
      - os: macos-latest;   runtime: osx-x64
```
