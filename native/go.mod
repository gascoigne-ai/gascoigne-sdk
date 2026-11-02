module github.com/gascoigne-ai/gascoigne-sdk/native

go 1.27

require (
	github.com/ebitengine/purego v0.11.1 // indirect
	github.com/google/jsonschema-go v0.4.3 // indirect
	github.com/jinzhu/inflection v1.0.0 // indirect
	github.com/jinzhu/now v1.1.5 // indirect
	github.com/modelcontextprotocol/go-sdk v1.8.0 // indirect
	github.com/ncruces/go-sqlite3 v0.35.6 // indirect
	github.com/ncruces/go-sqlite3-wasm/v6 v6.3.35304 // indirect
	github.com/ncruces/go-sqlite3/gormlite v0.34.0 // indirect
	github.com/ncruces/julianday v1.0.0 // indirect
	github.com/segmentio/asm v1.1.3 // indirect
	github.com/segmentio/encoding v0.5.4 // indirect
	github.com/yosida95/uritemplate/v3 v3.0.2 // indirect
	go.yaml.in/yaml/v3 v3.0.5 // indirect
	golang.org/x/net v0.61.0 // indirect
	golang.org/x/oauth2 v0.35.0 // indirect
	golang.org/x/sync v0.24.0 // indirect
	golang.org/x/sys v0.49.0 // indirect
	golang.org/x/text v0.43.0 // indirect
	golang.org/x/time v0.15.0 // indirect
	gorm.io/gorm v1.31.2 // indirect
)

// Local sibling checkout until the engine facade (package inproc) is tagged in gascoigne-cli.
replace github.com/gascoigne-ai/gascoigne-cli => ../../../gascoigne-cli/master

require (
	github.com/gascoigne-ai/gascoigne-cli v0.0.0
	github.com/gascoigne-ai/gascoigne-sdk/go v0.0.0
)

// The Go SDK from this repository.
replace github.com/gascoigne-ai/gascoigne-sdk/go => ../go
