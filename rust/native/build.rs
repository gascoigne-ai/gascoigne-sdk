//! Lists the bundled libraries (`lib/<os>-<arch>/<file>.gz`, written by scripts/bundle_native.py)
//! as a static table, so the crate builds with whichever platforms the bundle holds.

use std::fmt::Write;
use std::path::Path;

fn main() {
    let lib = Path::new(env!("CARGO_MANIFEST_DIR")).join("lib");
    println!("cargo:rerun-if-changed=lib");
    let mut table = String::from("pub static BUNDLE: &[(&str, &str, &[u8])] = &[\n");
    let mut dirs: Vec<_> = std::fs::read_dir(&lib)
        .into_iter()
        .flatten()
        .flatten()
        .filter(|e| e.path().is_dir())
        .collect();
    dirs.sort_by_key(std::fs::DirEntry::file_name);
    for dir in dirs {
        for file in std::fs::read_dir(dir.path()).unwrap().flatten() {
            let name = file
                .file_name()
                .to_string_lossy()
                .trim_end_matches(".gz")
                .to_string();
            let key = dir.file_name().to_string_lossy().to_string();
            writeln!(
                table,
                "    ({key:?}, {name:?}, include_bytes!({:?})),",
                file.path().display().to_string()
            )
            .unwrap();
        }
    }
    table.push_str("];\n");
    let out = std::env::var("OUT_DIR").unwrap();
    std::fs::write(Path::new(&out).join("bundle.rs"), table).unwrap();
}
