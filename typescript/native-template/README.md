# @gascoigne-ai/sdk-native

Adds the native variant to `@gascoigne-ai/sdk`: the engine runs inside your Node process, with no
server and no CLI. Install it with `koffi` and select it:

```ts
import { init } from "@gascoigne-ai/sdk";

init({ mode: "native" });
```

The library for your platform is unpacked to the temporary directory on first use. This package
holds data only; see `spec/native.md` in the repository.
