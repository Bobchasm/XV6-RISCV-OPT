#!/usr/bin/env bash

set -Eeuo pipefail

readonly REQUIRED_QEMU_VERSION="7.2"
readonly QEMU_SOURCE_VERSION="7.2.0"
readonly QEMU_PREFIX="/usr/local"
readonly QEMU_SOURCE_URL="https://download.qemu.org/qemu-${QEMU_SOURCE_VERSION}.tar.xz"
readonly QEMU_FALLBACK_URL="https://github.com/qemu/qemu/archive/refs/tags/v${QEMU_SOURCE_VERSION}.tar.gz"

log() {
  printf '[xv6-env] %s\n' "$*"
}

fail() {
  printf '[xv6-env] ERROR: %s\n' "$*" >&2
  exit 1
}

version_at_least() {
  printf '%s\n%s\n' "$REQUIRED_QEMU_VERSION" "$1" | sort -V -C
}

qemu_version() {
  local version

  if ! command -v qemu-system-riscv64 >/dev/null 2>&1; then
    return 1
  fi

  version=$(qemu-system-riscv64 --version |
    sed -nE 's/^QEMU emulator version ([0-9]+\.[0-9]+(\.[0-9]+)?).*/\1/p' |
    head -n 1)
  [ -n "$version" ] || return 1
  printf '%s\n' "$version"
}

install_packages() {
  local packages=(
    build-essential
    gcc-riscv64-linux-gnu
    binutils-riscv64-linux-gnu
    qemu-system-misc
    qemu-utils
    python3
    perl
    curl
    wget
    xz-utils
    ninja-build
    meson
    pkg-config
    libglib2.0-dev
    libpixman-1-dev
    libfdt-dev
    libslirp-dev
    zlib1g-dev
    libcapstone-dev
  )

  log "Installing required packages..."
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${packages[@]}"
}

build_qemu() {
  local build_root archive source_dir archive_type temp_archive

  build_root="${TMPDIR:-/tmp}/xv6-qemu-${QEMU_SOURCE_VERSION}"
  source_dir="${build_root}/qemu-${QEMU_SOURCE_VERSION}"

  if [ ! -d "$source_dir" ]; then
    mkdir -p "$build_root"

    archive="${build_root}.tar.xz"
    temp_archive="${archive}.download"
    archive_type="xz"

    log "Downloading QEMU ${QEMU_SOURCE_VERSION}..."
    rm -f "$temp_archive"
    if ! curl --fail --location --show-error --retry 3 \
      --connect-timeout 15 --output "$temp_archive" "$QEMU_SOURCE_URL" ||
      ! xz -t "$temp_archive" >/dev/null 2>&1; then
      log "Primary QEMU download failed; trying GitHub mirror..."
      rm -f "$temp_archive"
      archive="${build_root}.tar.gz"
      temp_archive="${archive}.download"
      archive_type="gz"
      curl --fail --location --show-error --retry 3 \
        --connect-timeout 15 --output "$temp_archive" "$QEMU_FALLBACK_URL"
      tar -tzf "$temp_archive" >/dev/null
    fi

    mv "$temp_archive" "$archive"
    if [ "$archive_type" = "xz" ]; then
      tar -xJf "$archive" -C "$build_root"
    else
      tar -xzf "$archive" -C "$build_root"
    fi
  fi

  log "Building QEMU ${QEMU_SOURCE_VERSION}..."
  make -C "$source_dir" distclean >/dev/null 2>&1 || true
  (
    cd "$source_dir"
    ./configure \
      --prefix="$QEMU_PREFIX" \
      --target-list=riscv64-softmmu \
      --enable-slirp \
      --disable-werror
    make -j"$(nproc)"
  )

  log "Installing QEMU ${QEMU_SOURCE_VERSION} to ${QEMU_PREFIX}..."
  sudo make -C "$source_dir" install
  hash -r
}

check_supported_ubuntu() {
  local version_id codename

  # shellcheck disable=SC1091
  . /etc/os-release
  version_id="${VERSION_ID:-}"
  codename="${VERSION_CODENAME:-unknown}"

  case "$version_id" in
    22.04|24.04)
      log "Detected Ubuntu ${version_id} (${codename})."
      ;;
    *)
      fail "This script supports Ubuntu 22.04 and 24.04, detected ${version_id:-unknown}."
      ;;
  esac
}

main() {
  local version

  [ "$(id -u)" -ne 0 ] ||
    fail "Run this script as a normal user; it will use sudo when needed."

  check_supported_ubuntu
  install_packages

  if version=$(qemu_version) && version_at_least "$version"; then
    log "QEMU ${version} already satisfies the requirement (>= ${REQUIRED_QEMU_VERSION})."
  else
    log "System QEMU is missing or older than ${REQUIRED_QEMU_VERSION}; building QEMU ${QEMU_SOURCE_VERSION}."
    build_qemu
  fi

  command -v riscv64-linux-gnu-gcc >/dev/null 2>&1 ||
    fail "riscv64-linux-gnu-gcc was not found after installation."

  version=$(qemu_version) || fail "qemu-system-riscv64 was not found after installation."
  version_at_least "$version" ||
    fail "QEMU ${version} is still older than ${REQUIRED_QEMU_VERSION}."

  log "Environment is ready."
  log "Compiler: $(command -v riscv64-linux-gnu-gcc)"
  log "QEMU: $(command -v qemu-system-riscv64) (${version})"
  log "Build with: make -j\"$(nproc)\" TOOLPREFIX=riscv64-linux-gnu-"
}

main "$@"
