#![cfg(feature = "native")]
use gascoigne::{Attrs, RunsQuery, Runtime, Settings, TotalsQuery};

/// Against the real library built from native/: a memory ledger counts runs and writes no file.
#[test]
fn embedded_memory_ledger() {
    let lib =
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../native/dist/libgascoigne.so");
    if !lib.exists() {
        eprintln!("skipped: build native/ first");
        return;
    }
    let data = std::env::temp_dir().join(format!("gas-rust-mem-{}", std::process::id()));
    std::fs::create_dir_all(&data).unwrap();
    std::env::set_var("GASCOIGNE_LIB", &lib);
    std::env::set_var("GASCOIGNE_LEDGER", "");
    std::env::set_var("XDG_DATA_HOME", &data);
    std::env::remove_var("GASCOIGNE_SDK");
    let rt = Runtime::native(
        "sdk",
        Settings {
            ignore_user_file: true,
            ledger: "memory".into(),
            ..Settings::default()
        },
    )
    .unwrap();
    let raw = "INFO request served path=/api/items status=200 ms=12\n".repeat(400);
    let attrs = Attrs {
        tool: "bash".into(),
        ..Attrs::default()
    };
    rt.optimize_result(&raw, &attrs);
    let totals = rt.totals(&TotalsQuery {
        by: "agent".into(),
        ..TotalsQuery::default()
    });
    assert_eq!((totals[0].group.as_str(), totals[0].runs), ("sdk", 1));
    assert!(totals[0].saved > 0);
    let runs = rt.runs(&RunsQuery::default());
    assert_eq!(runs.len(), 1);
    assert!(!runs[0].raw_id.is_empty());
    assert!(rt
        .totals(&TotalsQuery {
            by: "nonsense".into(),
            ..TotalsQuery::default()
        })
        .is_empty());
    assert_eq!(std::fs::read_dir(&data).unwrap().count(), 0);
}
