use gascoigne::{Runtime, Settings};

/// No library anywhere: native mode is an error that says where it looked, not a silent bypass.
#[test]
fn missing_library_is_an_error_naming_where_it_looked() {
    std::env::set_var("GASCOIGNE_LIB", "/nonexistent/libgascoigne.so");
    let Err(message) = Runtime::native("t", Settings::default()) else {
        panic!("expected an error");
    };
    assert!(message.contains("libgascoigne not found"), "{message}");
    assert!(message.contains("GASCOIGNE_LIB"), "{message}");
}
