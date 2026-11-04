//! The native variant: libgascoigne loaded at run time (feature `native`, see
//! spec/native.md). Without the feature `Native::open` always reports it is missing.

use serde::Serialize;
use std::collections::BTreeMap;

#[cfg(feature = "native")]
const ABI: i32 = 2;

/// Configuration the library merges over its defaults and the user's file.
#[derive(Default, Serialize, Clone)]
pub struct Settings {
    /// YAML laid over the defaults and the user's file.
    #[serde(skip_serializing_if = "String::is_empty")]
    pub config: String,
    /// `dotted.path=value` assignments applied last.
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub set: Vec<String>,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub only: Vec<String>,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub disable: Vec<String>,
    #[serde(skip_serializing_if = "std::ops::Not::not")]
    pub ignore_user_file: bool,
    #[serde(skip_serializing_if = "is_zero")]
    pub timeout_ms: u32,
    /// `file` (default: the configured sqlite file) or `memory` (private to this process).
    #[serde(skip_serializing_if = "String::is_empty")]
    pub ledger: String,
    /// Prices behind [`crate::Runtime::costs`].
    #[serde(skip_serializing_if = "Option::is_none")]
    pub pricing: Option<Pricing>,
}

/// Where dollar figures come from for the embedded engine. Prices are held per process, not per
/// runtime.
#[derive(Default, Serialize, Clone)]
pub struct Pricing {
    /// `api` (default) or `subscription`: a flat plan has no dollars.
    #[serde(skip_serializing_if = "String::is_empty")]
    pub billing: String,
    /// Static prices by model id.
    #[serde(skip_serializing_if = "BTreeMap::is_empty")]
    pub prices: BTreeMap<String, Price>,
    /// A price sheet (JSON) read once when the engine opens.
    #[serde(skip_serializing_if = "String::is_empty")]
    pub file: String,
}

/// One model's price, dollars per million tokens.
#[derive(Default, Serialize, Clone)]
pub struct Price {
    /// Required.
    #[serde(rename = "in")]
    pub input: f64,
    /// Required.
    #[serde(rename = "out")]
    pub output: f64,
    /// Defaults to `input` when `None`.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cache_read: Option<f64>,
    /// Defaults to `input` when `None`.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cache_write: Option<f64>,
    /// `o200k` (default), `claude`, `claude-legacy` or `gemini`.
    #[serde(skip_serializing_if = "String::is_empty")]
    pub tokenizer: String,
}

// serde passes a reference.
#[allow(clippy::trivially_copy_pass_by_ref)]
fn is_zero(n: &u32) -> bool {
    *n == 0
}

#[cfg(feature = "native")]
fn library_name() -> &'static str {
    if cfg!(windows) {
        "gascoigne.dll"
    } else if cfg!(target_os = "macos") {
        "libgascoigne.dylib"
    } else {
        "libgascoigne.so"
    }
}

/// Where an installed library may live (see spec/native.md).
#[cfg(feature = "native")]
fn system_dirs() -> Vec<std::path::PathBuf> {
    use std::path::PathBuf;
    let mut dirs: Vec<PathBuf> = std::env::var_os("GASCOIGNE_LIB_PATH")
        .map(|p| std::env::split_paths(&p).collect())
        .unwrap_or_default();
    if let Some(bin) = std::env::var_os("GASCOIGNE_BIN") {
        dirs.extend(PathBuf::from(bin).parent().map(PathBuf::from));
    }
    let home = std::env::var_os("HOME")
        .map(PathBuf::from)
        .unwrap_or_default();
    if cfg!(windows) {
        for var in ["LOCALAPPDATA", "ProgramFiles"] {
            dirs.extend(std::env::var_os(var).map(|d| PathBuf::from(d).join("gascoigne")));
        }
    } else if cfg!(target_os = "macos") {
        dirs.extend([
            home.join(".local/lib"),
            "/usr/local/lib".into(),
            "/opt/homebrew/lib".into(),
        ]);
    } else {
        let multiarch = format!("{}-linux-gnu", std::env::consts::ARCH);
        dirs.extend([
            home.join(".local/lib"),
            "/usr/local/lib".into(),
            "/usr/lib".into(),
            "/usr/lib64".into(),
            PathBuf::from("/usr/lib").join(multiarch),
            "/opt/gascoigne/lib".into(),
        ]);
    }
    dirs
}

/// The library to load: `$GASCOIGNE_LIB`, else the system directories. `looked` receives where it
/// searched. The `gascoigne-native` dependency passes its own path to `Native::open`.
#[cfg(feature = "native")]
fn find_library(looked: &mut Vec<String>) -> Option<std::path::PathBuf> {
    if let Some(path) = std::env::var_os("GASCOIGNE_LIB") {
        let path = std::path::PathBuf::from(path);
        looked.push(format!("$GASCOIGNE_LIB={}", path.display()));
        return path.is_file().then_some(path);
    }
    for dir in system_dirs() {
        looked.push(dir.display().to_string());
        let found = [library_name()]
            .iter()
            .map(|n| dir.join(n))
            .find(|p| p.is_file());
        if found.is_some() {
            return found;
        }
    }
    None
}

#[cfg(feature = "native")]
pub use enabled::Native;

#[cfg(feature = "native")]
mod enabled {
    use std::ffi::{c_char, c_int, c_void, CStr, CString};
    use std::path::Path;

    use libloading::{Library, Symbol};

    use super::{find_library, Settings, ABI};

