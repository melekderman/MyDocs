# Jekyll setup & troubleshooting notes (macOS)

Purpose: backup of commands and fixes used to get a local Jekyll preview running for this repository.

## Environment
- macOS (Apple Silicon / Homebrew)
- Use Homebrew Ruby to avoid system permission and gem compatibility issues.

## Quick commands (preferred flow)

```bash
# 1) Install Homebrew Ruby (if not installed)
brew install ruby@3.2

# 2) Add Ruby & gem bin to PATH (one-liner; add to ~/.zshrc for permanence)
export PATH="/opt/homebrew/opt/ruby@3.2/bin:/opt/homebrew/lib/ruby/gems/3.2.0/bin:$PATH"

# 3) Install Bundler (global) and project gems
gem install bundler
cd ~/github/website/melekderman.github.io
bundle install

# 4) Start local server
bundle exec jekyll serve
# or on a different port if 4000 busy:
bundle exec jekyll serve --port 4001
```

## Common problems & fixes

### 1) `jekyll: command not found` or permission errors installing gems
- Use Homebrew Ruby (see above) to avoid installing into `/Library/Ruby/Gems`.
- Alternatively install user gems with `gem install --user-install <gem>` and add the user gem bin dir to PATH.

### 2) Incompatible gem versions / native extension errors
- If Bundler fails resolving with system Ruby, use Homebrew Ruby and re-run `bundle install`.
- For specific gem version hints, install the compatible versions manually, e.g.:

```bash
# examples used while troubleshooting on older ruby
gem install --user-install bundler -v 2.4.22
gem install --user-install rouge -v 3.30.0
gem install --user-install ffi -v 1.16.3
```

But switching to Homebrew Ruby (3.2+) then running `bundle install` in the repo is the cleaner fix.

### 3) SCSS / import error: `File to import not found or unreadable: vendor/breakpoint/breakpoint.`
- Verify the referenced file exists under `_sass/vendor/...` (e.g. `_sass/vendor/breakpoint/_breakpoint.scss`).
- Confirm `_config.yml` has `sass_dir: _sass` (default) and imports in `assets/css/main.scss` match relative paths.
- If the file exists but error persists, run `bundle install` then `bundle exec jekyll serve` (some converters rely on gems installed via Bundler).

### 4) `Address already in use - bind(2) for 127.0.0.1:4000` (port in use)
- Check which process listens on port 4000:

```bash
lsof -iTCP:4000 -sTCP:LISTEN -n -P
```

- Kill the process (use PID from lsof):

```bash
kill <PID>
# or kill all jekyll processes
pkill -f jekyll
```

- Or start Jekyll on another port:

```bash
bundle exec jekyll serve --port 4001
# open in browser:
open http://localhost:4001/publications/
```

### 5) `Could not locate Gemfile` when running `bundle exec`:
- Make sure you are in the repository root where `Gemfile` lives (e.g. `~/github/website/melekderman.github.io`).

```bash
pwd
ls -la Gemfile
```

### 6) Useful server startup flags
- Trace errors to get more details:

```bash
bundle exec jekyll serve --trace
```

- Use incremental builds during editing (faster):

```bash
bundle exec jekyll serve --incremental
```

## Helpful PATH note (add to ~/.zshrc)

```bash
# add to ~/.zshrc
echo 'export PATH="/opt/homebrew/opt/ruby@3.2/bin:/opt/homebrew/lib/ruby/gems/3.2.0/bin:$PATH"' >> ~/.zshrc
# then reload
source ~/.zshrc
```

## Final checklist (to preview changes)
- [ ] Ensure `Gemfile` exists in repo root
- [ ] `cd` to repo root
- [ ] `export PATH=...` (or have it in `~/.zshrc`)
- [ ] `bundle install`
- [ ] `bundle exec jekyll serve`
- [ ] Open `http://localhost:4000/publications/` (or chosen port)

---
