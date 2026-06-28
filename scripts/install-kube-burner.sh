#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
source "$SCRIPT_DIR/common.sh"

require_command curl
require_command tar

version=${KUBE_BURNER_VERSION:-v2.7.3}
version_no_v=${version#v}
os=${KUBE_BURNER_OS:-auto}
arch=${KUBE_BURNER_ARCH:-auto}

if [[ "$os" == auto ]]; then
  case "$(uname -s)" in
    Linux) os=linux ;;
    Darwin) os=darwin ;;
    *) die "unsupported OS $(uname -s); set KUBE_BURNER_OS manually" ;;
  esac
fi

if [[ "$arch" == auto ]]; then
  case "$(uname -m)" in
    x86_64|amd64) arch=x86_64 ;;
    aarch64|arm64) arch=arm64 ;;
    ppc64le) arch=ppc64le ;;
    s390x) arch=s390x ;;
    *) die "unsupported architecture $(uname -m); set KUBE_BURNER_ARCH manually" ;;
  esac
fi

asset="kube-burner-V${version_no_v}-${os}-${arch}.tar.gz"
base_url="https://github.com/kube-burner/kube-burner/releases/download/${version}"
install_dir="$REPO_ROOT/${TOOLS_DIR:-tools}/kube-burner/${version}"
bin_dir="$REPO_ROOT/${TOOLS_DIR:-tools}/bin"
binary="$install_dir/kube-burner"
link="$bin_dir/kube-burner"

if [[ -x "$binary" ]]; then
  log "kube-burner $version already installed at $binary"
  mkdir -p "$bin_dir"
  ln -sf "../kube-burner/${version}/kube-burner" "$link"
  exit 0
fi

tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT

archive="$tmp_dir/$asset"
checksums="$tmp_dir/kube-burner-checksums.txt"

log "Downloading $asset"
curl -fsSL "$base_url/$asset" -o "$archive"
curl -fsSL "$base_url/kube-burner-checksums.txt" -o "$checksums"

if command -v sha256sum >/dev/null 2>&1; then
  expected=$(awk -v asset="$asset" '$2 == asset {print $1}' "$checksums")
  [[ -n "$expected" ]] || die "checksum entry for $asset not found"
  actual=$(sha256sum "$archive" | awk '{print $1}')
elif command -v shasum >/dev/null 2>&1; then
  expected=$(awk -v asset="$asset" '$2 == asset {print $1}' "$checksums")
  [[ -n "$expected" ]] || die "checksum entry for $asset not found"
  actual=$(shasum -a 256 "$archive" | awk '{print $1}')
else
  die "sha256sum or shasum is required to validate kube-burner release assets"
fi
[[ "$actual" == "$expected" ]] || die "checksum mismatch for $asset"
log "Validated checksum for $asset"

mkdir -p "$install_dir" "$bin_dir"
tar -xzf "$archive" -C "$tmp_dir"
found_binary=$(find "$tmp_dir" -type f -name kube-burner -perm -u+x | head -n 1)
[[ -n "$found_binary" ]] || die "kube-burner binary not found in $asset"
cp "$found_binary" "$binary"
chmod +x "$binary"
ln -sf "../kube-burner/${version}/kube-burner" "$link"
log "Installed kube-burner $version at $link"
