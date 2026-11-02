use std::io::Write;

use flate2::write::GzEncoder;
use flate2::Compression;

fn gzip(text: &str) -> Vec<u8> {
    let mut enc = GzEncoder::new(Vec::new(), Compression::default());
    enc.write_all(text.as_bytes()).unwrap();
    enc.finish().unwrap()
}

#[test]
fn unpack_is_idempotent_and_checks_content() {
    let dir = std::env::temp_dir().join(format!("gas-rs-unpack-{}", std::process::id()));
    std::env::set_var("GASCOIGNE_LIB_DIR", &dir);
    let first = gascoigne_native::unpack_bytes(&gzip("library bytes"), "lib.so").unwrap();
    assert_eq!(std::fs::read_to_string(&first).unwrap(), "library bytes");
    assert!(first.to_string_lossy().contains("gascoigne-native-"));
    assert_eq!(
        gascoigne_native::unpack_bytes(&gzip("library bytes"), "lib.so").unwrap(),
        first
    );
    // A file replaced behind our back is rewritten, never loaded as is.
    std::fs::write(&first, "tampered").unwrap();
    let again = gascoigne_native::unpack_bytes(&gzip("library bytes"), "lib.so").unwrap();
    assert_eq!(std::fs::read_to_string(again).unwrap(), "library bytes");
}

#[test]
fn bundled_library_loads_from_tmp() {
    let Some(path) = gascoigne_native::unpack().unwrap() else {
        eprintln!("skipped: run scripts/bundle_native.py");
        return;
    };
    let db = std::env::temp_dir().join(format!("gas-rs-bundle-{}.db", std::process::id()));
    std::env::remove_var("GASCOIGNE_LIB");
    let rt = gascoigne::Runtime::native_at(
        "t",
        gascoigne::Settings {
            config: format!("extensions:\n  ledger:\n    path: {}\n", db.display()),
            ignore_user_file: true,
            ..gascoigne::Settings::default()
        },
        Some(path),
    )
    .unwrap();
    let raw = "INFO request served path=/api/items status=200 ms=12\n".repeat(400);
    assert!(!rt
        .optimize_result(&raw, &gascoigne::Attrs::default())
        .raw_id
        .is_empty());
}
