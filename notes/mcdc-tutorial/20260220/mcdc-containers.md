# MC/DC Container Guide

## What Are Containers?

A container is a lightweight, portable package that bundles an application
together with everything it needs to run: code, libraries, system tools,
and settings. Think of it like a shipping container — no matter what ship
(computer) carries it, the contents inside stay the same.

**Why does this matter for MC/DC?**

Installing MC/DC requires Python, MPI, Numba, and many other dependencies.
Getting all of these working together — especially on HPC systems where you
don't have admin access — can be painful. A container solves this by giving
you a pre-built environment where everything is already installed and tested.

**Key terms:**

- **Image**: A read-only template (like a recipe). You build it once.
- **Container**: A running instance of an image (like the cooked meal).
- **Dockerfile**: Instructions to build an image (like the recipe card).
- **Registry**: A place to store and share images (like a cookbook library).
- **Docker**: Container tool for laptops and some HPC systems.
- **Podman**: Container tool used on LLNL HPC systems (works like Docker).
- **Apptainer (Singularity)**: Container tool used on OSU HPC systems.
- **SIF file**: Apptainer's container format (a single `.sif` file).
- **Sandbox**: An uncompressed container directory (alternative to SIF).

## Tested Platforms

| System      | OS         | Arch   | Container Tool     | Status |
|-------------|------------|--------|--------------------|--------|
| MacBook Pro | macOS 26.3 | arm64  | Docker 29.2.0      | ✅      |
| Tuolumne    | RHEL 8.10  | x86_64 | Podman 4.9.4       | ✅      |
| Dane        | RHEL 8.10  | x86_64 | Podman 4.9.4       | ✅      |
| Tioga       | RHEL 8.10  | x86_64 | Podman 4.9.4       | ✅      |
| COE (OSU)   | Rocky 8.10 | x86_64 | Apptainer 1.4.5    | ✅      |

All platforms produce identical containers: Debian 13, Python 3.11,
MPICH 4.2.1, MC/DC 0.12.0.

## Quick Start: Pull a Pre-Built Image (Recommended)

The easiest way to use MC/DC in a container is to pull a pre-built image
from the GitHub Container Registry. No building required.

### Local Machine (Docker)

```bash
docker pull ghcr.io/cement-psaap/mcdc:dev
docker run --rm -it ghcr.io/cement-psaap/mcdc:dev
```

### LLNL Systems — Tuolumne, Tioga, Dane (Podman)

```bash
podman pull ghcr.io/cement-psaap/mcdc:dev
podman run --rm -it ghcr.io/cement-psaap/mcdc:dev
```

