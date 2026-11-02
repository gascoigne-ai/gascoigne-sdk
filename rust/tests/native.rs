#![cfg(feature = "native")]
use gascoigne::{Attrs, Runtime, Settings};

/// Against the real library built from native/ (feature `embedded`, skipped when not built).
#[test]
fn embedded_optimizes_and_returns_original() {
    let lib =
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../native/dist/libgascoigne.so");
    if !lib.exists() {
        eprintln!("skipped: build native/ first");
        return;
    }
    std::env::set_var("GASCOIGNE_LIB", &lib);
    let db = std::env::temp_dir().join(format!("gas-rust-{}.db", std::process::id()));
    let rt = Runtime::native(
        "t",
        Settings {
            config: format!("extensions:\n  ledger:\n    path: {}\n", db.display()),
            ignore_user_file: true,
            ..Settings::default()
        },
    )
    .unwrap();
    let raw = "INFO request served path=/api/items status=200 ms=12\n".repeat(400);
    let res = rt.optimize_result(&raw, &Attrs::tool("bash"));
    assert!(res.out_tokens < res.raw_tokens && !res.raw_id.is_empty());
    assert_eq!(rt.raw(&res.raw_id), raw);
    assert!(rt.proxy_base_url("openai").is_none());
}
