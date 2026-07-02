# .gitignore Templates

Minimal patterns per stack. Append to a base `.gitignore`.

## Python
```
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/
.env
*.env
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage
```

## Node / JavaScript / TypeScript
```
node_modules/
dist/
build/
.env
*.env
.env.local
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.next/
.nuxt/
```

## Go
```
/bin/
/dist/
*.exe
*.test
*.out
vendor/
```

## Rust
```
/target/
Cargo.lock   # remove this line for libraries (keep for binaries)
```

## .NET / C#
```
bin/
obj/
*.user
.vs/
TestResults/
*.nupkg
publish/
```

## General (always include)
```
.DS_Store
Thumbs.db
*.swp
*.swo
.idea/
.vscode/
*.log
```

## MIT LICENSE file template
```
MIT License

Copyright (c) YEAR AUTHOR

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
