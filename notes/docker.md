# MC/DC Docker Image — Platform Usage Guide

## 1) Linux (Intel/AMD64) — Native ✅

**Pull (tag)**

```bash
docker pull ghcr.io/cement-psaap/mcdc:dev
# or pinned tag:
docker pull ghcr.io/cement-psaap/mcdc:dev-2025-02-18
```

**Run**

```bash
docker run --rm -it ghcr.io/cement-psaap/mcdc:dev
# or:
docker run --rm -it ghcr.io/cement-psaap/mcdc:dev-2025-02-18
```

---

## 2) Windows (Intel/AMD64) — Native ✅ (Docker Desktop + WSL2)

**Pull**

```bash
docker pull ghcr.io/cement-psaap/mcdc:dev
# or:
docker pull ghcr.io/cement-psaap/mcdc:dev-2025-02-18
```

**Run**

```bash
docker run --rm -it ghcr.io/cement-psaap/mcdc:dev
# or:
docker run --rm -it ghcr.io/cement-psaap/mcdc:dev-2025-02-18
```

> **Note:** "Linux containers" mode must be enabled in Docker Desktop (this is typically the default).

---

## 3) macOS Intel — Native ✅

**Pull**

```bash
docker pull ghcr.io/cement-psaap/mcdc:dev
# or:
docker pull ghcr.io/cement-psaap/mcdc:dev-2025-02-18
```

**Run**

```bash
docker run --rm -it ghcr.io/cement-psaap/mcdc:dev
# or:
docker run --rm -it ghcr.io/cement-psaap/mcdc:dev-2025-02-18
```

---

## 4) macOS Apple Silicon (M1/M2/M3/M4) — Via Emulation ✅ (may be slower)

**Pull (force amd64)**

```bash
docker pull --platform=linux/amd64 ghcr.io/cement-psaap/mcdc:dev
# or:
docker pull --platform=linux/amd64 ghcr.io/cement-psaap/mcdc:dev-2025-02-18
```

**Run (force amd64)**

```bash
docker run --rm -it --platform=linux/amd64 ghcr.io/cement-psaap/mcdc:dev
# or:
docker run --rm -it --platform=linux/amd64 ghcr.io/cement-psaap/mcdc:dev-2025-02-18
```

---

## 5) Linux ARM64 (e.g., AWS Graviton, Raspberry Pi) — No Native Support ❌ / Via Emulation ⚠️

**Attempting via emulation (running amd64 on an ARM64 host)**

```bash
docker run --rm -it --platform=linux/amd64 ghcr.io/cement-psaap/mcdc:dev
```

> **Note:** This may not work on some ARM64 Linux systems if qemu/binfmt is not properly installed. The correct solution is to build and push the image for `linux/arm64` as well.

---

## What Is the "unknown/unknown" Digest?

- `unknown/unknown` typically indicates a manifest or attestation entry with missing platform metadata.
- It is **not recommended** to use it at runtime.
- The actual image you want to run is the `linux/amd64` digest: `sha256:337dd...f9a6`.

> If needed, I can provide a ready-made GitHub Actions snippet for publishing multi-arch images (amd64 + arm64), which would eliminate the need to specify `--platform` on Apple Silicon.
