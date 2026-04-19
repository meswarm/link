# .gitignore Rules by Stack

Agent 在审查或生成 `.gitignore` 时，根据检测到的技术栈选取对应章节的规则。
每个章节可叠加使用——例如一个 Node + Docker 项目应同时包含 "Node / JavaScript"
和 "Docker" 两个章节的规则。

---

## Universal (always include)

```gitignore
# === OS files ===
.DS_Store
Desktop.ini
Thumbs.db
._*

# === Editor / IDE ===
.vscode/
.idea/
*.swp
*.swo
*~
.project
.classpath
.settings/

# === Environment & secrets ===
.env
.env.*
!.env.example
*.pem
*.key
*.p12
```

---

## Node / JavaScript / TypeScript

```gitignore
# === Dependencies ===
node_modules/

# === Build output ===
dist/
build/
.next/
.nuxt/
.output/
out/
.svelte-kit/

# === Cache ===
.cache/
.parcel-cache/
.turbo/
.eslintcache
tsconfig.tsbuildinfo

# === Logs ===
*.log
npm-debug.log*
yarn-debug.log*
pnpm-debug.log*

# === Coverage ===
coverage/
.nyc_output/
```

**不要忽略**: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`

---

## Python

```gitignore
# === Bytecode ===
__pycache__/
*.py[cod]
*$py.class

# === Virtual environments ===
.venv/
venv/
env/
.python-version

# === Distribution ===
dist/
build/
*.egg-info/
*.egg

# === Cache ===
.mypy_cache/
.ruff_cache/
.pytest_cache/
.coverage
htmlcov/

# === Jupyter ===
.ipynb_checkpoints/
```

**不要忽略**: `poetry.lock`, `uv.lock`, `Pipfile.lock`, `requirements.txt`

---

## Rust

```gitignore
# === Build ===
target/

# === Debug ===
**/*.rs.bk
```

**注意**: 应用项目 (binary) 应提交 `Cargo.lock`；库 (library) 项目通常不提交。

---

## Go

```gitignore
# === Binary output ===
/bin/
*.exe
*.exe~
*.dll
*.so
*.dylib

# === Test ===
*.test
*.out
coverage.txt

# === Vendor (if not vendoring) ===
# vendor/
```

**不要忽略**: `go.sum`

---

## Java / Kotlin / JVM

```gitignore
# === Build ===
target/
build/
*.class
*.jar
*.war

# === Gradle ===
.gradle/
!gradle-wrapper.jar

# === Maven ===
.mvn/repository/
```

---

## Docker

```gitignore
# === Docker (optional overrides) ===
docker-compose.override.yml
.docker/
```

**不要忽略**: `Dockerfile`, `docker-compose.yml`

---

## Terraform

```gitignore
.terraform/
*.tfstate
*.tfstate.*
crash.log
*.tfvars
!*.tfvars.example
.terraform.lock.hcl
```

---

## C / C++

```gitignore
# === Build ===
*.o
*.obj
*.a
*.lib
*.so
*.dylib
*.dll
*.exe
build/
cmake-build-*/
CMakeFiles/
CMakeCache.txt
```




