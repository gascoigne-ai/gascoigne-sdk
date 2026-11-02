//! The native variant of the `gascoigne` crate: the engine library bundled for every platform and
//! unpacked to the temporary directory on first use (see spec/native.md).

use std::io::Read;
use std::path::PathBuf;

use flate2::read::GzDecoder;
use gascoigne::{Runtime, Settings};
use sha2::{Digest, Sha256};

include!(concat!(env!("OUT_DIR"), "/bundle.rs"));

/// `<os>-<arch>` as the bundle names its folders.
fn platform_key() -> String {
    let os = match std::env::consts::OS {
        "macos" => "darwin",
        other => other,
    };
    let arch = match std::env::consts::ARCH {
        "x86_64" => "amd64",
        "aarch64" => "arm64",
        other => other,
    };
    format!("{os}-{arch}")
}

fn digest(data: &[u8]) -> String {
    Sha256::digest(data)
        .iter()
        .take(8)
        .fold(String::new(), |acc, b| acc + &format!("{b:02x}"))
}

/// Unpacks a gzip-compressed library into the temp directory and returns the file to load.
///
/// The folder is named by the library's hash, so this is idempotent and an existing file is trusted
/// only when its content matches; the write goes through a temporary name and a rename.
///
/// # Errors
/// Fails when the data is not gzip or the temp directory cannot be written.
pub fn unpack_bytes(gzipped: &[u8], name: &str) -> std::io::Result<PathBuf> {
    let mut data = Vec::new();
    GzDecoder::new(gzipped).read_to_end(&mut data)?;
    let digest = digest(&data);
    let root = std::env::var_os("GASCOIGNE_LIB_DIR").map_or_else(std::env::temp_dir, PathBuf::from);
    let folder = root.join(format!("gascoigne-native-{digest}"));
    let target = folder.join(name);
    if std::fs::read(&target).is_ok_and(|existing| self::digest(&existing) == digest) {
        return Ok(target);
    }
    std::fs::create_dir_all(&folder)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        std::fs::set_permissions(&folder, std::fs::Permissions::from_mode(0o700))?;
    }
    let partial = folder.join(format!(".{}.tmp", std::process::id()));
    std::fs::write(&partial, &data)?;
    std::fs::rename(&partial, &target)?;
    Ok(target)
}

/// Unpacks this platform's bundled library, or `None` when the bundle has none for it.
///
/// # Errors
/// Fails when unpacking fails.
pub fn unpack() -> std::io::Result<Option<PathBuf>> {
    let key = platform_key();
    BUNDLE
        .iter()
        .find(|(k, _, _)| *k == key)
        .map(|(_, name, bytes)| unpack_bytes(bytes, name))
        .transpose()
}

/// A runtime that runs the engine in this process. `settings` is merged by the library over its
/// defaults and the user's file.
///
/// The library is looked up in this order: `$GASCOIGNE_LIB` (which stops the search), the system
/// directories, then this crate's bundle for the platform, unpacked to the temp directory
/// (skipped with `GASCOIGNE_UNPACK=off`).
///
/// # Errors
/// Fails when none of them yields a library; the message names where it looked.
pub fn runtime(agent: &str, settings: Settings) -> Result<Runtime, String> {
    let found = Runtime::native(agent, settings.clone());
    if found.is_ok()
        || std::env::var_os("GASCOIGNE_LIB").is_some()
        || std::env::var("GASCOIGNE_UNPACK").is_ok_and(|v| v == "off")
    {
        return found;
    }
    match unpack() {
        Ok(Some(path)) => Runtime::native_at(agent, settings, Some(path)),
        _ => found,
    }
}
