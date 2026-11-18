module github.com/gascoigne-ai/gascoigne-sdk/native

go 1.27

require (
	github.com/ebitengine/purego v0.11.3 // indirect
	github.com/google/jsonschema-go v0.4.3 // indirect
	github.com/jinzhu/inflection v1.0.0 // indirect
	github.com/jinzhu/now v1.1.5 // indirect
	github.com/modelcontextprotocol/go-sdk v1.8.0 // indirect
	github.com/ncruces/go-sqlite3 v0.37.0 // indirect
	github.com/ncruces/go-sqlite3-wasm/v6 v6.7.35401 // indirect
	github.com/ncruces/go-sqlite3/gormlite v0.34.0 // indirect
	github.com/ncruces/julianday v1.0.0 // indirect
	github.com/segmentio/asm v1.2.1 // indirect
	github.com/segmentio/encoding v0.5.4 // indirect
	github.com/yosida95/uritemplate/v3 v3.0.2 // indirect
	go.yaml.in/yaml/v3 v3.0.6 // indirect
	golang.org/x/net v0.62.0 // indirect
	golang.org/x/oauth2 v0.38.0 // indirect
	golang.org/x/sync v0.25.0 // indirect
	golang.org/x/sys v0.50.0 // indirect
	golang.org/x/text v0.44.0 // indirect
	golang.org/x/time v0.16.0 // indirect
	gorm.io/gorm v1.31.2 // indirect
)

// CLI checkout (submodule `cli`) until the engine facade (package inproc) is tagged in gascoigne-cli.
replace github.com/gascoigne-ai/gascoigne-cli => ../cli

require (
	github.com/gascoigne-ai/gascoigne-cli v0.0.0
	github.com/gascoigne-ai/gascoigne-sdk/go v0.0.0
)

// The Go SDK from this repository.
replace github.com/gascoigne-ai/gascoigne-sdk/go => ../go