> **Note:** If you get `lsetxattr: operation not supported`, Podman's
> storage is on a network filesystem. See [LLNL Storage Setup](#llnl-storage-setup)
> below.

### OSU Systems — COE (Apptainer)

```bash
# Pull as a sandbox (recommended for COE)
apptainer build --sandbox mcdc_sandbox docker://ghcr.io/cement-psaap/mcdc:dev

# Run
apptainer exec mcdc_sandbox python -c "import mcdc; print('MC/DC OK')"
```

> **Note:** `apptainer pull mcdc.sif ...` may fail with "Out of memory"
> on COE due to limited mksquashfs resources. Use `--sandbox` instead.

## Building from Source

If you want to build the image yourself (e.g., to test code changes),
follow the instructions for your system below.

### Prerequisites

Make sure you are in the **root directory of the MC/DC repository**
(not inside the `containers/` folder). The build context needs access
to the full source code.

```bash
cd /path/to/MCDC
ls containers/Dockerfile    # This should exist
ls pyproject.toml            # This should exist
```

### Local Machine (Docker)

```bash
docker build -f containers/Dockerfile -t mcdc:dev .
```

### Local Machine (Docker Compose)

```bash
docker compose -f containers/docker-compose.yml build
docker compose -f containers/docker-compose.yml run --rm dev bash
```

See [Docker Compose](#docker-compose) section for more details.

### LLNL Systems — Tuolumne, Tioga, Dane (Podman)

```bash
podman build -f containers/Dockerfile -t mcdc:dev .
```

> **Note:** If you get `lsetxattr: operation not supported`, you need
> to set up local storage first. See [LLNL Storage Setup](#llnl-storage-setup).

### OSU Systems — COE (Apptainer)

Apptainer cannot build directly from a Dockerfile. Instead, pull from
the registry:

```bash
apptainer build --sandbox mcdc_sandbox docker://ghcr.io/cement-psaap/mcdc:dev
```

Or, if the image was built elsewhere and saved as a tar file:

```bash
# On the machine with Docker (e.g., your laptop)
docker build -f containers/Dockerfile -t mcdc:dev .
docker save mcdc:dev -o mcdc.tar
scp mcdc.tar <username>@submit-a.hpc.engr.oregonstate.edu:~/

# On COE
apptainer build --sandbox mcdc_sandbox docker-archive://mcdc.tar
```

## Running MC/DC

### Docker (Local Machine)

```bash
# Interactive shell
docker run --rm -it mcdc:dev

# Run a script directly
docker run --rm -v $(pwd):/work -w /work mcdc:dev python input.py

# Run with MPI
docker run --rm mcdc:dev mpirun -n 4 python input.py
```

**What do the flags mean?**

- `--rm`: Remove the container when it exits (keeps things clean).
- `-it`: Interactive mode with a terminal (so you can type commands).
- `-v $(pwd):/work`: Mount your current directory inside the container
  at `/work`, so the container can see your input files.
- `-w /work`: Set the working directory inside the container to `/work`.

### Podman (LLNL Systems)

Podman commands are identical to Docker — just replace `docker` with `podman`:

```bash
# Interactive shell
podman run --rm -it mcdc:dev

# Run a script
podman run --rm -v $(pwd):/work -w /work mcdc:dev python input.py

# Run with MPI
podman run --rm mcdc:dev mpirun -n 4 python input.py
```

### Apptainer (OSU Systems)

Apptainer uses a different syntax:

```bash
# Interactive shell
apptainer shell mcdc_sandbox

# Run a command
apptainer exec mcdc_sandbox python input.py

# Run with MPI (must use -launcher fork on login/compute nodes)
apptainer exec mcdc_sandbox mpirun -launcher fork -n 4 python input.py
```

> **Note:** Apptainer automatically mounts your home directory, so your
> input files are already visible inside the container.

## Docker Compose

Docker Compose simplifies running containers by storing all the options
in a configuration file. Instead of typing long `docker run` commands,
you can use short `docker compose` commands.

Three services are available:

### Development Shell

```bash
docker compose -f containers/docker-compose.yml run --rm dev bash
```

This mounts your local source code into the container, so any changes
you make on your laptop are immediately reflected inside. Great for
editing code and testing interactively.

### Running Tests

```bash
docker compose -f containers/docker-compose.yml run --rm test
```

This automatically runs the unit test suite.

### Running with MPI

```bash
docker compose -f containers/docker-compose.yml run --rm mpi mpirun -n 4 python input.py
```

### Building

```bash
docker compose -f containers/docker-compose.yml build
```

## LLNL Storage Setup

LLNL HPC systems use network filesystems (NFS/Lustre) that are
incompatible with Podman's default container storage. You will see this
error if storage is not configured:

```
lsetxattr: operation not supported
```

**Option A: Use the `--root` flag on every command**

```bash
podman --root /var/tmp/$USER/containers/storage build -f containers/Dockerfile -t mcdc:dev .
podman --root /var/tmp/$USER/containers/storage run --rm -it mcdc:dev
```

**Option B: Create a configuration file (recommended)**

This tells Podman to always use local storage, so you don't need
the `--root` flag:

```bash
mkdir -p ~/.config/containers
cat > ~/.config/containers/storage.conf << EOF
[storage]
driver = "overlay"
graphroot = "/var/tmp/$USER/containers/storage"

[storage.options.overlay]
force_mask = "700"
mount_program = "/usr/bin/fuse-overlayfs"
EOF
```

After creating this file, verify it works:

```bash
podman info | grep graphRoot
```

You should see `/var/tmp/<your-username>/containers/storage`.

> **Note:** On some systems (e.g., Tioga), the configuration file may
> not take effect. If Podman still fails after creating the config,
> fall back to Option A (`--root` flag).

## Pushing to the Registry

If you are a developer and need to update the container image on the
GitHub Container Registry:

### One-Time Setup

1. Create a GitHub Personal Access Token (classic) at
   https://github.com/settings/tokens
2. Select the `write:packages` scope
3. Login to the registry:

```bash
echo "YOUR_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

### Building and Pushing

For HPC compatibility, always build for the `linux/amd64` platform:

```bash
docker build --platform linux/amd64 -f containers/Dockerfile -t mcdc:dev-amd64 .
docker tag mcdc:dev-amd64 ghcr.io/cement-psaap/mcdc:dev
docker tag mcdc:dev-amd64 ghcr.io/cement-psaap/mcdc:dev-$(date +%Y-%m-%d)
docker push ghcr.io/cement-psaap/mcdc:dev
docker push ghcr.io/cement-psaap/mcdc:dev-$(date +%Y-%m-%d)
```

> **Why `--platform linux/amd64`?** If you build on an Apple Silicon Mac
> (arm64), the image will only run on arm64 machines. All HPC systems
> are x86_64 (amd64), so we must cross-compile.

## Troubleshooting

### `lsetxattr: operation not supported`

**Cause:** Podman is trying to write container storage to a network
filesystem (NFS/Lustre).

**Fix:** See [LLNL Storage Setup](#llnl-storage-setup).

### `setgroups 65534 failed` or APT sandbox errors

**Cause:** Rootless Podman cannot map the `nobody` user that `apt-get`
tries to use for privilege separation.

**Fix:** The Dockerfile already includes a fix for this:
```dockerfile
RUN echo 'APT::Sandbox::User "root";' > /etc/apt/apt.conf.d/no-sandbox
```
Make sure you are using the latest Dockerfile.

### `permission denied` when running container (Podman)

**Cause:** On some LLNL filesystems, the non-root user inside the
container cannot access executables.

**Fix:** Run as root:
```bash
podman run --rm -it --user root mcdc:dev
```

### `Out of memory (cache_alloc)` or `Failed to create thread` (Apptainer)

**Cause:** The `mksquashfs` tool that creates SIF files needs more
resources than are available.

**Fix:** Use sandbox mode instead of SIF:
```bash
apptainer build --sandbox mcdc_sandbox docker://ghcr.io/cement-psaap/mcdc:dev
```

### hwloc or UCX warnings

Messages like `hwloc received invalid information` or
`unable to read somaxconn` are **harmless**. The container cannot fully
read the host's hardware topology, but MPI communication still works
correctly.

### `HYDU_create_process: execvp error on file srun`

**Cause:** MPICH detects Slurm and tries to use `srun`, which is not
available inside the container.

**Fix:** Use the fork launcher:
```bash
mpirun -launcher fork -n 4 python input.py
```

### `manifest unknown` or `permission_denied` when pushing

**Cause:** The GitHub Container Registry package may not be linked to
the repository or may be private.

**Fix:**
1. Go to https://github.com/orgs/CEMeNT-PSAAP/packages
2. Find the `mcdc` package → Settings
3. Change visibility to **Public**
4. Under "Manage Actions access", add the `MCDC` repository

## File Overview

```
containers/
├── Dockerfile           # Build instructions for the container image
├── docker-compose.yml   # Simplified commands for Docker users
├── mcdc.def             # Apptainer definition file (alternative build)
└── README.md            # This file
```