    type Open = unsafe extern "C" fn(*const c_char, *mut *mut c_char) -> u64;
    type Call = unsafe extern "C" fn(u64, *const c_char, *mut *mut c_char) -> *mut c_char;

    /// An open engine in this process.
    pub struct Native {
        lib: Library,
        handle: u64,
    }

    impl Native {
        /// Loads the library and starts an engine from `settings`.
        pub fn open(settings: &Settings, library: Option<&Path>) -> Result<Native, String> {
            let mut looked = Vec::new();
            let path = library
                .map(Path::to_path_buf)
                .or_else(|| find_library(&mut looked))
                .ok_or_else(|| {
                    format!(
                        "libgascoigne not found; looked in: {}. Install it in one of those \
                         places or add the gascoigne-native crate",
                        looked.join(", ")
                    )
                })?;
            // SAFETY: loading a library runs its initializers; this one is the gascoigne build.
            let lib =
                unsafe { Library::new(&path) }.map_err(|e| format!("{}: {e}", path.display()))?;
            // SAFETY: the symbol has this signature in spec/native.md.
            let version: c_int = unsafe {
                let f: Symbol<unsafe extern "C" fn() -> c_int> = lib
                    .get(b"gascoigne_abi_version")
                    .map_err(|e| e.to_string())?;
                f()
            };
            if version != ABI {
                return Err(format!("{} speaks another ABI than {ABI}", path.display()));
            }
            let options = CString::new(serde_json::to_string(settings).map_err(|e| e.to_string())?)
                .map_err(|e| e.to_string())?;
            let mut err: *mut c_char = std::ptr::null_mut();
            // SAFETY: options is a valid C string and err a valid out pointer.
            let handle = unsafe {
                let f: Symbol<Open> = lib.get(b"gascoigne_open").map_err(|e| e.to_string())?;
                f(options.as_ptr(), &mut err)
            };
            let native = Native { lib, handle };
            if handle == 0 {
                return Err(native.take(err).unwrap_or_else(|| "open failed".into()));
            }
            Ok(native)
        }

        /// Copies and releases a string the library returned.
        fn take(&self, ptr: *mut c_char) -> Option<String> {
            if ptr.is_null() {
                return None;
            }
            // SAFETY: ptr came from the library and is a NUL-terminated string released once.
            unsafe {
                let text = CStr::from_ptr(ptr).to_string_lossy().into_owned();
                if let Ok(free) = self
                    .lib
                    .get::<unsafe extern "C" fn(*mut c_void)>(b"gascoigne_free")
                {
                    free(ptr.cast());
                }
                Some(text)
            }
        }

        fn call(&self, name: &[u8], arg: &str) -> Result<String, String> {
            let arg = CString::new(arg).map_err(|e| e.to_string())?;
            let mut err: *mut c_char = std::ptr::null_mut();
            // SAFETY: handle is open, arg is a valid C string, err a valid out pointer.
            let out = unsafe {
                let f: Symbol<Call> = self.lib.get(name).map_err(|e| e.to_string())?;
                f(self.handle, arg.as_ptr(), &mut err)
            };
            match self.take(out) {
                Some(text) => Ok(text),
                None => Err(self.take(err).unwrap_or_else(|| "call failed".into())),
            }
        }

        /// Optimizes a request JSON document; returns the response JSON document.
        pub fn optimize(&self, request: &str) -> Result<String, String> {
            self.call(b"gascoigne_optimize", request)
        }

        /// The original text behind a raw id.
        pub fn raw(&self, id: &str) -> Result<String, String> {
            self.call(b"gascoigne_raw", id)
        }

        /// Totals per group, as the library's JSON list.
        pub fn stats(&self, query: &str) -> Result<String, String> {
            self.call(b"gascoigne_stats", query)
        }

        /// Recorded runs, as the library's JSON list.
        pub fn recent(&self, query: &str) -> Result<String, String> {
            self.call(b"gascoigne_recent", query)
        }

        /// The tokens saved, priced, as the library's JSON object.
        pub fn costs(&self, query: &str) -> Result<String, String> {
            self.call(b"gascoigne_costs", query)
        }
    }

    impl Drop for Native {
        fn drop(&mut self) {
            // SAFETY: the handle is open and closed exactly once.
            unsafe {
                if let Ok(close) = self
                    .lib
                    .get::<unsafe extern "C" fn(u64)>(b"gascoigne_close")
                {
                    close(self.handle);
                }
            }
        }
    }
}

/// Stand-in when the crate is built without the `native` feature.
#[cfg(not(feature = "native"))]
pub struct Native;

// The stand-in keeps the real signatures, so its methods ignore `self` on purpose.
#[cfg(not(feature = "native"))]
#[allow(clippy::unused_self)]
impl Native {
    pub fn open(
        _settings: &Settings,
        _library: Option<&std::path::Path>,
    ) -> Result<Native, String> {
        Err("built without the `native` feature".into())
    }

    pub fn optimize(&self, _request: &str) -> Result<String, String> {
        Err("built without the `native` feature".into())
    }

    pub fn raw(&self, _id: &str) -> Result<String, String> {
        Err("built without the `native` feature".into())
    }

    pub fn stats(&self, _query: &str) -> Result<String, String> {
        Err("built without the `native` feature".into())
    }

    pub fn recent(&self, _query: &str) -> Result<String, String> {
        Err("built without the `native` feature".into())
    }

    pub fn costs(&self, _query: &str) -> Result<String, String> {
        Err("built without the `native` feature".into())
    }
}
