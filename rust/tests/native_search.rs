use gascoigne::{Runtime, Settings};

/// The system directories are searched, `$GASCOIGNE_LIB_PATH` first.
#[test]
fn system_directories_are_searched() {
    std::env::remove_var("GASCOIGNE_LIB");
    let dir = std::env::temp_dir().join(format!("gas-rs-sys-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    std::env::set_var("GASCOIGNE_LIB_PATH", &dir);
    let Err(message) = Runtime::native("t", Settings::default()) else {
        panic!("expected an error");
    };
    assert!(message.contains(&dir.display().to_string()), "{message}");
}
