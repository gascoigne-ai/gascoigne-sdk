// Command native builds the gascoigne C ABI library:
//
//	go build -buildmode=c-shared -o dist/libgascoigne.so .
//
// Every function takes and returns UTF-8 C strings holding JSON (or plain text for raw and
// config). Returned strings belong to the caller and are released with gascoigne_free. On failure
// a function returns NULL (or 0) and, when err is not NULL, stores a message in *err, which is
// also released with gascoigne_free. Calls are safe from any thread.
package main

/*
#include <stdint.h>
#include <stdlib.h>
*/
import "C"

import (
	"unsafe"

	"github.com/gascoigne-ai/gascoigne-sdk/native/core"
)

func main() {}

// ret converts a Go result to the C convention.
func ret(s string, err error, out **C.char) *C.char {
	if err != nil {
		if out != nil {
			*out = C.CString(err.Error())
		}
		return nil
	}
	return C.CString(s)
}

// gascoigne_abi_version returns the ABI version of this library.
//
//export gascoigne_abi_version
func gascoigne_abi_version() C.int { return core.ABIVersion }

// gascoigne_open starts an engine from an options JSON document (NULL or "" for defaults) and
// returns its handle, or 0 on failure.
//
//export gascoigne_open
func gascoigne_open(options *C.char, err **C.char) C.uint64_t {
	h, e := core.Open(C.GoString(options))
	if e != nil {
		if err != nil {
			*err = C.CString(e.Error())
		}
		return 0
	}
	return C.uint64_t(h)
}

// gascoigne_config returns the merged YAML configuration the options describe.
//
//export gascoigne_config
func gascoigne_config(options *C.char, err **C.char) *C.char {
	s, e := core.Config(C.GoString(options))
	return ret(s, e, err)
}

// gascoigne_optimize runs a request JSON document and returns a response JSON document.
//
//export gascoigne_optimize
func gascoigne_optimize(h C.uint64_t, request *C.char, err **C.char) *C.char {
	s, e := core.Optimize(core.Handle(h), C.GoString(request))
	return ret(s, e, err)
}

// gascoigne_raw returns the original text behind a raw id.
//
//export gascoigne_raw
func gascoigne_raw(h C.uint64_t, id *C.char, err **C.char) *C.char {
	s, e := core.Raw(core.Handle(h), C.GoString(id))
	return ret(s, e, err)
}

// gascoigne_close stops an engine and releases its handle.
//
//export gascoigne_close
func gascoigne_close(h C.uint64_t) { _ = core.Close(core.Handle(h)) }

// gascoigne_free releases a string returned by this library.
//
//export gascoigne_free
func gascoigne_free(s *C.char) { C.free(unsafe.Pointer(s)) }
