# My GitHub Command Cheatsheet
---

## ➡️ Checking Out a Pull Request

```bash
git fetch origin pull/364/head:pr-364 && git checkout pr-364
```

## ➡️ GitHub SSH Setup with RSA

### 1. Generate an RSA SSH Key

Open your terminal on the server (or local machine):

```bash
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

- Press **Enter** to accept the default path (`~/.ssh/id_rsa`).
- Optionally enter a passphrase for extra security.

This creates two files:

- `~/.ssh/id_rsa` → Private key (keep secret)
- `~/.ssh/id_rsa.pub` → Public key (add to GitHub)

### 2. Copy the Public Key

```bash
cat ~/.ssh/id_rsa.pub
```

Copy the **full output** (starts with `ssh-rsa`, ends with your email).

### 3. Add the Key to GitHub

1. Go to **GitHub → Settings → SSH and GPG keys**
2. Click **New SSH key**
3. Give it a descriptive title (e.g., `my-server`)
4. Paste the public key into the **Key** field
5. Click **Add SSH key**

### 4. Start SSH Agent and Add Key

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_rsa
```

Verify the key is loaded:

```bash
ssh-add -l
```

### 5. Test GitHub SSH Connection

```bash
ssh -T git@github.com
```

Expected output:

```
Hi USERNAME! You've successfully authenticated, but GitHub does not provide shell access.
```

### 6. Clone Using SSH (Not HTTPS)

```bash
git clone git@github.com:USERNAME/REPO.git
```

If your existing repo uses HTTPS, switch it to SSH:

```bash
git remote set-url origin git@github.com:USERNAME/REPO.git
```

Verify with:

```bash
git remote -v
```

---

### Notes

- **Never share your private key** (`id_rsa`).
- RSA 4096 is widely compatible with older servers and HPC clusters.
- For modern systems, `ed25519` keys are shorter and faster — consider using `ssh-keygen -t ed25519` if compatibility is not a concern.
