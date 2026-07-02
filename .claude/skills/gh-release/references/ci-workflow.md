# CI Workflow Reference

Annotated pattern from jschell/HEIC-convert. Adapt stack-specific steps; keep structure.

## Full template

```yaml
name: CI

on:
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest        # use windows-latest for WPF/WinForms
    timeout-minutes: 15

    steps:
      - uses: actions/checkout@v4

      # --- Stack setup (adapt per stack) ---
      # .NET:
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'
      # Node:
      # - uses: actions/setup-node@v4
      #   with: { node-version: '20' }
      # Python:
      # - uses: actions/setup-python@v5
      #   with: { python-version: '3.12' }

      # --- Dependency cache (adapt glob to your lock file) ---
      - uses: actions/cache@v4
        with:
          path: ~/.nuget/packages          # Node: ~/.npm  Python: ~/.cache/pip
          key: ${{ runner.os }}-deps-${{ hashFiles('**/*.csproj') }}
          # Node:   hashFiles('**/package-lock.json')
          # Python: hashFiles('**/requirements*.txt')
          restore-keys: ${{ runner.os }}-deps-

      # --- Restore / install ---
      - run: dotnet restore              # Node: npm ci  Python: pip install -r requirements.txt

      # --- Vulnerability scan (never block CI on this) ---
      - name: Vulnerability scan
        run: dotnet list package --vulnerable
        continue-on-error: true          # surfaces CVEs as annotation, doesn't fail PR

      # --- Build ---
      - run: dotnet build --no-restore --configuration Release /warnaserror

      # --- Tests: results ---
      - name: Test (results)
        run: dotnet test --no-build --configuration Release --logger trx

      # --- Tests: coverage ---
      - name: Test (coverage)
        run: dotnet test --no-build --configuration Release --collect:"XPlat Code Coverage"

      # --- Publish artifact ---
      - name: Publish
        run: >
          dotnet publish src/MyApp/MyApp.csproj
          --configuration Release
          --runtime win-x64
          --self-contained true
          -p:PublishSingleFile=true
          -o publish/

      # --- Smoke test ---
      - name: Smoke test
        shell: bash
        run: |
          ./publish/MyApp &
          PID=$!
          sleep 5
          if kill -0 $PID 2>/dev/null; then
            echo "Smoke test passed"
            kill $PID
          else
            echo "Process exited early" && exit 1
          fi

      # --- Upload artifacts for review ---
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: "**/*.trx"
```

## Cache key strategy

| Stack | Path | `hashFiles` glob |
|-------|------|-----------------|
| .NET | `~/.nuget/packages` | `**/*.csproj` |
| Node | `~/.npm` | `**/package-lock.json` |
| Python (pip) | `~/.cache/pip` | `**/requirements*.txt` |
| Python (uv) | `~/.cache/uv` | `**/pyproject.toml` |
| Go | `~/go/pkg/mod` | `**/go.sum` |
| Rust | `~/.cargo/registry` | `**/Cargo.lock` |

**Note:** Built-in caching (`setup-dotnet` `cache: true`) fails when lock files are missing. Manual `actions/cache@v4` is more reliable — always use it.
